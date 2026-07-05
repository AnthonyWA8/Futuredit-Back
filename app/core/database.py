"""
Conexion a la base de datos.

El sistema usa PostgreSQL como base de datos principal (recomendado, ya que el
enunciado requiere soportar multiples usuarios simultaneos). Si no se configura
una conexion a PostgreSQL, el sistema recurre automaticamente a SQLite como
respaldo, de modo que el proyecto siempre puede ejecutarse.

La eleccion se hace mediante la configuracion (ver app/core/config.py):
- Si hay una DATABASE_URL de PostgreSQL definida, se usa esa.
- Si no, se usa un archivo SQLite local.

Como el proyecto esta construido con SQLModel (sobre SQLAlchemy), el mismo
codigo de modelos y consultas funciona con ambos motores sin cambios.
"""

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


def _crear_engine():
    """
    Crea el motor de base de datos segun la configuracion.

    Devuelve una tupla (engine, tipo) donde tipo es "postgresql" o "sqlite",
    util para informar al usuario que base se esta usando.
    """
    url = settings.database_url

    if url.startswith("postgresql"):
        # PostgreSQL: pool de conexiones con reciclado, adecuado para
        # multiples usuarios concurrentes.
        engine = create_engine(
            url,
            pool_pre_ping=True,   # verifica la conexion antes de usarla
            pool_size=10,         # conexiones mantenidas en el pool
            max_overflow=20,      # conexiones extra permitidas en picos
            echo=False,
        )
        return engine, "postgresql"

    # SQLite (respaldo): check_same_thread=False para usarlo desde varios hilos.
    engine = create_engine(url, connect_args={"check_same_thread": False}, echo=False)
    return engine, "sqlite"


engine, DB_TYPE = _crear_engine()


def init_db():
    """Crea las tablas si no existen (se llama al arrancar la aplicacion)."""
    # Importar los modelos asegura que SQLModel los registre antes de crear tablas.
    from app.models import db_models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependencia de FastAPI que entrega una sesion de base de datos por peticion."""
    with Session(engine) as session:
        yield session
