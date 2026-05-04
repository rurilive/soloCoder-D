from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

DB_HOST = "64.83.36.96"
DB_PORT = 53306
DB_USER = "01Qcb6rBM5MS2GKXvjDq"
DB_PASSWORD = "lsTiBCoLk3cWvQKMZ4Mq"
DB_NAME = "cd"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class TimerMode(enum.Enum):
    WORK = "work"
    SHORT_BREAK = "short-break"
    LONG_BREAK = "long-break"
    CUSTOM = "custom"


class TimerRecord(Base):
    __tablename__ = "timer_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mode = Column(SQLEnum(TimerMode), nullable=False, default=TimerMode.WORK)
    duration_seconds = Column(Integer, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)
    note = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<TimerRecord(id={self.id}, mode={self.mode}, duration={self.duration_seconds}s)>"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
