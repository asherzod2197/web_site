from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, User, UserSettings
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверный email или пароль"
        })

    token = create_access_token(data={"sub": user.id})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("register.html", {
        "request": request,
        "error": None
    })


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if password != password_confirm:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Пароли не совпадают"
        })

    if len(password) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Пароль должен содержать минимум 6 символов"
        })

    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Пользователь с таким email уже существует"
        })

    user = User(
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.flush()

    # Создаём настройки по умолчанию
    settings = UserSettings(user_id=user.id)
    db.add(settings)
    await db.commit()

    token = create_access_token(data={"sub": user.id})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response
