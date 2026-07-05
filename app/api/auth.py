"""
Endpoints de autenticacion: registro e inicio de sesion.

Gestiona las cuentas de usuario y entrega tokens JWT para las sesiones. Los
roles NO se asignan aqui, sino dentro de cada proyecto (ver api/projects.py).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.database import get_session
from app.core.security import create_access_token, hash_password, verify_password
from app.models.db_models import User
from app.models.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


def _token_para(user: User) -> TokenResponse:
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token, user_id=user.id, nombre=user.nombre, email=user.email
    )


@router.post("/register", response_model=TokenResponse)
def register(data: RegisterRequest, session: Session = Depends(get_session)):
    """Registra un usuario nuevo y devuelve su token de sesion."""
    existente = session.exec(select(User).where(User.email == data.email)).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese correo.",
        )
    user = User(
        email=data.email,
        nombre=data.nombre,
        hashed_password=hash_password(data.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _token_para(user)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)):
    """Valida las credenciales y devuelve un token de sesion."""
    user = session.exec(select(User).where(User.email == data.email)).first()
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contrasena incorrectos.",
        )
    return _token_para(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """Devuelve los datos del usuario autenticado."""
    return {
        "id": user.id,
        "email": user.email,
        "nombre": user.nombre,
        "avatar_url": user.avatar_url,
    }
