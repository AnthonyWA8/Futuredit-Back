"""
Utilidades de seguridad: hashing de contrasenas, tokens JWT y cifrado.

Cubre los requisitos de seguridad del enunciado:
- Contrasenas nunca se guardan en texto plano (hash con bcrypt).
- Sesiones mediante tokens JWT firmados.
- Cifrado del contenido (imagenes y textos) en reposo con Fernet (AES).
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings


# ---------------------------------------------------------------------------
# Contrasenas
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contrasena."""
    # bcrypt trabaja sobre bytes y limita a 72 bytes; se trunca por seguridad.
    pwd = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Comprueba si una contrasena coincide con su hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tokens JWT
# ---------------------------------------------------------------------------
def create_access_token(data: dict) -> str:
    """Crea un token JWT firmado con los datos del usuario y una expiracion."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Valida y decodifica un token JWT. Devuelve None si es invalido o expiro."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------------------
# Cifrado de contenido en reposo
# ---------------------------------------------------------------------------
def _get_fernet() -> Fernet:
    """Obtiene el cifrador Fernet a partir de la clave configurada."""
    key = settings.ENCRYPTION_KEY
    if not key:
        # En desarrollo, si no hay clave, se genera una temporal.
        key = Fernet.generate_key().decode("utf-8")
        settings.ENCRYPTION_KEY = key
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


def encrypt_text(texto: str) -> str:
    """Cifra un texto y devuelve el resultado en base64."""
    return _get_fernet().encrypt(texto.encode("utf-8")).decode("utf-8")


def decrypt_text(token: str) -> str:
    """Descifra un texto previamente cifrado con encrypt_text."""
    return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def generate_encryption_key() -> str:
    """Genera una clave de cifrado valida (para ponerla en el archivo .env)."""
    return Fernet.generate_key().decode("utf-8")
