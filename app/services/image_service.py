"""
Servicio de generacion de imagenes.

El enunciado pide generar imagenes con Stable Diffusion (a traves de Amazon
Bedrock). Para que el proyecto sea ejecutable y probable sin depender de una
cuenta de AWS, se implementa un sistema de proveedores conmutable:

- "huggingface": genera imagenes REALES con Stable Diffusion a traves de la
  Inference API de Hugging Face. Es la opcion recomendada para la version
  ejecutable: usa IA de verdad y solo requiere un token gratuito.
- "demo": genera una imagen local determinista a partir del prompt (sin claves
  ni servicios externos). Sirve como respaldo para probar el flujo completo
  (interfaz -> backend -> almacenamiento cifrado -> galeria) si no se dispone de
  token de Hugging Face.
- "bedrock": usa Stable Diffusion XL en Amazon Bedrock (equivalente al enunciado).
- "stability": usa la API de Stability AI directamente.

Todas las variantes devuelven la imagen como bytes PNG, que luego se cifran
antes de guardarse.
"""

import base64
import hashlib
import io

from app.core.config import settings

# Modificadores de estilo que se anaden al prompt para orientar la generacion.
# Cubren los ejemplos del enunciado (anime, pintura al oleo, realismo).
_ESTILOS = {
    "Fotorrealista": "photorealistic, highly detailed, natural lighting, 8k",
    "Realismo": "realistic style, precise details, natural lighting",
    "Anime": "anime style, cel shading, clean lines, vibrant colors",
    "Pintura al oleo": "oil painting, visible brushstrokes, canvas texture",
    "Acuarela": "watercolor, soft colors, blurred edges, artistic",
    "Arte Digital": "digital art, modern illustration, saturated colors",
    "Cinematografico": "cinematic style, dramatic lighting, wide angle",
    "Render 3D": "3D render, studio lighting, realistic materials",
    "Ilustracion": "illustration, editorial style, clean composition",
    "Abstracto": "abstract art, geometric shapes, creative composition",
}

# Relaciones de aspecto y sus dimensiones.
_RATIOS = {
    "1:1": (768, 768), "16:9": (896, 512), "9:16": (512, 896),
    "4:3": (800, 600), "3:4": (600, 800),
}


# ---------------------------------------------------------------------------
# Proveedor recomendado: Hugging Face (Stable Diffusion real)
# ---------------------------------------------------------------------------
def _generar_huggingface(prompt: str, estilo: str, ratio: str, negative_prompt: str) -> bytes:
    """
    Genera una imagen real con Stable Diffusion mediante la Inference API de
    Hugging Face. Requiere un token gratuito (variable HF_API_TOKEN).
    """
    import os

    import requests

    token = os.environ.get("HF_API_TOKEN", "")
    if not token:
        raise RuntimeError(
            "Falta HF_API_TOKEN. Consigue un token gratuito en "
            "https://huggingface.co/settings/tokens y ponlo en el archivo .env."
        )

    modelo = settings.HF_IMAGE_MODEL
    url = f"https://api-inference.huggingface.co/models/{modelo}"

    modificador = _ESTILOS.get(estilo, "")
    prompt_final = f"{prompt}, {modificador}" if modificador else prompt
    width, height = _RATIOS.get(ratio, (768, 768))

    payload = {
        "inputs": prompt_final,
        "parameters": {
            "width": width,
            "height": height,
        },
    }
    if negative_prompt.strip():
        payload["parameters"]["negative_prompt"] = negative_prompt

    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "image/png"},
        json=payload,
        timeout=120,
    )
    # La API responde con la imagen en binario si todo va bien.
    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
        return resp.content

    # Si el modelo se esta cargando, Hugging Face devuelve un JSON con el estado.
    try:
        detalle = resp.json()
    except Exception:
        detalle = resp.text
    raise RuntimeError(f"Hugging Face devolvio un error ({resp.status_code}): {detalle}")


# ---------------------------------------------------------------------------
# Respaldo: modo demo (sin dependencias externas)
# ---------------------------------------------------------------------------
def _color_desde_texto(texto: str, offset: int = 0) -> tuple[int, int, int]:
    """Deriva un color RGB determinista a partir de un texto (modo demo)."""
    h = hashlib.sha256((texto + str(offset)).encode("utf-8")).hexdigest()
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _generar_demo(prompt: str, estilo: str, ratio: str) -> bytes:
    """
    Genera una imagen ilustrativa (degradado + texto) de forma local.

    ATENCION: esto NO es una imagen generada por IA. Es un marcador de posicion
    determinista cuyo unico proposito es permitir probar el flujo completo de la
    aplicacion sin depender de un servicio externo. Para generacion real con IA,
    usar el proveedor "huggingface" o "bedrock".
    """
    from PIL import Image, ImageDraw, ImageFont

    w, h = _RATIOS.get(ratio, (768, 768))
    c1 = _color_desde_texto(prompt, 0)
    c2 = _color_desde_texto(prompt + estilo, 1)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x + y) / (w + h)
            px[x, y] = (
                int(c1[0] * (1 - t) + c2[0] * t),
                int(c1[1] * (1 - t) + c2[1] * t),
                int(c1[2] * (1 - t) + c2[2] * t),
            )
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    draw.rectangle([0, h - 70, w, h], fill=(0, 0, 0))
    draw.text((16, h - 60), f"[DEMO] {estilo}", fill=(255, 255, 255), font=font)
    prompt_corto = (prompt[:60] + "...") if len(prompt) > 60 else prompt
    draw.text((16, h - 32), prompt_corto, fill=(200, 200, 200), font=font_small)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Equivalentes al enunciado (documentados y listos para activar)
# ---------------------------------------------------------------------------
def _generar_bedrock(prompt: str, estilo: str, ratio: str, negative_prompt: str) -> bytes:
    """Genera una imagen con Stable Diffusion XL en Amazon Bedrock."""
    import json

    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
    modificador = _ESTILOS.get(estilo, "")
    prompt_final = f"{prompt}, {modificador}" if modificador else prompt
    text_prompts = [{"text": prompt_final, "weight": 1.0}]
    if negative_prompt.strip():
        text_prompts.append({"text": negative_prompt, "weight": -1.0})
    body = {"text_prompts": text_prompts, "cfg_scale": 8, "steps": 30, "seed": 0}
    resp = client.invoke_model(modelId=settings.BEDROCK_IMAGE_MODEL, body=json.dumps(body))
    data = json.loads(resp["body"].read())
    return base64.b64decode(data["artifacts"][0]["base64"])


def _generar_stability(prompt: str, estilo: str, ratio: str) -> bytes:
    """Genera una imagen con la API de Stability AI."""
    import os

    import requests

    api_key = os.environ.get("STABILITY_API_KEY", "")
    if not api_key:
        raise RuntimeError("Falta STABILITY_API_KEY para el proveedor 'stability'.")
    modificador = _ESTILOS.get(estilo, "")
    prompt_final = f"{prompt}, {modificador}" if modificador else prompt
    resp = requests.post(
        "https://api.stability.ai/v2beta/stable-image/generate/core",
        headers={"authorization": f"Bearer {api_key}", "accept": "image/*"},
        files={"none": ""},
        data={"prompt": prompt_final, "output_format": "png"},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def generar_imagen(
    prompt: str, estilo: str = "", ratio: str = "1:1", negative_prompt: str = ""
) -> bytes:
    """
    Genera una imagen segun el proveedor configurado y devuelve los bytes PNG.
    """
    proveedor = settings.IMAGE_PROVIDER
    if proveedor == "huggingface":
        return _generar_huggingface(prompt, estilo, ratio, negative_prompt)
    if proveedor == "bedrock":
        return _generar_bedrock(prompt, estilo, ratio, negative_prompt)
    if proveedor == "stability":
        return _generar_stability(prompt, estilo, ratio)
    # Por defecto: modo demo (sin dependencias externas).
    return _generar_demo(prompt, estilo, ratio)
