"""
Esquemas Pydantic para las peticiones y respuestas de la API.

Separan la forma de los datos que entran y salen de la API de los modelos de
base de datos, lo que es una buena practica de diseno.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.db_models import Role


# --- Autenticacion ---
class RegisterRequest(BaseModel):
    email: EmailStr
    nombre: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str



class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    nombre: str
    email: str


# --- Texto ---
class TextEditRequest(BaseModel):
    operacion: str  # resumir | expandir | corregir | variacion
    texto: str


class TextEditResponse(BaseModel):
    operacion: str
    resultado: str


# --- Imagenes ---
class ImageGenRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    estilo: str = ""
    ratio: str = "1:1"
    project_id: Optional[int] = None


class ImageResponse(BaseModel):
    id: int
    prompt: str
    estilo: str
    ratio: str
    aprobada: bool
    # La imagen se entrega como data URL (base64) lista para mostrar en el frontend.
    data_url: str


# --- Documentos y versiones ---
class DocumentCreateRequest(BaseModel):
    titulo: str = "Documento sin titulo"
    contenido: str = ""
    project_id: Optional[int] = None


class DocumentVersionResponse(BaseModel):
    version_num: int
    accion: str
    contenido: str
    author_id: int
    created_at: str


class DocumentResponse(BaseModel):
    id: int
    titulo: str
    contenido_actual: str
    total_versiones: int


# --- Comentarios ---
class CommentRequest(BaseModel):
    texto: str
    project_id: Optional[int] = None
    document_id: Optional[int] = None
    image_id: Optional[int] = None


class CommentResponse(BaseModel):
    id: int
    autor: str
    texto: str
    created_at: str


# --- Proyectos y membresias ---
class ProjectCreateRequest(BaseModel):
    nombre: str
    descripcion: str = ""
    color: str = "#7c3aed"


class JoinProjectRequest(BaseModel):
    codigo_invitacion: str


class AssignRoleRequest(BaseModel):
    user_id: int
    role: Role


class MemberResponse(BaseModel):
    user_id: int
    nombre: str
    email: str
    role: Role
    avatar_url: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str
    codigo_invitacion: str
    estado: str
    color: str
    mi_rol: Role                 # rol del usuario actual en este proyecto
    total_miembros: int
    total_imagenes: int = 0
    total_documentos: int = 0
    created_at: str
