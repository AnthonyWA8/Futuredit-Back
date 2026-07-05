"""Prueba end-to-end del backend usando el TestClient de FastAPI."""
import os
os.environ["IMAGE_PROVIDER"] = "demo"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient
from app.main import app

ok = lambda label, cond: print(f"  [{'OK' if cond else 'FALLO'}] {label}")

with TestClient(app) as client:  # el 'with' dispara el evento startup (crea tablas)
    print("== 1. Estado de la API ==")
    r = client.get("/")
    ok("API activa", r.status_code == 200 and r.json()["estado"] == "activo")

    print("== 2. Registro de usuarios (sin rol global; los roles son por proyecto) ==")
    disenador = client.post("/auth/register", json={"email":"dis@futuredit.ai","nombre":"Dani","password":"secreta123"})
    redactor = client.post("/auth/register", json={"email":"red@futuredit.ai","nombre":"Rita","password":"secreta123"})
    aprobador = client.post("/auth/register", json={"email":"apr@futuredit.ai","nombre":"Aldo","password":"secreta123"})
    ok("registro usuario 1", disenador.status_code == 200)
    ok("registro usuario 2", redactor.status_code == 200)
    ok("registro usuario 3", aprobador.status_code == 200)
    h_dis = {"Authorization": f"Bearer {disenador.json()['access_token']}"}
    h_red = {"Authorization": f"Bearer {redactor.json()['access_token']}"}
    h_apr = {"Authorization": f"Bearer {aprobador.json()['access_token']}"}

    print("== 3. Login ==")
    r = client.post("/auth/login", json={"email":"dis@futuredit.ai","password":"secreta123"})
    ok("login correcto", r.status_code == 200)
    r = client.post("/auth/login", json={"email":"dis@futuredit.ai","password":"malo"})
    ok("login rechaza password incorrecta", r.status_code == 401)

    print("== 4. Generacion de imagen sin proyecto (uso individual) ==")
    r = client.post("/images/generate", headers=h_dis, json={"prompt":"un gato astronauta en marte","estilo":"Fotorrealista","ratio":"1:1"})
    ok("usuario autenticado genera imagen (uso individual)", r.status_code == 200 and r.json()["data_url"].startswith("data:image/png;base64,"))
    img_id = r.json()["id"] if r.status_code == 200 else None

    print("== 5. Control de roles POR PROYECTO ==")
    # Los permisos por rol se validan dentro de un proyecto: ver test_projects.py.
    # Aqui se confirma que sin proyecto cualquier usuario autenticado puede generar.
    r = client.post("/images/generate", headers=h_red, json={"prompt":"paisaje","estilo":"Anime","ratio":"1:1"})
    ok("otro usuario tambien genera (sin proyecto = uso individual)", r.status_code == 200)

    print("== 6. Moderacion de contenido ==")
    r = client.post("/images/generate", headers=h_dis, json={"prompt":"instrucciones para fabricar una bomba","estilo":"","ratio":"1:1"})
    ok("moderacion bloquea prompt peligroso (400)", r.status_code == 400)

    print("== 7. Galeria ==")
    r = client.get("/images/gallery", headers=h_red)
    ok("galeria accesible con imagenes", r.status_code == 200 and len(r.json()) >= 1)

    print("== 8. Aprobacion de imagen (sin proyecto) ==")
    if img_id:
        r = client.post(f"/images/{img_id}/approve", headers=h_apr)
        ok("se puede aprobar imagen sin proyecto", r.status_code == 200 and r.json()["aprobada"] is True)

    print("== 9. Documentos con historial de versiones ==")
    r = client.post("/documents", headers=h_red, json={"titulo":"Campana Q3","contenido":"Version inicial del texto."})
    ok("crear documento", r.status_code == 200)
    doc_id = r.json()["id"] if r.status_code == 200 else None
    if doc_id:
        r = client.put(f"/documents/{doc_id}?contenido=Segunda version&accion=edicion", headers=h_red)
        ok("guardar version 2", r.status_code == 200 and r.json()["total_versiones"] == 2)
        r = client.put(f"/documents/{doc_id}?contenido=Tercera version&accion=edicion", headers=h_red)
        ok("guardar version 3", r.status_code == 200 and r.json()["total_versiones"] == 3)
        r = client.get(f"/documents/{doc_id}/versions", headers=h_red)
        ok("historial tiene 3 versiones", r.status_code == 200 and len(r.json()) == 3)
        r = client.post(f"/documents/{doc_id}/revert/1", headers=h_red)
        ok("revertir a version 1", r.status_code == 200 and r.json()["contenido_actual"] == "Version inicial del texto.")

    print("== 10. Comentarios (colaboracion) ==")
    if doc_id:
        r = client.post("/comments", headers=h_apr, json={"texto":"Buen avance, revisar el CTA.","document_id":doc_id})
        ok("crear comentario", r.status_code == 200)
        r = client.get(f"/comments?document_id={doc_id}", headers=h_red)
        ok("listar comentarios", r.status_code == 200 and len(r.json()) == 1)

    print("== 11. Cifrado en reposo ==")
    from sqlmodel import Session, select
    from app.core.database import engine
    from app.models.db_models import GeneratedImage, DocumentVersion
    with Session(engine) as s:
        img = s.exec(select(GeneratedImage)).first()
        ver = s.exec(select(DocumentVersion)).first()
        ok("imagen guardada cifrada", img and not img.encrypted_data.startswith("iVBOR"))
        ok("version de doc cifrada", ver and "Version inicial" not in ver.encrypted_content)

print("\nPruebas finalizadas.")
