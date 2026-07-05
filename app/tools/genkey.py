"""Genera una clave de cifrado valida para poner en ENCRYPTION_KEY del .env."""
from app.core.security import generate_encryption_key

if __name__ == "__main__":
    print(generate_encryption_key())
