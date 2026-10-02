import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{ROOT / "data" / "app.db"}')
(ROOT / 'data').mkdir(exist_ok=True)
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})


@event.listens_for(engine, 'connect')
def enable_foreign_keys(connection, _):
    connection.execute('PRAGMA foreign_keys=ON')


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine)
