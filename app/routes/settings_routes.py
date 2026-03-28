from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, UserSettings
from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await require_user(request)

    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    })


@router.post("/settings")
async def save_settings(
    request: Request,
    telegram_chat_id: str = Form(""),
    telegram_notifications: bool = Form(False),
    email_notifications: bool = Form(False),
    notification_email: str = Form(""),
    smtp_server: str = Form("smtp.gmail.com"),
    smtp_port: int = Form(587),
    smtp_email: str = Form(""),
    smtp_password: str = Form(""),
    default_check_interval: int = Form(10),
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)

    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)

    settings.telegram_chat_id = telegram_chat_id
    settings.telegram_notifications = telegram_notifications
    settings.email_notifications = email_notifications
    settings.notification_email = notification_email
    settings.smtp_server = smtp_server
    settings.smtp_port = smtp_port
    settings.smtp_email = smtp_email
    settings.smtp_password = smtp_password
    settings.default_check_interval = max(1, min(default_check_interval, 1440))

    await db.commit()

    return RedirectResponse("/settings?success=Настройки+сохранены", status_code=303)
