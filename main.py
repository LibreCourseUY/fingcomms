from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import logging
import secrets

logging.basicConfig(level=logging.DEBUG)
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from database import engine, SessionLocal, Group, ImportantLink, Base, get_db

app = FastAPI(root_path=os.getenv("ROOT_PATH", ""))

logger = logging.getLogger(__name__)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug("REQUEST: %s %s", request.method, request.url.path)
    response = await call_next(request)
    return response


Base.metadata.create_all(bind=engine)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

lockout_data = {}
admin_tokens = set()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def verify_admin(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()

    if token not in admin_tokens:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return True


def verify_admin_origin(request: Request):
    referer = request.headers.get("Referer", "")
    if "/admin" not in referer and "/admin.html" not in referer:
        raise HTTPException(status_code=403, detail="Access denied")


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def fuzzy_match(query: str, text: str, threshold: float = 0.3) -> float:
    query = query.lower()
    text = text.lower()

    if query in text:
        return 1.0

    words = text.split()
    for word in words:
        if query in word:
            return 0.9

    max_score = 0.0
    for word in words:
        if len(word) >= len(query):
            distance = levenshtein_distance(query, word)
            max_len = max(len(query), len(word))
            score = 1 - (distance / max_len)
            if score > max_score:
                max_score = score

    if max_score >= (1 - threshold):
        return max_score
    return 0.0


def fuzzy_search(query: str, groups: List, threshold: float = 0.3):
    results = []
    for group in groups:
        name_score = fuzzy_match(query, group.name, threshold)
        desc_score = fuzzy_match(query, group.description or "", threshold)
        total_score = max(name_score, desc_score * 0.7)

        if total_score > 0:
            results.append((group, total_score))

    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]


class GroupCreate(BaseModel):
    name: str
    description: str = ""
    url: str = ""


class GroupUpdate(BaseModel):
    id: int
    name: str
    description: str
    url: str


class PinGroup(BaseModel):
    group_id: int
    pinned: bool


class AdminLogin(BaseModel):
    password: str


@app.get("/api/groups")
def get_groups(q: Optional[str] = None, db: Session = Depends(get_db)):
    groups = db.query(Group).all()

    if q and q.strip():
        results = fuzzy_search(q, groups)
        return [group_to_dict(g) for g in results]

    pinned = [g for g in groups if g.pinned]
    unpinned = [g for g in groups if not g.pinned]
    return [group_to_dict(g) for g in pinned + unpinned]


def group_to_dict(group: Group):
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "url": group.url,
        "pinned": group.pinned,
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }


@app.post("/api/groups")
def create_group(group: GroupCreate, request: Request, db: Session = Depends(get_db)):
    verify_admin(request)

    if len(group.name) < 3:
        raise HTTPException(
            status_code=400, detail="El nombre debe tener al menos 3 caracteres"
        )

    new_group = Group(
        name=group.name, description=group.description, url=group.url, pinned=False
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return group_to_dict(new_group)


@app.put("/api/groups")
def update_group(group: GroupUpdate, request: Request, db: Session = Depends(get_db)):
    verify_admin(request)

    db_group = db.query(Group).filter(Group.id == group.id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    db_group.name = group.name
    db_group.description = group.description
    db_group.url = group.url
    db.commit()
    db.refresh(db_group)
    return {"success": True, "group": group_to_dict(db_group)}


@app.delete("/api/groups/{group_id}")
def delete_group(group_id: int, request: Request, db: Session = Depends(get_db)):
    verify_admin(request)

    db_group = db.query(Group).filter(Group.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    db.delete(db_group)
    db.commit()
    return {"success": True}


@app.post("/api/groups/pin")
def pin_group(pin_data: PinGroup, request: Request, db: Session = Depends(get_db)):
    verify_admin(request)

    db_group = db.query(Group).filter(Group.id == pin_data.group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    db_group.pinned = pin_data.pinned
    db.commit()
    db.refresh(db_group)
    return {"success": True, "group": group_to_dict(db_group)}


@app.post("/api/admin/login")
def admin_login(login: AdminLogin, request: Request):
    global lockout_data

    client_ip = get_client_ip(request)

    if client_ip not in lockout_data:
        lockout_data[client_ip] = {"attempts": 0, "locked_until": None}

    ip_data = lockout_data[client_ip]

    if ip_data["locked_until"] and datetime.now() < ip_data["locked_until"]:
        remaining = (ip_data["locked_until"] - datetime.now()).total_seconds()
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        if hours > 0:
            detail = f"Cuenta bloqueada. Intenta en {hours} hora(s)"
        else:
            detail = f"Cuenta bloqueada. Intenta en {minutes} minutos"
        raise HTTPException(
            status_code=403,
            detail=detail,
        )

    if login.password == ADMIN_PASSWORD:
        lockout_data[client_ip] = {"attempts": 0, "locked_until": None}
        token = secrets.token_hex(32)
        admin_tokens.add(token)
        return {"success": True, "message": "Admin autenticado", "token": token}

    lockout_data[client_ip]["attempts"] += 1
    if lockout_data[client_ip]["attempts"] >= 3:
        lockout_data[client_ip]["locked_until"] = datetime.now() + timedelta(hours=24)
        raise HTTPException(
            status_code=403, detail="Demasiados intentos. Cuenta bloqueada por 24 horas"
        )

    raise HTTPException(
        status_code=401,
        detail=f"Contraseña incorrecta. Intentos: {lockout_data[client_ip]['attempts']}/3",
    )


@app.get("/api/admin/status")
def admin_status(request: Request):
    client_ip = get_client_ip(request)

    if client_ip in lockout_data:
        ip_data = lockout_data[client_ip]
        if ip_data["locked_until"] and datetime.now() < ip_data["locked_until"]:
            remaining = int((ip_data["locked_until"] - datetime.now()).total_seconds())
            return {
                "locked": True,
                "remaining_seconds": remaining,
                "attempts": ip_data["attempts"],
            }
        return {"locked": False, "attempts": ip_data["attempts"]}

    return {"locked": False, "attempts": 0}


class ImportantLinkCreate(BaseModel):
    title: str
    description: str = ""
    url: str


class ImportantLinkUpdate(BaseModel):
    id: int
    title: str
    description: str
    url: str


def link_to_dict(link: ImportantLink):
    return {
        "id": link.id,
        "title": link.title,
        "description": link.description,
        "url": link.url,
        "created_at": link.created_at.isoformat() if link.created_at else None,
    }


@app.get("/api/important-links")
def get_important_links(db: Session = Depends(get_db)):
    links = db.query(ImportantLink).all()
    return [link_to_dict(l) for l in links]


@app.post("/api/important-links")
def create_important_link(
    link: ImportantLinkCreate, request: Request, db: Session = Depends(get_db)
):
    verify_admin(request)

    if len(link.title) < 3:
        raise HTTPException(
            status_code=400, detail="El título debe tener al menos 3 caracteres"
        )
    if not link.url:
        raise HTTPException(status_code=400, detail="La URL es requerida")

    new_link = ImportantLink(
        title=link.title, description=link.description, url=link.url
    )
    db.add(new_link)
    db.commit()
    db.refresh(new_link)
    return link_to_dict(new_link)


@app.put("/api/important-links")
def update_important_link(
    link: ImportantLinkUpdate, request: Request, db: Session = Depends(get_db)
):
    verify_admin(request)

    db_link = db.query(ImportantLink).filter(ImportantLink.id == link.id).first()
    if not db_link:
        raise HTTPException(status_code=404, detail="Link no encontrado")

    db_link.title = link.title
    db_link.description = link.description
    db_link.url = link.url
    db.commit()
    db.refresh(db_link)
    return {"success": True, "link": link_to_dict(db_link)}


@app.delete("/api/important-links/{link_id}")
def delete_important_link(
    link_id: int, request: Request, db: Session = Depends(get_db)
):
    verify_admin(request)

    db_link = db.query(ImportantLink).filter(ImportantLink.id == link_id).first()
    if not db_link:
        raise HTTPException(status_code=404, detail="Link no encontrado")

    db.delete(db_link)
    db.commit()
    return {"success": True}


@app.get("/favicon.svg")
def serve_favicon():
    logger = logging.getLogger(__name__)
    logger.debug("FAVICON REQUEST - root_path: %s", app.root_path)
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
def serve_catch_all(path: str):
    logger = logging.getLogger(__name__)
    logger.debug("CATCH-ALL REQUEST - path: %s, root_path: %s", path, app.root_path)

    if ".." in path:
        raise HTTPException(status_code=404, detail="Not found")
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    if path.endswith("favicon.svg") or "favicon.svg" in path:
        logger.debug("FAVICON MATCH in catch-all!")
        return FileResponse("static/favicon.svg", media_type="image/svg+xml")
    if path.startswith("static/"):
        return FileResponse(path)
    if path == "admin" or path.startswith("admin/"):
        return FileResponse("static/admin.html")
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_index_root():
    return FileResponse("static/index.html")
