import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.monitor import monitor_loop, stop_monitor
from app.routes import auth_routes, tracking_routes, log_routes, settings_routes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Создаём директорию для БД
os.makedirs("data", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle — инициализация БД и запуск мониторинга."""
    logger.info("🚀 Запуск приложения...")
    await init_db()
    logger.info("✅ База данных инициализирована")

    # Запускаем фоновый мониторинг
    monitor_task = asyncio.create_task(monitor_loop())
    logger.info("✅ Фоновый мониторинг запущен")

    yield

    # Останавливаем мониторинг
    stop_monitor()
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    logger.info("🛑 Приложение остановлено")


app = FastAPI(
    title="Веб-мониторинг",
    description="Система мониторинга изменений на веб-страницах",
    version="1.0.0",
    lifespan=lifespan,
)

# Статические файлы
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключаем маршруты
app.include_router(auth_routes.router)
app.include_router(tracking_routes.router)
app.include_router(log_routes.router)
app.include_router(settings_routes.router)


@app.exception_handler(303)
async def redirect_handler(request: Request, exc):
    return RedirectResponse(exc.headers.get("Location", "/login"), status_code=303)
