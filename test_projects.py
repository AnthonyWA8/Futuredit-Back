"""Prueba end-to-end del flujo de proyectos y roles por proyecto."""
import os
os.environ["SECRET_KEY"] = "test-secret"
os.environ["IMAGE_PROVIDER"] = "demo"
os.environ.pop("DATABASE_URL", None)

from fastapi.testclient import TestClient
from app.main import app

ok = lambda label, cond: print(f"  [{'OK' if cond else 'FALLO'}] {label}")

with TestClient(app) as c:
    # Registrar 3 usuarios
    ana = c.post("/auth/register", json={"email":"ana@f.com","nombre":"Ana","password":"secreta123"}).json()
    beto = c.post("/auth/register", json={"email":"beto@f.com","nombre":"Beto","password":"secreta123"}).json()
    caro = c.post("/auth/register", json={"email":"caro@f.com","nombre":"Caro","password":"secreta123"}).json()
    hA = {"Authorization": f"Bearer {ana['access_token']}"}
    hB = {"Authorization": f"Bearer {beto['access_token']}"}
    hC = {"Authorization": f"Bearer {caro['access_token']}"}
    ok("registro sin rol global", "access_token" in ana and "role" not in ana)

    print("== Crear proyecto (Ana = admin automatico) ==")
    r = c.post("/projects", headers=hA, json={"nombre":"Campana Q3","descripcion":"test","color":"#7c3aed"})
    proj = r.json()
    ok("proyecto creado", r.status_code == 200)
    ok("Ana es admin del proyecto", proj["mi_rol"] == "admin")
    ok("tiene codigo de invitacion", proj["codigo_invitacion"].startswith("FTX-"))
    ok("Ana es el unico miembro", proj["total_miembros"] == 1)
    pid = proj["id"]
    codigo = proj["codigo_invitacion"]

    print("== Beto y Caro se unen por codigo ==")
    r = c.post("/projects/join", headers=hB, json={"codigo_invitacion": codigo})
    ok("Beto se une", r.status_code == 200 and r.json()["mi_rol"] == "redactor")
    r = c.post("/projects/join", headers=hC, json={"codigo_invitacion": codigo})
    ok("Caro se une", r.status_code == 200)
    r = c.post("/projects/join", headers=hB, json={"codigo_invitacion": "FTX-NOEXISTE"})
    ok("codigo invalido rechazado", r.status_code == 404)

    print("== Miembros del proyecto ==")
    r = c.get(f"/projects/{pid}/members", headers=hA)
    ok("3 miembros", r.status_code == 200 and len(r.json()) == 3)

    print("== Ana (admin) asigna roles ==")
    r = c.post(f"/projects/{pid}/assign-role", headers=hA, json={"user_id": beto["user_id"], "role": "disenador"})
    ok("Beto ahora es disenador", r.status_code == 200 and r.json()["role"] == "disenador")
    r = c.post(f"/projects/{pid}/assign-role", headers=hA, json={"user_id": caro["user_id"], "role": "aprobador"})
    ok("Caro ahora es aprobador", r.status_code == 200 and r.json()["role"] == "aprobador")

    print("== Control de permisos por proyecto ==")
    # Beto (disenador) puede generar imagen en el proyecto
    r = c.post("/images/generate", headers=hB, json={"prompt":"un logo","estilo":"Anime","ratio":"1:1","project_id":pid})
    ok("Beto (disenador) genera imagen en el proyecto", r.status_code == 200)
    img_id = r.json()["id"] if r.status_code == 200 else None
    # Caro (aprobador) NO puede generar imagen
    r = c.post("/images/generate", headers=hC, json={"prompt":"otro logo","estilo":"Anime","ratio":"1:1","project_id":pid})
    ok("Caro (aprobador) NO puede generar imagen (403)", r.status_code == 403)
    # Caro (aprobador) SI puede aprobar
    if img_id:
        r = c.post(f"/images/{img_id}/approve", headers=hC)
        ok("Caro (aprobador) aprueba imagen", r.status_code == 200 and r.json()["aprobada"])
    # Beto (disenador) NO puede aprobar
    if img_id:
        r = c.post(f"/images/{img_id}/approve", headers=hB)
        ok("Beto (disenador) NO puede aprobar (403)", r.status_code == 403)

    print("== Beto NO admin no puede asignar roles ==")
    r = c.post(f"/projects/{pid}/assign-role", headers=hB, json={"user_id": caro["user_id"], "role": "redactor"})
    ok("Beto (no admin) no puede asignar roles (403)", r.status_code == 403)

    print("== Roles por proyecto: Beto crea su propio proyecto y es admin ahi ==")
    r = c.post("/projects", headers=hB, json={"nombre":"Proyecto de Beto"})
    ok("Beto es admin en SU proyecto", r.status_code == 200 and r.json()["mi_rol"] == "admin")

    print("== Mis proyectos ==")
    r = c.get("/projects", headers=hB)
    ok("Beto ve sus 2 proyectos con roles distintos", r.status_code == 200 and len(r.json()) == 2)
    roles_beto = sorted(p["mi_rol"] for p in r.json())
    ok("Beto: disenador en uno, admin en otro", roles_beto == ["admin","disenador"])

    print("== Galeria del proyecto ==")
    r = c.get(f"/images/gallery?project_id={pid}", headers=hA)
    ok("galeria del proyecto accesible", r.status_code == 200 and len(r.json()) >= 1)

print("\nPruebas de proyectos finalizadas.")
