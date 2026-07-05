"""
Modelos de base de datos (SQLModel / SQLite o PostgreSQL).

Definen las entidades del sistema. El modelo de colaboracion se basa en roles
POR PROYECTO: un usuario no tiene un rol global, sino un rol distinto en cada
proyecto del que forma parte. Quien crea un proyecto queda como administrador
de ese proyecto y puede asignar roles a los demas miembros; otros usuarios
pueden unirse mediante un codigo de invitacion.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    """
    Roles que un usuario puede tener DENTRO de un proyecto.

    - ADMIN: crea el proyecto, asigna roles, aprueba y gestiona todo.
    - DISENADOR: genera y edita imagenes.
    - REDACTOR: genera y edita contenido de texto.
    - APROBADOR: revisa y aprueba/rechaza el trabajo.
    """
    ADMIN = "admin"
    DISENADOR = "disenador"
    REDACTOR = "redactor"
    APROBADOR = "aprobador"


class User(SQLModel, table=True):
    """Cuenta de usuario. El rol NO vive aqui, sino en cada proyecto."""
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    nombre: str
    hashed_password: str
    avatar_url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_now)


class Project(SQLModel, table=True):
    """Proyecto / espacio de trabajo colaborativo."""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    descripcion: str = ""
    # Codigo unico que permite a otros usuarios unirse al proyecto.
    codigo_invitacion: str = Field(index=True, unique=True)
    owner_id: int = Field(foreign_key="user.id")
    estado: str = Field(default="active")  # active | review | draft
    color: str = Field(default="#7c3aed")
    created_at: datetime = Field(default_factory=_now)


class ProjectMember(SQLModel, table=True):
    """
    Membresia de un usuario en un proyecto, con su rol en ESE proyecto.

    Esta es la tabla que implementa los roles por proyecto: la misma persona
    puede ser 'admin' en un proyecto y 'redactor' en otro.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: Role = Field(default=Role.REDACTOR)
    joined_at: datetime = Field(default_factory=_now)


class GeneratedImage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    author_id: int = Field(foreign_key="user.id")
    prompt: str
    negative_prompt: str = ""
    estilo: str = ""
    ratio: str = "1:1"
    # La imagen se guarda cifrada (base64 cifrado) para proteger el contenido.
    encrypted_data: str
    mime: str = "image/png"
    aprobada: bool = False
    created_at: datetime = Field(default_factory=_now)


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    author_id: int = Field(foreign_key="user.id")
    titulo: str = "Documento sin titulo"
    created_at: datetime = Field(default_factory=_now)


class DocumentVersion(SQLModel, table=True):
    """
    Cada cambio en un documento crea una version nueva, lo que permite el
    historial y la reversion de cambios.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id")
    version_num: int
    encrypted_content: str
    accion: str = "edicion"
    author_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=_now)


class Comment(SQLModel, table=True):
    """Comentarios para la colaboracion y retroalimentacion."""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    document_id: Optional[int] = Field(default=None, foreign_key="document.id")
    image_id: Optional[int] = Field(default=None, foreign_key="generatedimage.id")
    author_id: int = Field(foreign_key="user.id")
    texto: str
    created_at: datetime = Field(default_factory=_now)
