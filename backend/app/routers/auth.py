from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import bcrypt

from app.core.dependencies import get_db
from app.core.ratelimit import auth_rate_limit
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

router = APIRouter()


@router.post("/register", dependencies=[Depends(auth_rate_limit)])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed_password = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt())
    new_user = User(username=payload.username, password=hashed_password.decode("utf-8"))
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent registrations of the same username race past the check
        # above; the unique constraint catches it — return a clean 400, not 500.
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already taken")
    return {"message": f"User {payload.username} registered successfully"}


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not bcrypt.checkpw(
        payload.password.encode("utf-8"), user.password.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
