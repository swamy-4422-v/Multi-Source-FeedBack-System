from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/feedback_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), default="api")          # webhook / email / api
    raw_text = Column(Text, nullable=False)
    cleaned_text = Column(Text)
    category = Column(String(100), default="general")   # bug / feature / billing / support / general
    sentiment = Column(String(20), default="neutral")   # positive / negative / neutral
    confidence = Column(Float, default=0.0)
    ai_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime)


class TrendAlert(Base):
    __tablename__ = "trend_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(100))
    message = Column(Text)
    category = Column(String(100))
    count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables created successfully.")


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()