import asyncio
import logging
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session, Tracking, CheckLog, UserSettings
from app.notifications import notify_user

logger = logging.getLogger(__name__)

# Глобальный флаг для остановки мониторинга
_running = False


async def fetch_value(url: str, selector: str, selector_type: str = "css") -> str | None:
    """Получить значение элемента со страницы."""
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Ошибка загрузки {url}: {e}")
        return None

    try:
        soup = BeautifulSoup(response.text, "lxml")

        if selector_type == "css":
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        elif selector_type == "xpath":
            # BeautifulSoup не поддерживает xpath напрямую, используем CSS
            logger.warning("XPath не поддерживается, используйте CSS-селектор")
            return None
        elif selector_type == "text":
            # Ищем текст на странице
            if selector in response.text:
                return f"Найдено: '{selector}'"
            else:
                return f"Не найдено: '{selector}'"
        else:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)

        return None
    except Exception as e:
        logger.error(f"Ошибка парсинга {url}: {e}")
        return None


async def check_tracking(tracking: Tracking, settings: UserSettings | None) -> None:
    """Проверить одно отслеживание."""
    logger.info(f"Проверка: {tracking.name or tracking.url} (#{tracking.id})")

    new_value = await fetch_value(tracking.url, tracking.selector, tracking.selector_type)

    async with async_session() as db:
        # Получаем свежую версию из БД
        result = await db.execute(select(Tracking).where(Tracking.id == tracking.id))
        db_tracking = result.scalar_one_or_none()
        if not db_tracking:
            return

        old_value = db_tracking.last_value
        is_changed = False

        if new_value is not None:
            if old_value is not None and old_value != new_value:
                is_changed = True
            elif old_value is None:
                is_changed = False  # Первая проверка

        # Обновляем отслеживание
        db_tracking.last_value = new_value
        db_tracking.last_checked = datetime.utcnow()
        db_tracking.is_changed = is_changed

        # Создаём запись в журнал
        log = CheckLog(
            tracking_id=db_tracking.id,
            old_value=old_value,
            new_value=new_value,
            checked_at=datetime.utcnow(),
            is_changed=is_changed,
        )
        db.add(log)
        await db.commit()

        # Отправляем уведомление при изменении
        if is_changed and settings:
            try:
                await notify_user(
                    settings=settings,
                    tracking_name=db_tracking.name or db_tracking.url,
                    tracking_url=db_tracking.url,
                    old_value=old_value,
                    new_value=new_value,
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")

        status_text = "ИЗМЕНЕНО ✅" if is_changed else "без изменений"
        logger.info(f"  Результат: {status_text} | Значение: {(new_value or '(нет)')[:80]}")


async def monitor_loop():
    """Основной цикл мониторинга."""
    global _running
    _running = True
    logger.info("🚀 Мониторинг запущен")

    while _running:
        try:
            async with async_session() as db:
                # Получаем все активные отслеживания
                result = await db.execute(
                    select(Tracking).where(Tracking.is_active == True)
                )
                trackings = result.scalars().all()

                for tracking in trackings:
                    if not _running:
                        break

                    # Проверяем интервал
                    if tracking.last_checked:
                        next_check = tracking.last_checked + timedelta(
                            minutes=tracking.check_interval_minutes
                        )
                        if datetime.utcnow() < next_check:
                            continue

                    # Получаем настройки пользователя
                    settings_result = await db.execute(
                        select(UserSettings).where(
                            UserSettings.user_id == tracking.user_id
                        )
                    )
                    settings = settings_result.scalar_one_or_none()

                    await check_tracking(tracking, settings)
                    # Пауза между проверками чтобы не нагружать
                    await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Ошибка в цикле мониторинга: {e}")

        # Ожидание перед следующим циклом проверки (30 секунд)
        await asyncio.sleep(30)

    logger.info("🛑 Мониторинг остановлен")


def stop_monitor():
    """Остановка мониторинга."""
    global _running
    _running = False
