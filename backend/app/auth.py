import os
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

SECRET_KEY = "change-this-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480
SESSION_TIMEZONE = ZoneInfo(os.getenv("CASHUP_SESSION_TIMEZONE", "America/Sao_Paulo"))
APP_BOOTED_AT = datetime.now(SESSION_TIMEZONE)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _get_session_reset_at(reference: Optional[datetime] = None) -> datetime:
    current = reference.astimezone(SESSION_TIMEZONE) if reference else datetime.now(SESSION_TIMEZONE)
    next_day = current.date() + timedelta(days=1)
    return datetime.combine(next_day, time.min, tzinfo=SESSION_TIMEZONE)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    issued_at = datetime.now(SESSION_TIMEZONE)
    expires_at = issued_at + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    session_reset_at = _get_session_reset_at(issued_at)
    expire = min(expires_at, session_reset_at)

    to_encode = data.copy()
    to_encode.update(
        {
            "exp": expire,
            "iat": issued_at,
            "boot": APP_BOOTED_AT.isoformat(),
            "session_reset_at": session_reset_at.isoformat(),
        }
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_boot = payload.get("boot")
        token_session_reset_at = payload.get("session_reset_at")
        if email is None or token_boot is None or token_session_reset_at is None:
            raise credentials_exception
        if token_boot != APP_BOOTED_AT.isoformat():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session revoked after application restart",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if datetime.now(SESSION_TIMEZONE) >= datetime.fromisoformat(token_session_reset_at):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired after daily reset",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except JWTError as exc:
        raise credentials_exception from exc
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


ROLE_LEVELS = {
    "viewer": 1,
    "finance": 2,
    "admin": 3,
}


def require_role(role: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        required_level = ROLE_LEVELS.get(role)
        user_level = ROLE_LEVELS.get(user.role, 0)
        if required_level is None or user_level < required_level:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return dependency
