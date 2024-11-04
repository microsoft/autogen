from ...database.dbmanager import DBManager
from ..config import settings


def init_db():
    return DBManager(engine_uri=settings.DATABASE_URI)
