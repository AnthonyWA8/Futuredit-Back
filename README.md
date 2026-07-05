# Futuredit — Backend

Backend de la aplicación **Futuredit**: una herramienta de generación de
imágenes y edición de contenido con IA generativa para equipos de marketing y
publicidad. Desarrollado con **Python + FastAPI**.

Este backend da vida al frontend ya existente, implementando de forma **real**
(no simulada) las cuatro áreas que pide el proyecto:

1. **Generación de imágenes** a partir de descripciones de texto, con estilos y
   relación de aspecto, galería y descarga.
2. **Edición de contenido** con IA: resumir, expandir, corregir y generar
   variaciones.
3. **Colaboración y flujo de trabajo**: usuarios con roles y permisos
   (diseñador, redactor, aprobador), comentarios e historial de versiones.
4. **Ética y seguridad**: moderación de contenido, cifrado en reposo,
   autenticación con tokens y manejo seguro de credenciales.

## Compatibilidad con Amazon Bedrock

El enunciado pide usar Amazon Bedrock con Claude y Stable Diffusion. El backend
está preparado para ello: la integración con Bedrock ya está escrita y se activa
cambiando dos variables de entorno (ver `bedrock_notes.md`). Para poder ejecutar
y probar el proyecto sin una cuenta de AWS, trae proveedores alternativos que
funcionan de inmediato:

- **Texto**: Groq (Llama 3.1) por defecto → Claude en Bedrock al activarlo.
- **Imágenes**: modo *demo* local por defecto → Stable Diffusion en Bedrock al
  activarlo.

## Estructura

```
futuredit-backend/
├── app/
│   ├── main.py              Aplicación FastAPI (une todo)
│   ├── core/
│   │   ├── config.py        Configuración desde variables de entorno
│   │   ├── database.py      Conexión a BD (PostgreSQL o SQLite de respaldo)
│   │   └── security.py      Hashing, JWT y cifrado
│   ├── models/
│   │   ├── db_models.py     Tablas: usuarios, proyectos, imágenes, docs...
│   │   └── schemas.py       Esquemas de petición/respuesta
│   ├── services/
│   │   ├── text_service.py  Edición de texto (Groq / Claude-Bedrock)
│   │   ├── image_service.py Generación de imágenes (demo / Bedrock / Stability)
│   │   └── moderation.py    Filtrado de contenido inapropiado
│   ├── api/
│   │   ├── auth.py          Registro y login
│   │   ├── projects.py      Proyectos, roles por proyecto, códigos
│   │   ├── images.py        Generar, galería, aprobar
│   │   ├── text.py          Editar contenido con IA
│   │   ├── documents.py     Documentos + historial de versiones
│   │   ├── comments.py      Comentarios (colaboración)
│   │   └── deps.py          Autenticación y control de roles por proyecto
│   └── tools/genkey.py      Genera la clave de cifrado
├── requirements.txt
├── .env.example
├── bedrock_notes.md         Cómo migrar a Amazon Bedrock
└── test_e2e.py              Prueba end-to-end de todo el backend
```

## Instalación y ejecución

1. Crea un entorno virtual e instala dependencias:

   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Configura el entorno. Copia la plantilla y complétala:

   ```bash
   cp .env.example .env
   ```

   - Genera una clave de cifrado y ponla en `ENCRYPTION_KEY`:

     ```bash
     python -m app.tools.genkey
     ```

   - Pon tu clave de Groq en `GROQ_API_KEY` (gratis en https://console.groq.com).
     Si no la pones, todo funciona salvo la edición de texto.

3. Arranca el servidor:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Abre la documentación interactiva de la API en:

   ```
   http://localhost:8000/docs
   ```

   Desde ahí puedes probar todos los endpoints (registrar usuarios, generar
   imágenes, editar texto, etc.) sin necesidad del frontend.

## Base de datos

El sistema usa **PostgreSQL** como base de datos principal (recomendado, ya que
el enunciado requiere soportar múltiples usuarios simultáneos). Si no se
configura PostgreSQL, el sistema recurre automáticamente a **SQLite** como
respaldo, de modo que el proyecto siempre puede ejecutarse.

La base se elige mediante la variable `DATABASE_URL` en el archivo `.env`:

**Opción A — PostgreSQL local:**

```
DATABASE_URL=postgresql://postgres:tu_clave@localhost:5432/futuredit
```

Antes, crea la base de datos una vez:

```bash
createdb -U postgres futuredit
```

**Opción B — Supabase (recomendada para entregar o desplegar):**

1. Crea un proyecto gratuito en https://supabase.com
2. Ve a *Project Settings > Database > Connection string > URI*.
3. Copia la URL y reemplaza `[YOUR-PASSWORD]` por la clave de tu base:

```
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[REF].supabase.co:5432/postgres
```

**Opción C — SQLite (respaldo automático):**

Si dejas `DATABASE_URL` vacía, el sistema usa un archivo `futuredit.db` local.
Útil para pruebas rápidas sin instalar nada.

En todos los casos, las tablas se crean automáticamente al arrancar la
aplicación; no hay que ejecutar migraciones manualmente. Como el proyecto está
construido con SQLModel (sobre SQLAlchemy), el mismo código funciona con
cualquiera de los tres motores sin cambios.

Puedes comprobar qué base está en uso consultando el endpoint de estado
(`GET /`), que devuelve el campo `base_de_datos` con el valor `postgresql` o
`sqlite`.

## Autenticación y roles por proyecto

El acceso se gestiona con correo y contraseña. Las contraseñas se guardan como
hash con bcrypt (nunca en texto plano) y las sesiones se manejan con tokens JWT.

Los **roles son por proyecto**, no globales. Esto significa que un mismo usuario
puede tener un rol distinto en cada proyecto del que forma parte:

- Quien **crea** un proyecto queda automáticamente como **administrador** de ese
  proyecto, y se genera un **código de invitación** único (por ejemplo `FTX-7K2Q9`).
- Otros usuarios pueden **unirse** al proyecto con ese código (entran con rol
  `redactor` por defecto).
- El administrador puede **asignar o cambiar el rol** de cada miembro:
  `disenador`, `redactor`, `aprobador` o `admin`.
- El sistema garantiza que un proyecto siempre tenga al menos un administrador.

Los permisos se aplican según el rol dentro del proyecto:

- **disenador**: genera y edita imágenes en el proyecto.
- **redactor**: crea y edita contenido de texto.
- **aprobador**: revisa y aprueba las imágenes.
- **admin**: todo lo anterior, más gestionar miembros y roles.

Cuando una acción se hace sin proyecto (uso individual), basta con estar
autenticado. Cuando se hace dentro de un proyecto, se valida el rol del usuario
en ese proyecto.

## Prueba automática

Para verificar que todo funciona de extremo a extremo:

```bash
python test_e2e.py
```

Comprueba registro con roles, login, generación de imágenes, control de
permisos, moderación, galería, aprobación, documentos con versiones, reversión,
comentarios y cifrado en reposo.

## Endpoints principales

| Método | Ruta | Descripción | Permiso |
|---|---|---|---|
| POST | `/auth/register` | Registrar usuario | — |
| POST | `/auth/login` | Iniciar sesión | — |
| GET | `/auth/me` | Datos del usuario actual | autenticado |
| POST | `/projects` | Crear proyecto (te vuelve admin + genera código) | autenticado |
| GET | `/projects` | Mis proyectos con mi rol en cada uno | autenticado |
| POST | `/projects/join` | Unirse a un proyecto por código | autenticado |
| GET | `/projects/{id}/members` | Miembros del proyecto y sus roles | miembro |
| POST | `/projects/{id}/assign-role` | Asignar rol a un miembro | admin del proyecto |
| POST | `/images/generate` | Generar imagen | disenador (en proyecto) |
| GET | `/images/gallery` | Ver galería | autenticado / miembro |
| POST | `/images/{id}/approve` | Aprobar imagen | aprobador (en proyecto) |
| POST | `/text/edit` | Resumir/expandir/corregir/variar | autenticado |
| POST | `/documents` | Crear documento | autenticado |
| PUT | `/documents/{id}` | Guardar versión | autenticado |
| GET | `/documents/{id}/versions` | Historial de versiones | autenticado |
| POST | `/documents/{id}/revert/{n}` | Revertir a versión | autenticado |
| POST | `/comments` | Comentar | autenticado |
| GET | `/comments` | Listar comentarios | autenticado |

## Conexión con el frontend

El frontend (React + Vite) debe apuntar sus llamadas a `http://localhost:8000`.
El backend ya tiene CORS configurado para `http://localhost:5173` (Vite) y
`http://localhost:3000`. Basta con reemplazar en el frontend los datos simulados
por llamadas `fetch` a estos endpoints, enviando el token JWT en la cabecera
`Authorization: Bearer <token>`.
