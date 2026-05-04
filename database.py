from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
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


class CycleStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TimerRecord(Base):
    __tablename__ = "timer_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mode = Column(SQLEnum(TimerMode), nullable=False, default=TimerMode.WORK)
    duration_seconds = Column(Integer, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)
    note = Column(String(255), nullable=True)
    cycle_segment_id = Column(Integer, ForeignKey("cycle_segments.id"), nullable=True)

    cycle_segment = relationship("CycleSegment", back_populates="timer_records")

    def __repr__(self):
        return f"<TimerRecord(id={self.id}, mode={self.mode}, duration={self.duration_seconds}s)>"


class WorkCycle(Base):
    __tablename__ = "work_cycles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=True, default="默认循环")
    total_pomodoros = Column(Integer, nullable=False, default=4)
    completed_pomodoros = Column(Integer, nullable=False, default=0)
    work_duration_minutes = Column(Integer, nullable=False, default=25)
    short_break_duration_minutes = Column(Integer, nullable=False, default=5)
    long_break_duration_minutes = Column(Integer, nullable=False, default=15)
    status = Column(SQLEnum(CycleStatus), nullable=False, default=CycleStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    segments = relationship("CycleSegment", back_populates="work_cycle", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkCycle(id={self.id}, completed={self.completed_pomodoros}/{self.total_pomodoros})>"


class CycleSegment(Base):
    __tablename__ = "cycle_segments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    work_cycle_id = Column(Integer, ForeignKey("work_cycles.id"), nullable=False)
    segment_order = Column(Integer, nullable=False)
    segment_type = Column(SQLEnum(TimerMode), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    work_cycle = relationship("WorkCycle", back_populates="segments")
    timer_records = relationship("TimerRecord", back_populates="cycle_segment")

    def __repr__(self):
        return f"<CycleSegment(id={self.id}, type={self.segment_type}, order={self.segment_order})>"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
