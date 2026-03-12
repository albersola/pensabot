from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings

sync_engine = create_engine(settings.celery_database_url, echo=False)
SyncSessionLocal = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)
