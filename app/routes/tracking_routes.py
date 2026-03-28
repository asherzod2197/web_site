from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, Tracking, User
from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    user = await require_user(request)

    result = await db.execute(
        select(Tracking)
        .where(Tracking.user_id == user.id)
        .order_by(Tracking.created_at.desc())
    )
    trackings = result.scalars().all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "trackings": trackings,
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    })


@router.post("/tracking/add")
async def add_tracking(
    request: Request,
    url: str = Form(...),
    name: str = Form(""),
    selector: str = Form(...),
    selector_type: str = Form("css"),
    check_interval: int = Form(10),
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)

    tracking = Tracking(
        user_id=user.id,
        url=url,
        name=name or url[:50],
        selector=selector,
        selector_type=selector_type,
        check_interval_minutes=max(1, min(check_interval, 1440)),
        is_active=True,
    )
    db.add(tracking)
    await db.commit()

    return RedirectResponse("/?success=Отслеживание+добавлено", status_code=303)


@router.get("/tracking/{tracking_id}/edit", response_class=HTMLResponse)
async def edit_tracking_page(
    tracking_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)

    result = await db.execute(
        select(Tracking).where(
            Tracking.id == tracking_id,
            Tracking.user_id == user.id,
        )
    )
    tracking = result.scalar_one_or_none()
    if not tracking:
        return RedirectResponse("/?error=Отслеживание+не+найдено", status_code=303)

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "user": user,
        "tracking": tracking,
        "error": None,
    })


@router.post("/tracking/{tracking_id}/edit")
async def edit_tracking(
    tracking_id: int,
    request: Request,
    url: str = Form(...),
    name: str = Form(""),
    selector: str = Form(...),
    selector_type: str = Form("css"),
    check_interval: int = Form(10),
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)

    result = await db.execute(
        select(Tracking).where(
            Tracking.id == tracking_id,
            Tracking.user_id == user.id,
        )
    )
    tracking = result.scalar_one_or_none()
    if not tracking:
        return RedirectResponse("/?error=Отслеживание+не+найдено", status_code=303)

    tracking.url = url
    tracking.name = name or url[:50]
    tracking.selector = selector
    tracking.selector_type = selector_type
    tracking.check_interval_minutes = max(1, min(check_interval, 1440))
    await db.commit()

    return RedirectResponse("/?success=Отслеживание+обновлено", status_code=303)


@router.post("/tracking/{tracking_id}/delete")
async def delete_tracking(
    tracking_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)

    result = await db.execute(
        select(Tracking).where(
            Tracking.id == tracking_id,
            Tracking.user_id == user.id,
        )
    )
    tracking = result.scalar_one_or_none()
    if not tracking:
        return RedirectResponse("/?error=Отслеживание+не+найдено", status_code=303)

    await db.delete(tracking)
    await db.commit()

    return RedirectResponse("/?success=Отслеживание+удалено", status_code=303)


@router.post("/tracking/{tracking_id}/toggle")
async def toggle_tracking(
    tracking_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)

    result = await db.execute(
        select(Tracking).where(
            Tracking.id == tracking_id,
            Tracking.user_id == user.id,
        )
    )
    tracking = result.scalar_one_or_none()
    if not tracking:
        return RedirectResponse("/?error=Отслеживание+не+найдено", status_code=303)

    tracking.is_active = not tracking.is_active
    await db.commit()

    status = "активировано" if tracking.is_active else "приостановлено"
    return RedirectResponse(f"/?success=Отслеживание+{status}", status_code=303)
