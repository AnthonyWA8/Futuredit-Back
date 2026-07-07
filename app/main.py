"""
Aplicacion principal de Futuredit (FastAPI).

Une todos los modulos y expone la API que consume el frontend. Al arrancar,
crea las tablas de la base de datos y configura CORS para permitir la conexion
desde el frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, comments, documents, images, projects, text
from app.core.config import settings
from app.core.database import init_db

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend de Futuredit: generacion de imagenes, edicion de contenido con "
        "IA, colaboracion con roles, historial de versiones y moderacion de "
        "contenido. Compatible con Amazon Bedrock (Claude y Stable Diffusion)."
    ),
)

# CORS: permite que el frontend (local o desplegado en Vercel) llame a la API.
# - allow_origins: lista explicita (localhost y las URLs que definas en CORS_ORIGINS).
# - allow_origin_regex: acepta automaticamente cualquier subdominio de vercel.app,
#   lo que cubre el dominio de produccion y las URLs de preview sin tener que
#   escribirlas una por una.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", tags=["General"])
def root():
    """Endpoint de estado para comprobar que la API esta activa."""
    from app.core.database import DB_TYPE

    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "estado": "activo",
        "base_de_datos": DB_TYPE,
        "proveedor_texto": settings.TEXT_PROVIDER,
        "proveedor_imagen": settings.IMAGE_PROVIDER,
    }


# Registro de los routers de cada modulo.
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(images.router)
app.include_router(text.router)
app.include_router(documents.router)
app.include_router(comments.router)