










































from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
import enum, hashlib, os

# ── Database setup ──────────────────────────────────────────────────────────
DATABASE_URL = "sqlite:///./svcte.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class RoleEnum(str, enum.Enum):
    requester = "Requester"
    approver  = "Approver"
    admin     = "Admin"

class StatusEnum(str, enum.Enum):
    pending  = "Pending"
    review   = "In Review"
    approved = "Approved"
    rejected = "Rejected"

class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, index=True, nullable=False)
    name       = Column(String, nullable=False)
    role       = Column(Enum(RoleEnum), default=RoleEnum.requester, nullable=False)
    password   = Column(String, nullable=False)  # hashed

class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"
    id           = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, nullable=False)
    software     = Column(String, nullable=False)
    vendor       = Column(String, nullable=False)
    cost         = Column(Float, nullable=False)
    seats        = Column(Integer, nullable=False)
    justification= Column(String, nullable=False)
    status       = Column(Enum(StatusEnum), default=StatusEnum.pending)
    created_at   = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_db():
    db = SessionLocal()
    if db.query(User).count() == 0:
        users = [
            User(email="requester@svcte.edu", name="Jordan Lee",   role=RoleEnum.requester, password=hash_pw("password")),
            User(email="approver@svcte.edu",  name="Sam Rivera",   role=RoleEnum.approver,  password=hash_pw("password")),
            User(email="admin@svcte.edu",     name="Alex Morgan",  role=RoleEnum.admin,     password=hash_pw("password")),
        ]
        db.add_all(users)
        db.commit()
        db.refresh(users[0])
        requests = [
            PurchaseRequest(requester_id=users[0].id, software="Linear",   vendor="Linear B Inc.",  cost=1440, seats=5,  justification="Project tracking for engineering team.", status=StatusEnum.pending),
            PurchaseRequest(requester_id=users[0].id, software="Datadog",  vendor="Datadog Inc.",   cost=4800, seats=10, justification="Infrastructure monitoring and alerting.",  status=StatusEnum.review),
            PurchaseRequest(requester_id=users[0].id, software="Figma Org",vendor="Figma Inc.",     cost=2000, seats=8,  justification="Design collaboration platform.",           status=StatusEnum.approved),
        ]
        db.add_all(requests)
        db.commit()
    db.close()

seed_db()

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="SVCTE Staff Finance Registrar")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Simple cookie-based session (no external deps)
SESSION_COOKIE = "svcte_session"
_sessions: dict[str, int] = {}  # token -> user_id (in-memory for simplicity)

import secrets

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if not token or token not in _sessions:
        return None
    user_id = _sessions[token]
    return db.query(User).filter(User.id == user_id).first()

def require_user(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, detail="Not authenticated",
                            headers={"Location": "/"})
    return user

# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def landing(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("landing.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request,
                email: str = Form(...),
                password: str = Form(...),
                db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.password != hash_pw(password):
        return templates.TemplateResponse("landing.html",
            {"request": request, "error": "Invalid email or password."})
    token = secrets.token_urlsafe(32)
    _sessions[token] = user.id
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
    return response

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        _sessions.pop(token, None)
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if not token or token not in _sessions:
        return RedirectResponse("/", status_code=302)
    user = db.query(User).filter(User.id == _sessions[token]).first()
    if not user:
        return RedirectResponse("/", status_code=302)

    requests = db.query(PurchaseRequest).filter(
        PurchaseRequest.requester_id == user.id
    ).order_by(PurchaseRequest.created_at.desc()).all()

    total_spend = sum(r.cost for r in requests if r.status == StatusEnum.approved)
    pending_count = sum(1 for r in requests if r.status == StatusEnum.pending)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "purchases": requests,
        "total_spend": total_spend,
        "pending_count": pending_count,
    })

@app.get("/new-request", response_class=HTMLResponse)
async def new_request_form(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if not token or token not in _sessions:
        return RedirectResponse("/", status_code=302)
    user = db.query(User).filter(User.id == _sessions[token]).first()
    return templates.TemplateResponse("new_request.html", {"request": request, "user": user, "error": None})

@app.post("/new-request", response_class=HTMLResponse)
async def submit_request(request: Request,
                         software: str = Form(...),
                         vendor: str = Form(...),
                         cost: float = Form(...),
                         seats: int = Form(...),
                         justification: str = Form(...),
                         db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if not token or token not in _sessions:
        return RedirectResponse("/", status_code=302)
    user = db.query(User).filter(User.id == _sessions[token]).first()
    if len(justification.strip()) < 20:
        return templates.TemplateResponse("new_request.html", {
            "request": request, "user": user,
            "error": "Justification must be at least 20 characters."
        })
    pr = PurchaseRequest(
        requester_id=user.id,
        software=software, vendor=vendor,
        cost=cost, seats=seats,
        justification=justification,
        status=StatusEnum.pending,
    )
    db.add(pr)
    db.commit()
    return RedirectResponse("/dashboard", status_code=302)