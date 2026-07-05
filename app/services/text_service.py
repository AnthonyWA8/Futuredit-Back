"""
Servicio de edicion de contenido con IA.

Implementa las operaciones de texto que pide el enunciado:
- resumir texto
- expandir/ampliar ideas
- corregir errores gramaticales y de estilo
- generar variaciones del contenido

Proveedor por defecto: Groq (Llama), que es ejecutable de inmediato con una
clave gratuita. El codigo esta preparado para cambiar a Claude en Amazon
Bedrock cambiando la variable TEXT_PROVIDER a "bedrock" (ver bedrock_notes.md).
"""

from app.core.config import settings
from app.services.moderation import revisar_texto

# Instrucciones base para cada operacion de edicion.
_PROMPTS = {
    "resumir": (
        "Resume el siguiente texto conservando las ideas principales. "
        "Se claro y conciso, en el mismo idioma del texto original."
    ),
    "expandir": (
        "Amplia y desarrolla el siguiente texto, agregando detalles y ejemplos "
        "relevantes, sin cambiar su intencion ni su idioma."
    ),
    "corregir": (
        "Corrige los errores gramaticales, ortograficos y de estilo del siguiente "
        "texto. Devuelve unicamente el texto corregido, en el mismo idioma."
    ),
    "variacion": (
        "Genera una variacion creativa del siguiente texto, con otras palabras y "
        "estructura pero conservando el mensaje y el idioma original."
    ),
}


def _generar_con_groq(system: str, texto_usuario: str) -> str:
    """Llama a la API de Groq para procesar el texto."""
    from groq import Groq

    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "Falta GROQ_API_KEY. Configura la clave en el archivo .env o cambia "
            "TEXT_PROVIDER a otro proveedor."
        )
    client = Groq(api_key=settings.GROQ_API_KEY)
    respuesta = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": texto_usuario},
        ],
        temperature=0.5,
        max_tokens=1500,
    )
    return respuesta.choices[0].message.content.strip()


def _generar_con_bedrock(system: str, texto_usuario: str) -> str:
    """
    Llama a Claude a traves de Amazon Bedrock.

    Requiere tener configuradas las credenciales de AWS y acceso al modelo en
    Bedrock. Ver bedrock_notes.md para el detalle de configuracion.
    """
    import json

    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "system": system,
        "messages": [{"role": "user", "content": texto_usuario}],
        "temperature": 0.5,
    }
    resp = client.invoke_model(
        modelId=settings.BEDROCK_TEXT_MODEL,
        body=json.dumps(body),
    )
    data = json.loads(resp["body"].read())
    return data["content"][0]["text"].strip()


def procesar_texto(operacion: str, texto: str) -> str:
    """
    Aplica una operacion de edicion sobre un texto.

    operacion: "resumir" | "expandir" | "corregir" | "variacion"
    """
    if operacion not in _PROMPTS:
        raise ValueError(f"Operacion no soportada: {operacion}")

    # El texto de entrada pasa por moderacion antes de enviarse al modelo.
    revisar_texto(texto)

    system = _PROMPTS[operacion]

    if settings.TEXT_PROVIDER == "bedrock":
        resultado = _generar_con_bedrock(system, texto)
    else:
        resultado = _generar_con_groq(system, texto)

    # La salida tambien se revisa, por seguridad.
    revisar_texto(resultado)
    return resultado
