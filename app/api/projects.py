"""
Endpoints de proyectos y colaboracion.

Implementa el modelo de roles por proyecto que pide el frontend:
- Crear un proyecto: quien lo crea queda como ADMIN y se genera un codigo de
  invitacion unico.
- Unirse a un proyecto mediante ese codigo (se entra con rol REDACTOR por
  defecto, que el admin puede cambiar despues).
- Listar los proyectos del usuario, con su rol en cada uno.
- Ver los miembros de un proyecto.
- Asignar o cambiar el rol de un miembro (solo el admin del proyecto).
"""

import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_member
from app.core.database import get_session
from app.models.db_models import (
    Document,
    GeneratedImage,
    Project,
    ProjectMember,
    Role,
    User,
)
from app.models.schemas import (
    AssignRoleRequest,
    JoinProjectRequest,
    MemberResponse,
    ProjectCreateRequest,
    ProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["Proyectos"])


def _generar_codigo(session: Session) -> str:
    """Genera un codigo de invitacion unico y legible (ej. 'FTX-7K2Q9')."""
    alfabeto = string.ascii_uppercase + string.digits
    while True:
        codigo = "FTX-" + "".join(secrets.choice(alfabeto) for _ in range(5))
        existe = session.exec(
            select(Project).where(Project.codigo_invitacion == codigo)
        ).first()
        if not existe:
            return codigo


def _to_response(session: Session, project: Project, mi_rol: Role) -> ProjectResponse:
    """Arma la respuesta de un proyecto con sus contadores."""
    miembros = session.exec(
        select(ProjectMember).where(ProjectMember.project_id == project.id)
    ).all()
    imagenes = session.exec(
        select(GeneratedImage).where(GeneratedImage.project_id == project.id)
    ).all()
    documentos = session.exec(
        select(Document).where(Document.project_id == project.id)
    ).all()
    return ProjectResponse(
        id=project.id,
        nombre=project.nombre,
        descripcion=project.descripcion,
        codigo_invitacion=project.codigo_invitacion,
        estado=project.estado,
        color=project.color,
        mi_rol=mi_rol,
        total_miembros=len(miembros),
        total_imagenes=len(imagenes),
        total_documentos=len(documentos),
        created_at=project.created_at.isoformat(),
    )


@router.post("", response_model=ProjectResponse)
def crear_proyecto(
    data: ProjectCreateRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Crea un proyecto. Quien lo crea queda automaticamente como ADMIN y se genera
    un codigo de invitacion para que otros se unan.
    """
    project = Project(
        nombre=data.nombre,
        descripcion=data.descripcion,
        color=data.color,
        owner_id=user.id,
        codigo_invitacion=_generar_codigo(session),
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # El creador se registra como miembro con rol ADMIN.
    membresia = ProjectMember(
        project_id=project.id, user_id=user.id, role=Role.ADMIN
    )
    session.add(membresia)
    session.commit()

    return _to_response(session, project, Role.ADMIN)


@router.post("/join", response_model=ProjectResponse)
def unirse_por_codigo(
    data: JoinProjectRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Une al usuario a un proyecto mediante su codigo de invitacion."""
    project = session.exec(
        select(Project).where(Project.codigo_invitacion == data.codigo_invitacion.strip())
    ).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Codigo de invitacion no valido.")

    # Si ya es miembro, se devuelve el proyecto sin duplicar la membresia.
    existente = get_member(session, project.id, user.id)
    if existente:
        return _to_response(session, project, existente.role)

    membresia = ProjectMember(
        project_id=project.id, user_id=user.id, role=Role.REDACTOR
    )
    session.add(membresia)
    session.commit()
    return _to_response(session, project, Role.REDACTOR)


@router.get("", response_model=list[ProjectResponse])
def mis_proyectos(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Lista todos los proyectos a los que pertenece el usuario, con su rol."""
    membresias = session.exec(
        select(ProjectMember).where(ProjectMember.user_id == user.id)
    ).all()
    resultado = []
    for m in membresias:
        project = session.get(Project, m.project_id)
        if project:
            resultado.append(_to_response(session, project, m.role))
    return resultado


@router.get("/{project_id}/members", response_model=list[MemberResponse])
def miembros(
    project_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Lista los miembros de un proyecto y su rol. Solo para miembros."""
    if get_member(session, project_id, user.id) is None:
        raise HTTPException(status_code=403, detail="No perteneces a este proyecto.")

    membresias = session.exec(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    ).all()
    resultado = []
    for m in membresias:
        u = session.get(User, m.user_id)
        if u:
            resultado.append(
                MemberResponse(
                    user_id=u.id, nombre=u.nombre, email=u.email,
                    role=m.role, avatar_url=u.avatar_url,
                )
            )
    return resultado


@router.post("/{project_id}/assign-role", response_model=MemberResponse)
def asignar_rol(
    project_id: int,
    data: AssignRoleRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Asigna o cambia el rol de un miembro. Solo el ADMIN del proyecto puede
    hacerlo. El admin no puede quitarse a si mismo el rol de admin si es el unico.
    """
    yo = get_member(session, project_id, user.id)
    if yo is None or yo.role != Role.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Solo el administrador del proyecto puede asignar roles.",
        )

    objetivo = get_member(session, project_id, data.user_id)
    if objetivo is None:
        raise HTTPException(status_code=404, detail="Ese usuario no es miembro del proyecto.")

    # Evitar que el proyecto se quede sin ningun admin.
    if objetivo.role == Role.ADMIN and data.role != Role.ADMIN:
        admins = session.exec(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .where(ProjectMember.role == Role.ADMIN)
        ).all()
        if len(admins) <= 1:
            raise HTTPException(
                status_code=400,
                detail="El proyecto debe tener al menos un administrador.",
            )

    objetivo.role = data.role
    session.add(objetivo)
    session.commit()
    session.refresh(objetivo)

    u = session.get(User, objetivo.user_id)
    return MemberResponse(
        user_id=u.id, nombre=u.nombre, email=u.email,
        role=objetivo.role, avatar_url=u.avatar_url,
    )
