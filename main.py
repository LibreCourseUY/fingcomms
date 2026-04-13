"""
Fingcomms - Main Application Entry Point

This file contains the FastAPI application that powers the Fingcomms group directory.
It handles HTTP requests, manages the admin authentication system, and provides
the fuzzy search functionality for finding groups.

Key Features:
- RESTful API for CRUD operations on groups and important links
- Admin authentication with token-based sessions and IP lockout protection
- Fuzzy search algorithm for flexible group discovery
- Static file serving for the Vue.js frontend
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import logging
import secrets
import httpx

logging.basicConfig(level=logging.DEBUG)
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from database import SessionLocal, Group, ImportantLink, get_db

# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = FastAPI(root_path=os.getenv("ROOT_PATH", ""))

logger = logging.getLogger(__name__)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all incoming HTTP requests for debugging purposes."""
    logger.debug("REQUEST: %s %s", request.method, request.url.path)
    response = await call_next(request)
    return response


# ============================================================================
# ADMIN AUTHENTICATION CONFIGURATION
# ============================================================================

# In production, use a strong password from environment variables
# Default "admin123" is only for development/testing
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# In-memory storage for admin sessions (tokens) and IP lockout data
# Note: In production, consider using Redis or a database for session management
lockout_data = {}
admin_tokens = set()


def get_client_ip(request: Request) -> str:
    """
    Extract the client's real IP address from the request.
    Handles proxy forwarding (X-Forwarded-For header) correctly.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def verify_admin(request: Request):
    """
    Verify that the request comes from an authenticated admin.
    Checks the Authorization header for a valid admin token.
    Raises HTTP 401 if not authenticated.
    """
    auth_header = request.headers.get("Authorization", "")
    logger.debug("VERIFY_ADMIN - Authorization header: %s", auth_header)
    token = auth_header.replace("Bearer ", "").strip()
    logger.debug("VERIFY_ADMIN - token: %s, admin_tokens: %s", token, admin_tokens)

    if token not in admin_tokens:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return True


def verify_admin_origin(request: Request):
    """
    Additional security check: verify the request originated from the admin page.
    This prevents CSRF attacks where external sites try to admin actions.
    """
    referer = request.headers.get("Referer", "")
    if "/admin" not in referer and "/admin.html" not in referer:
        raise HTTPException(status_code=403, detail="Access denied")


# ============================================================================
# METRICS CONFIGURATION
# ============================================================================

METRICS_EVENTS_URL = os.getenv(
    "METRICS_EVENTS_URL", "https://api.eclipselabs.com.uy/metrics/event"
)
METRICS_VIEWS_URL = os.getenv(
    "METRICS_VIEWS_URL", "https://api.eclipselabs.com.uy/metrics/views"
)
METRICS_API_KEY = os.getenv("METRICS_API_KEY", "")


class MetricsEvent(BaseModel):
    event_type: str
    metadata: Optional[dict] = None


class ViewEvent(BaseModel):
    path: str
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    viewport: Optional[str] = None
    document_title: Optional[str] = None


# ============================================================================
# FUZZY SEARCH ALGORITHM
# ============================================================================


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.
    This measures the minimum number of single-character edits needed
    to change one string into the other.

    Used by fuzzy_match to find similar words even with typos.
    Example: "python" and "pythn" have distance 1 (one deletion)
    """
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
    """
    Perform fuzzy matching between a search query and a text string.
    Returns a score from 0.0 to 1.0 indicating how well they match.

    Matching strategy (in order):
    1. Exact substring match: returns 1.0
    2. Word contains query: returns 0.9
    3. Levenshtein distance similarity: returns score based on similarity

    This allows users to find groups even with typos or partial matches.
    """
    query = query.lower()
    text = text.lower()

    # Strategy 1: Exact substring match
    if query in text:
        return 1.0

    # Strategy 2: Word contains query
    words = text.split()
    for word in words:
        if query in word:
            return 0.9

    # Strategy 3: Levenshtein distance (typo tolerance)
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
    """
    Search for groups using fuzzy matching on both name and description.
    Groups are sorted by relevance score (highest first).

    The description match is weighted 70% to prioritize name matches.
    """
    results = []
    for group in groups:
        name_score = fuzzy_match(query, group.name, threshold)
        desc_score = fuzzy_match(query, group.description or "", threshold)
        total_score = max(name_score, desc_score * 0.7)

        if total_score > 0:
            results.append((group, total_score))

    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]


# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================


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


# ============================================================================
# API Endpoints - Groups
# ============================================================================


@app.get("/api/groups")
def get_groups(q: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get all groups, optionally filtered by search query.

    If 'q' parameter is provided, uses fuzzy search to find matching groups.
    Otherwise, returns all groups with pinned groups appearing first.
    """
    groups = db.query(Group).all()

    if q and q.strip():
        results = fuzzy_search(q, groups)
        return [group_to_dict(g) for g in results]

    pinned = [g for g in groups if g.pinned]
    unpinned = [g for g in groups if not g.pinned]
    return [group_to_dict(g) for g in pinned + unpinned]


def group_to_dict(group: Group):
    """Convert a Group database model to a dictionary for JSON response."""
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
    """Create a new group. Requires admin authentication."""
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
    """Update an existing group. Requires admin authentication."""
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
    """Delete a group. Requires admin authentication."""
    verify_admin(request)

    db_group = db.query(Group).filter(Group.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    db.delete(db_group)
    db.commit()
    return {"success": True}


@app.post("/api/groups/pin")
def pin_group(pin_data: PinGroup, request: Request, db: Session = Depends(get_db)):
    """
    Pin or unpin a group.
    Pinned groups appear at the top of the list.
    Requires admin authentication.
    """
    verify_admin(request)

    db_group = db.query(Group).filter(Group.id == pin_data.group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    db_group.pinned = pin_data.pinned
    db.commit()
    db.refresh(db_group)
    return {"success": True, "group": group_to_dict(db_group)}


# ============================================================================
# API Endpoints - Admin Authentication
# ============================================================================


@app.post("/api/admin/login")
def admin_login(login: AdminLogin, request: Request):
    """
    Admin login endpoint with IP-based lockout protection.

    Security features:
    - Password verification
    - IP-based rate limiting (3 attempts max)
    - 24-hour lockout after failed attempts
    - Token-based session management
    """
    global lockout_data

    client_ip = get_client_ip(request)

    if client_ip not in lockout_data:
        lockout_data[client_ip] = {"attempts": 0, "locked_until": None}

    ip_data = lockout_data[client_ip]

    # Check if IP is currently locked
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

    # Verify password
    if login.password == ADMIN_PASSWORD:
        global admin_tokens
        lockout_data[client_ip] = {"attempts": 0, "locked_until": None}
        token = secrets.token_hex(32)
        admin_tokens.add(token)
        logger.debug("LOGIN SUCCESS - token added: %s", token)
        return {"success": True, "message": "Admin autenticado", "token": token}

    # Failed attempt - increment counter and lock if too many attempts
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
    """
    Check the lockout status for the current IP.
    Useful for the admin UI to show lockout countdown.
    """
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


# ============================================================================
# API Endpoints - Important Links
# ============================================================================


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
    """Convert an ImportantLink database model to a dictionary for JSON response."""
    return {
        "id": link.id,
        "title": link.title,
        "description": link.description,
        "url": link.url,
        "created_at": link.created_at.isoformat() if link.created_at else None,
    }


@app.get("/api/important-links")
def get_important_links(db: Session = Depends(get_db)):
    """Get all important links (public endpoint)."""
    links = db.query(ImportantLink).all()
    return [link_to_dict(l) for l in links]


@app.post("/api/important-links")
def create_important_link(
    link: ImportantLinkCreate, request: Request, db: Session = Depends(get_db)
):
    """Create a new important link. Requires admin authentication."""
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
    """Update an existing important link. Requires admin authentication."""
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
    """Delete an important link. Requires admin authentication."""
    verify_admin(request)

    db_link = db.query(ImportantLink).filter(ImportantLink.id == link_id).first()
    if not db_link:
        raise HTTPException(status_code=404, detail="Link no encontrado")

    db.delete(db_link)
    db.commit()
    return {"success": True}


# ============================================================================
# Metrics Endpoints
# ============================================================================


@app.post("/api/metrics/event")
async def track_event(event: MetricsEvent):
    """Track click events by forwarding to the metrics API."""
    if not METRICS_API_KEY:
        return {"status": "skipped", "reason": "Metrics not configured"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                METRICS_EVENTS_URL,
                json={"event_type": event.event_type, "metadata": event.metadata or {}},
                headers={"X-API-Key": METRICS_API_KEY},
            )
            if response.status_code == 200:
                return {"status": "ok"}
            return {"status": "error", "detail": response.text}
    except Exception as e:
        logger.error(f"Metrics tracking failed: {e}")
        return {"status": "error", "detail": str(e)}


@app.post("/api/metrics/views")
async def track_view(view: ViewEvent):
    """Track page views by forwarding to the metrics API."""
    if not METRICS_API_KEY:
        return {"status": "skipped", "reason": "Metrics not configured"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                METRICS_VIEWS_URL,
                json=view.model_dump(exclude_none=True),
                headers={"X-API-Key": METRICS_API_KEY},
            )
            if response.status_code == 200:
                return {"status": "ok"}
            return {"status": "error", "detail": response.text}
    except Exception as e:
        logger.error(f"View tracking failed: {e}")
        return {"status": "error", "detail": str(e)}


# ============================================================================
# Static File Serving
# ============================================================================


@app.get("/favicon.svg")
def serve_favicon():
    """Serve the favicon SVG file."""
    logger = logging.getLogger(__name__)
    logger.debug("FAVICON REQUEST - root_path: %s", app.root_path)
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
def serve_catch_all(path: str):
    """
    Catch-all route for SPA (Single Page Application) routing.

    This ensures that Vue.js handles all routing on the client side.
    The server serves index.html for any unknown paths, and Vue.js
    determines which component to render based on the URL.

    Security checks prevent directory traversal attacks.
    """
    logger = logging.getLogger(__name__)
    logger.debug("CATCH-ALL REQUEST - path: %s, root_path: %s", path, app.root_path)

    # Security: prevent directory traversal
    if ".." in path:
        raise HTTPException(status_code=404, detail="Not found")

    # Don't serve API routes through SPA handler
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    # Handle favicon specially
    if path.endswith("favicon.svg") or "favicon.svg" in path:
        logger.debug("FAVICON MATCH in catch-all!")
        return FileResponse("static/favicon.svg", media_type="image/svg+xml")

    # Serve static files directly
    if path.startswith("static/"):
        return FileResponse(path)

    # Admin routes
    if path == "admin" or path.startswith("admin/"):
        return FileResponse("static/admin.html")

    # Default: serve the Vue.js SPA
    return FileResponse("static/index.html")


# Mount static files directory at /static URL path
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_index_root():
    """Serve the main index.html for the root URL."""
    return FileResponse("static/index.html")
