from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_password_hash, require_role, authenticate_user
from ..database import get_db
from ..models import ActionLog, User
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserOut

router = APIRouter(prefix="/api/auth", tags=["Usuários"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token)


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        is_active=payload.is_active,
        password_hash=get_password_hash(payload.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log = ActionLog(user_id=user.id, action="Criou", entity="User", entity_id=new_user.id)
    db.add(log)
    db.commit()
    return new_user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    return db.query(User).all()
