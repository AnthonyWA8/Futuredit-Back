"""
Endpoints de generacion de imagenes.

Cubre el bloque 1 del enunciado (generacion de imagenes) y aspectos de seguridad
y etica: moderacion del prompt, control de roles por proyecto, cifrado del
contenido y galeria.

Sobre los permisos: si la imagen se genera dentro de un proyecto, se exige que
el usuario tenga rol de disenador (o admin) EN ese proyecto. Si se genera sin
proyecto (uso individual), basta con estar autenticado.
"""

import base64

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_member
from app.core.database import get_session
from app.core.security import decrypt_text, encrypt_text
from app.models.db_models import GeneratedImage, Role, User
from app.models.schemas import ImageGenRequest, ImageResponse
from app.services.image_service import generar_imagen
from app.services.moderation import ModeracionError, revisar_texto

router = APIRouter(prefix="/images", tags=["Imagenes"])


def _a_data_url(img: GeneratedImage) -> str:
    """Descifra la imagen y la devuelve como data URL para el frontend."""
    b64 = decrypt_text(img.encrypted_data)
    return f"data:{img.mime};base64,{b64}"


def _validar_permiso_proyecto(session, project_id, user, roles_permitidos):
    """
    Si hay project_id, verifica que el usuario tenga un rol permitido en el
    proyecto. Si no hay project_id, permite la accion (uso individual).
    """
    if project_id is None:
        return
    member = get_member(session, project_id, user.id)
    if member is None:
        raise HTTPException(status_code=403, detail="No perteneces a este proyecto.")
    if member.role != Role.ADMIN and member.role not in roles_permitidos:
        permitidos = ", ".join(r.value for r in roles_permitidos)
        raise HTTPException(
            status_code=403,
            detail=(
                f"Tu rol en este proyecto ('{member.role.value}') no permite esta "
                f"accion. Roles permitidos: {permitidos}."
            ),
        )


@router.post("/generate", response_model=ImageResponse)
def generar(
    data: ImageGenRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Genera una imagen a partir de un prompt, la modera, cifra y guarda."""
    # Control de permisos por proyecto (si aplica): generar imagenes es de disenadores.
    _validar_permiso_proyecto(session, data.project_id, user, [Role.DISENADOR])

    # 1. Moderacion del prompt (requisito etico).
    try:
        revisar_texto(data.prompt)
        revisar_texto(data.negative_prompt)
    except ModeracionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.motivo)

    # 2. Generacion (segun el proveedor configurado).
    try:
        png_bytes = generar_imagen(
            data.prompt, data.estilo, data.ratio, data.negative_prompt
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al generar la imagen: {e}",
        )

    # 3. Cifrado del contenido antes de guardarlo (seguridad en reposo).
    b64 = base64.b64encode(png_bytes).decode("utf-8")
    encrypted = encrypt_text(b64)

    img = GeneratedImage(
        project_id=data.project_id,
        author_id=user.id,
        prompt=data.prompt,
        negative_prompt=data.negative_prompt,
        estilo=data.estilo,
        ratio=data.ratio,
        encrypted_data=encrypted,
    )
    session.add(img)
    session.commit()
    session.refresh(img)

    return ImageResponse(
        id=img.id, prompt=img.prompt, estilo=img.estilo, ratio=img.ratio,
        aprobada=img.aprobada, data_url=_a_data_url(img),
    )


@router.get("/gallery", response_model=list[ImageResponse])
def galeria(
    project_id: int | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Devuelve la galeria de imagenes. Si se indica project_id, devuelve las de
    ese proyecto (requiere ser miembro). Si no, devuelve las imagenes propias
    del usuario mas las que no pertenecen a ningun proyecto.
    """
    if project_id is not None:
        if get_member(session, project_id, user.id) is None:
            raise HTTPException(status_code=403, detail="No perteneces a este proyecto.")
        query = select(GeneratedImage).where(GeneratedImage.project_id == project_id)
    else:
        query = select(GeneratedImage).where(GeneratedImage.author_id == user.id)

    imgs = session.exec(query.order_by(GeneratedImage.created_at.desc())).all()
    return [
        ImageResponse(
            id=i.id, prompt=i.prompt, estilo=i.estilo, ratio=i.ratio,
            aprobada=i.aprobada, data_url=_a_data_url(i),
        )
        for i in imgs
    ]


@router.post("/{image_id}/approve", response_model=ImageResponse)
def aprobar(
    image_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Marca una imagen como aprobada. Requiere rol de aprobador (o admin) en el
    proyecto al que pertenece la imagen.
    """
    img = session.get(GeneratedImage, image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")

    _validar_permiso_proyecto(session, img.project_id, user, [Role.APROBADOR])

    img.aprobada = True
    session.add(img)
    session.commit()
    session.refresh(img)
    return ImageResponse(
        id=img.id, prompt=img.prompt, estilo=img.estilo, ratio=img.ratio,
        aprobada=img.aprobada, data_url=_a_data_url(img),
    )
