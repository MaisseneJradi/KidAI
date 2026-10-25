from sqlalchemy import create_engine, text

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


def check_database() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
