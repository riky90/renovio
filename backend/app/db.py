"""SQLAlchemy 2.0 engine, session factory, and declarative base.

All Phase 1 ORM entities (backend/app/models/) subclass `Base`. Alembic's
env.py points at `Base.metadata` for autogenerate/upgrade.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

# pool_pre_ping: Neon spegne il compute quando e' inattivo e chiude le
# connessioni; senza il ping la prima richiesta dopo una pausa riceverebbe
# una connessione morta dal pool.
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
