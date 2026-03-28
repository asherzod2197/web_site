from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, CheckLog, Tracking
from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(
    request: Request,
    page: int = 1,
    tracking_id: int = 0,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)

    per_page = 50

    # Получаем все отслеживания пользователя для фильтра
    trackings_result = await db.execute(
        select(Tracking).where(Tracking.user_id == user.id).order_by(Tracking.name)
    )
    user_trackings = trackings_result.scalars().all()
    tracking_ids = [t.id for t in user_trackings]

    # Строим запрос
    query = select(CheckLog).where(CheckLog.tracking_id.in_(tracking_ids))

    if tracking_id and tracking_id in tracking_ids:
        query = query.where(CheckLog.tracking_id == tracking_id)

    query = query.order_by(CheckLog.checked_at.desc())

    # Пагинация
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page + 1)

    result = await db.execute(query)
    logs = result.scalars().all()

    has_next = len(logs) > per_page
    if has_next:
        logs = logs[:per_page]

    # Создаём маппинг tracking_id -> tracking для отображения
    tracking_map = {t.id: t for t in user_trackings}

    return templates.TemplateResponse("logs.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "tracking_map": tracking_map,
        "trackings": user_trackings,
        "current_tracking_id": tracking_id,
        "page": page,
        "has_next": has_next,
    })
