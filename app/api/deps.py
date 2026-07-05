"""
Dependencias compartidas de la API: autenticacion y control de roles por proyecto.

Como los roles son por proyecto, el control de permisos necesita saber en que
proyecto se esta actuando. Estas dependencias obtienen al usuario autenticado y,
cuando hace falta, comprueban su rol dentro de un proyecto concreto.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import decode_access_token
from app.models.db_models import ProjectMember, Role, User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    """Obtiene el usuario autenticado a partir del token JWT."""
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Falta el token de acceso.",
        )
    payload = decode_access_token(creds.credentials)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado.",
        )
    user = session.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario del token ya no existe.",
        )
    return user


def get_member(session: Session, project_id: int, user_id: int) -> ProjectMember | None:
    """Devuelve la membresia de un usuario en un proyecto, o None si no pertenece."""
    return session.exec(
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .where(ProjectMember.user_id == user_id)
    ).first()


def require_project_role(*roles: Role):
    """
    Genera una dependencia que exige que el usuario tenga uno de los roles dados
    DENTRO del proyecto indicado. El proyecto se toma del parametro 'project_id'
    de la ruta o del cuerpo de la peticion.

    El rol ADMIN del proyecto siempre tiene acceso.
    """

    def checker(
        project_id: int,
        session: Session = Depends(get_session),
        user: User = Depends(get_current_user),
    ) -> User:
        member = get_member(session, project_id, user.id)
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No perteneces a este proyecto.",
            )
        if member.role != Role.ADMIN and member.role not in roles:
            permitidos = ", ".join(r.value for r in roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Tu rol en este proyecto ('{member.role.value}') no permite "
                    f"esta accion. Roles permitidos: {permitidos}."
                ),
            )
        return user

    return checker


def require_member(
    project_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> User:
    """Exige solo que el usuario pertenezca al proyecto (cualquier rol)."""
    if get_member(session, project_id, user.id) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No perteneces a este proyecto.",
        )
    return user
