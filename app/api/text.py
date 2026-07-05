"""
Endpoints de edicion de contenido con IA.

Cubre el bloque 2 del enunciado (edicion de contenido): resumir, expandir,
corregir y generar variaciones. La edicion de texto es una herramienta de
asistencia disponible para cualquier usuario autenticado; el control por roles
se aplica al guardar documentos dentro de un proyecto (ver documents.py).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.db_models import User
from app.models.schemas import TextEditRequest, TextEditResponse
from app.services.moderation import ModeracionError
from app.services.text_service import procesar_texto

router = APIRouter(prefix="/text", tags=["Edicion de texto"])

_OPERACIONES = {"resumir", "expandir", "corregir", "variacion"}


@router.post("/edit", response_model=TextEditResponse)
def editar(
    data: TextEditRequest,
    user: User = Depends(get_current_user),
):
    """Aplica una operacion de edicion de IA sobre un texto."""
    if data.operacion not in _OPERACIONES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operacion no valida. Usa una de: {', '.join(sorted(_OPERACIONES))}.",
        )
    if not data.texto.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacio.")

    try:
        resultado = procesar_texto(data.operacion, data.texto)
    except ModeracionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.motivo)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al procesar el texto: {e}",
        )

    return TextEditResponse(operacion=data.operacion, resultado=resultado)
