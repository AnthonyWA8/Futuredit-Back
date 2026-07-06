"""
Configuracion central de la aplicacion Futuredit.

Todas las opciones se leen desde variables de entorno (archivo .env), de forma
que las credenciales nunca queden escritas en el codigo. Esto es una buena
practica de seguridad exigida por el enunciado.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- General ---
    APP_NAME = "Futuredit API"
    APP_VERSION = "1.0.0"

    # --- Seguridad / JWT ---
    # Clave para firmar los tokens de sesion. En produccion debe ser larga y secreta.
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # Clave de cifrado para el contenido en reposo (imagenes y textos).
    # Si no se define, se genera una temporal al arrancar (solo para desarrollo).
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")


    # --- Proveedor de texto (edicion con IA) ---
    # Opciones: "groq" (por defecto, ejecutable ya) o "bedrock" (Claude en AWS).
    TEXT_PROVIDER = os.environ.get("TEXT_PROVIDER", "groq")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    # --- Proveedor de imagenes ---
    # Opciones: "huggingface" (Stable Diffusion real, recomendado),
    # "demo" (sin claves, respaldo), "bedrock" o "stability".
    IMAGE_PROVIDER = os.environ.get("IMAGE_PROVIDER", "huggingface")

    # --- Hugging Face (generacion de imagenes con Stable Diffusion) ---
    HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")
    HF_IMAGE_MODEL = os.environ.get(
        "HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell"
    )

    # --- Amazon Bedrock (opcional, documentado) ---
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    BEDROCK_TEXT_MODEL = os.environ.get(
        "BEDROCK_TEXT_MODEL", "anthropic.claude-3-5-sonnet-20240620-v1:0"
    )
    BEDROCK_IMAGE_MODEL = os.environ.get(
        "BEDROCK_IMAGE_MODEL", "stability.stable-diffusion-xl-v1"
    )

    # --- CORS (para permitir que el frontend se conecte) ---
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000, https://futuredit-front.vercel.app"
    ).split(",")

    # --- Base de datos ---
    # Forma 1 (recomendada): URL completa de conexion a PostgreSQL.
    #   - Postgres local:  postgresql://usuario:clave@localhost:5432/futuredit
    #   - Supabase:        postgresql://postgres:[CLAVE]@db.[REF].supabase.co:5432/postgres
    # Si DATABASE_URL esta vacia, se usa SQLite como respaldo automatico.
    DATABASE_URL = os.environ.get("DATABASE_URL", "")

    # Archivo SQLite de respaldo (solo se usa si no hay DATABASE_URL).
    SQLITE_FILE = os.environ.get("SQLITE_FILE", "futuredit.db")

    @property
    def database_url(self) -> str:
        """
        Devuelve la URL de conexion definitiva.

        Prioridad:
        1. DATABASE_URL (PostgreSQL: local o Supabase).
        2. SQLite local como respaldo.

        Nota: se normaliza el prefijo 'postgres://' a 'postgresql://', porque
        algunos proveedores (como Supabase o Heroku) entregan la URL con el
        primer formato, que SQLAlchemy ya no acepta directamente.
        """
        url = self.DATABASE_URL.strip() if self.DATABASE_URL else ""

        if url:
            # Error comun: pegar la URL del panel/API de Supabase (https://...)
            # en lugar de la cadena de conexion de la base de datos.
            if url.startswith("http://") or url.startswith("https://"):
                raise ValueError(
                    "DATABASE_URL parece ser una URL web (https://...), no una "
                    "cadena de conexion de PostgreSQL. Debe empezar por "
                    "'postgresql://'. En Supabase, copiala desde "
                    "Project Settings > Database > Connection string > URI. "
                    "Si no quieres usar PostgreSQL, deja DATABASE_URL vacia para "
                    "usar SQLite."
                )
            # Normaliza postgres:// -> postgresql:// (Supabase, Heroku, etc.).
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            # Asegura el driver psycopg2 explicito para evitar ambiguedades.
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return url

        return f"sqlite:///{self.SQLITE_FILE}"


settings = Settings()