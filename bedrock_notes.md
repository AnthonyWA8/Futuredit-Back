# Migración a Amazon Bedrock

El enunciado pide usar **Amazon Bedrock** con **Claude** (texto) y **Stable
Diffusion** (imágenes). El backend ya está preparado para ello: solo hay que
cambiar dos variables de entorno y tener una cuenta de AWS con acceso a Bedrock.
El código de integración ya está escrito en los servicios.

## Por qué el proyecto trae, además, proveedores alternativos

Amazon Bedrock requiere una cuenta de AWS con facturación activa y solicitud de
acceso a los modelos, algo que no siempre está disponible durante el desarrollo
o la evaluación. Por eso el backend incluye proveedores que funcionan de
inmediato (Groq para texto, modo *demo* para imágenes), y deja Bedrock listo
para activarse. Así se puede probar toda la aplicación hoy y migrar a Bedrock
sin reescribir nada.

## Paso 1 — Requisitos en AWS

1. Cuenta de AWS con acceso a **Amazon Bedrock** en una región soportada
   (por ejemplo `us-east-1`).
2. En la consola de Bedrock, solicitar acceso a los modelos:
   - **Anthropic Claude 3.5 Sonnet** (texto).
   - **Stability AI Stable Diffusion XL** (imágenes).
3. Credenciales de AWS configuradas en el entorno (por ejemplo con
   `aws configure`, o variables `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`).

## Paso 2 — Instalar boto3

```bash
pip install boto3
```

(Está comentado en `requirements.txt`; basta con descomentarlo.)

## Paso 3 — Cambiar la configuración

En el archivo `.env`:

```
TEXT_PROVIDER=bedrock
IMAGE_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_TEXT_MODEL=anthropic.claude-3-5-sonnet-20240620-v1:0
BEDROCK_IMAGE_MODEL=stability.stable-diffusion-xl-v1
```

Con eso, el servicio de texto usará Claude y el de imágenes usará Stable
Diffusion, ambos a través de Bedrock. No hay que cambiar ninguna otra línea de
código: las funciones `_generar_con_bedrock` (en `text_service.py`) y
`_generar_bedrock` (en `image_service.py`) ya están implementadas.

## Cómo funciona la llamada a Claude en Bedrock

El servicio de texto arma una petición con el formato de mensajes de Anthropic
y la envía con `bedrock-runtime.invoke_model`. La respuesta trae el texto
generado en `content[0].text`.

## Cómo funciona la llamada a Stable Diffusion en Bedrock

El servicio de imágenes envía el prompt (más el estilo) al modelo de Stability
en Bedrock y recibe la imagen en base64, que luego se cifra y se guarda igual
que en el modo demo.

## Equivalencia de proveedores

| Función | Alternativa ejecutable | Amazon Bedrock (enunciado) |
|---|---|---|
| Edición de texto | Groq (Llama 3.1) | Claude 3.5 Sonnet |
| Generación de imágenes | Modo demo / Stability AI | Stable Diffusion XL |

La lógica de negocio (roles, moderación, cifrado, versiones, comentarios) es
idéntica en ambos casos: solo cambia el motor de IA que hay detrás.
