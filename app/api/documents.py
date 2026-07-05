"""
Endpoints de documentos con historial de versiones.

Cubre el requisito del enunciado de historial y seguimiento de cambios: cada
edicion crea una version nueva, y es posible listar las versiones y revertir a
una anterior. El contenido se guarda cifrado.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.database import get_session
from app.core.security import decrypt_text, encrypt_text
from app.models.db_models import Document, DocumentVersion, User
from app.models.schemas import (
    DocumentCreateRequest,
    DocumentResponse,
    DocumentVersionResponse,
)

router = APIRouter(prefix="/documents", tags=["Documentos"])


def _contenido_actual(session: Session, doc_id: int) -> str:
    """Devuelve el contenido de la ultima version de un documento."""
    ultima = session.exec(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_num.desc())
    ).first()
    return decrypt_text(ultima.encrypted_content) if ultima else ""


def _total_versiones(session: Session, doc_id: int) -> int:
    return len(
        session.exec(
            select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
        ).all()
    )


@router.post("", response_model=DocumentResponse)
def crear_documento(
    data: DocumentCreateRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Crea un documento con su primera version."""
    doc = Document(titulo=data.titulo, author_id=user.id, project_id=data.project_id)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    version = DocumentVersion(
        document_id=doc.id,
        version_num=1,
        encrypted_content=encrypt_text(data.contenido),
        accion="creacion",
        author_id=user.id,
    )
    session.add(version)
    session.commit()

    return DocumentResponse(
        id=doc.id, titulo=doc.titulo,
        contenido_actual=data.contenido, total_versiones=1,
    )


@router.put("/{doc_id}", response_model=DocumentResponse)
def guardar_version(
    doc_id: int,
    contenido: str,
    accion: str = "edicion",
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Guarda una version nueva del documento (historial de cambios)."""
    doc = session.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    nuevo_num = _total_versiones(session, doc_id) + 1
    version = DocumentVersion(
        document_id=doc_id,
        version_num=nuevo_num,
        encrypted_content=encrypt_text(contenido),
        accion=accion,
        author_id=user.id,
    )
    session.add(version)
    session.commit()

    return DocumentResponse(
        id=doc.id, titulo=doc.titulo,
        contenido_actual=contenido, total_versiones=nuevo_num,
    )


@router.get("/{doc_id}/versions", response_model=list[DocumentVersionResponse])
def listar_versiones(
    doc_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Lista el historial de versiones de un documento (para comparar)."""
    versiones = session.exec(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_num.desc())
    ).all()
    return [
        DocumentVersionResponse(
            version_num=v.version_num,
            accion=v.accion,
            contenido=decrypt_text(v.encrypted_content),
            author_id=v.author_id,
            created_at=v.created_at.isoformat(),
        )
        for v in versiones
    ]


@router.post("/{doc_id}/revert/{version_num}", response_model=DocumentResponse)
def revertir(
    doc_id: int,
    version_num: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Revierte el documento a una version anterior.

    En lugar de borrar el historial, se crea una version nueva con el contenido
    de la version elegida, preservando asi la trazabilidad completa.
    """
    doc = session.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    objetivo = session.exec(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .where(DocumentVersion.version_num == version_num)
    ).first()
    if objetivo is None:
        raise HTTPException(status_code=404, detail="Version no encontrada.")

    contenido = decrypt_text(objetivo.encrypted_content)
    nuevo_num = _total_versiones(session, doc_id) + 1
    version = DocumentVersion(
        document_id=doc_id,
        version_num=nuevo_num,
        encrypted_content=encrypt_text(contenido),
        accion=f"reversion-a-v{version_num}",
        author_id=user.id,
    )
    session.add(version)
    session.commit()

    return DocumentResponse(
        id=doc.id, titulo=doc.titulo,
        contenido_actual=contenido, total_versiones=nuevo_num,
    )
