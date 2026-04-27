from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_jti,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.entities import (
    AuthToken,
    Client,
    Driver,
    DriverApplication,
    DriverApplicationStatus,
    TokenType,
    User,
    UserRole,
)
from app.schemas.dto import (
    AuthResponse,
    DriverApplicationCreate,
    DriverApplicationOut,
    LoginRequest,
    RegisterRequest,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _issue_tokens(db: Session, user: User) -> tuple[str, str]:
    access_jti = generate_jti()
    refresh_jti = generate_jti()

    access_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    db.add(
        AuthToken(
            user_id=user.id,
            jti=access_jti,
            token_type=TokenType.ACCESS,
            expires_at=access_expires_at,
        )
    )
    db.add(
        AuthToken(
            user_id=user.id,
            jti=refresh_jti,
            token_type=TokenType.REFRESH,
            expires_at=refresh_expires_at,
        )
    )
    db.commit()

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        jti=access_jti,
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        role=user.role.value,
        jti=refresh_jti,
    )

    return access_token, refresh_token


def _build_auth_response(user: User, access_token: str) -> AuthResponse:
    return AuthResponse(
        id=user.id,
        email=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_blocked=user.is_blocked,
        accessToken=access_token,
    )


def _create_profile_for_role(db: Session, user: User, phone: str) -> None:
    if user.role == UserRole.CLIENT:
        db.add(Client(user_id=user.id, phone=phone, balance=0))
    elif user.role == UserRole.DRIVER:
        db.add(Driver(user_id=user.id, license_number=f"DRV-{user.id:06d}"))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    existing_user = db.scalar(select(User).where(User.username == payload.email))
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        username=payload.email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        role=UserRole.CLIENT,
    )
    db.add(user)
    db.flush()

    _create_profile_for_role(db, user, payload.phone)
    db.commit()
    db.refresh(user)

    access_token, refresh_token = _issue_tokens(db, user)
    _set_refresh_cookie(response, refresh_token)
    return _build_auth_response(user, access_token)


@router.post("/driver-applications", response_model=DriverApplicationOut, status_code=status.HTTP_201_CREATED)
def create_driver_application(payload: DriverApplicationCreate, db: Session = Depends(get_db)):
    existing_user = db.scalar(select(User).where(User.username == payload.email))
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    duplicate_application = db.scalar(
        select(DriverApplication).where(
            DriverApplication.email == payload.email,
            DriverApplication.status == DriverApplicationStatus.PENDING,
        )
    )
    if duplicate_application:
        raise HTTPException(status_code=400, detail="Pending application already exists for this email")

    duplicate_license = db.scalar(select(Driver).where(Driver.license_number == payload.license_number))
    if duplicate_license:
        raise HTTPException(status_code=400, detail="License number already exists")

    application = DriverApplication(
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        license_series=payload.license_series,
        license_number=payload.license_number,
        status=DriverApplicationStatus.PENDING,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="User is blocked")

    access_token, refresh_token = _issue_tokens(db, user)
    _set_refresh_cookie(response, refresh_token)
    return _build_auth_response(user, access_token)


@router.post("/refresh", response_model=AuthResponse)
def refresh_access_token(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        payload = decode_token(refresh_token)
        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        token_type = payload.get("type")
    except (TokenError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if token_type != TokenType.REFRESH.value or not jti:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    db_token = db.scalar(select(AuthToken).where(AuthToken.jti == jti))
    if not db_token or db_token.token_type != TokenType.REFRESH:
        raise HTTPException(status_code=401, detail="Refresh token does not exist")
    if db_token.is_revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    if _as_utc(db_token.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="User is blocked")

    db_token.is_revoked = True
    db.commit()

    access_token, new_refresh_token = _issue_tokens(db, user)
    _set_refresh_cookie(response, new_refresh_token)
    return _build_auth_response(user, access_token)


@router.post("/logout", response_model=dict)
def logout(request: Request, response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    refresh_token = request.cookies.get(settings.refresh_cookie_name)

    if refresh_token:
        try:
            payload = decode_token(refresh_token)
            refresh_jti = payload.get("jti")
            token_record = db.scalar(select(AuthToken).where(AuthToken.jti == refresh_jti))
            if token_record:
                token_record.is_revoked = True
                db.commit()
        except TokenError:
            pass

    response.delete_cookie(settings.refresh_cookie_name, path="/")

    active_access_tokens = db.scalars(
        select(AuthToken).where(
            AuthToken.user_id == current_user.id,
            AuthToken.token_type == TokenType.ACCESS,
            AuthToken.is_revoked.is_(False),
        )
    ).all()
    for token in active_access_tokens:
        token.is_revoked = True
    db.commit()

    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
