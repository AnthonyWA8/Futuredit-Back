"""
Endpoints de comentarios.

Cubre el requisito de comentarios y notas para la colaboracion y la
retroalimentacion en el proceso creativo. Los comentarios pueden asociarse a un
proyecto, un documento o una imagen.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.db_models import Comment, User
from app.models.schemas import CommentRequest, CommentResponse

router = APIRouter(prefix="/comments", tags=["Comentarios"])


@router.post("", response_model=CommentResponse)
def crear_comentario(
    data: CommentRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Crea un comentario asociado a un proyecto, documento o imagen."""
    if not data.texto.strip():
        raise HTTPException(status_code=400, detail="El comentario no puede estar vacio.")
    comentario = Comment(
        author_id=user.id,
        texto=data.texto,
        project_id=data.project_id,
        document_id=data.document_id,
        image_id=data.image_id,
    )
    session.add(comentario)
    session.commit()
    session.refresh(comentario)
    return CommentResponse(
        id=comentario.id, autor=user.nombre, texto=comentario.texto,
        created_at=comentario.created_at.isoformat(),
    )


@router.get("", response_model=list[CommentResponse])
def listar_comentarios(
    project_id: int | None = None,
    document_id: int | None = None,
    image_id: int | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Lista los comentarios filtrando por proyecto, documento o imagen."""
    query = select(Comment)
    if project_id is not None:
        query = query.where(Comment.project_id == project_id)
    if document_id is not None:
        query = query.where(Comment.document_id == document_id)
    if image_id is not None:
        query = query.where(Comment.image_id == image_id)
    query = query.order_by(Comment.created_at.desc())

    comentarios = session.exec(query).all()
    # Se resuelve el nombre del autor de cada comentario.
    resultado = []
    for c in comentarios:
        autor = session.get(User, c.author_id)
        resultado.append(
            CommentResponse(
                id=c.id, autor=autor.nombre if autor else "Desconocido",
                texto=c.texto, created_at=c.created_at.isoformat(),
            )
        )
    return resultado
