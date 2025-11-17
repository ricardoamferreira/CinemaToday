# backend/models.py
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    poster_url = Column(String, nullable=True)
    overview = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=False, index=True)

    # relationships
    clues = relationship("Clue", back_populates="movie", cascade="all, delete-orphan")
    daily_selection = relationship(
        "DailySelection", back_populates="movie", uselist=False
    )


class Clue(Base):
    __tablename__ = "clues"

    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)

    movie = relationship("Movie", back_populates="clues")

    __table_args__ = (
        # ensure we don't accidentally create duplicate clue positions per movie
        UniqueConstraint("movie_id", "order_index", name="uq_movie_clue_order"),
    )


class DailySelection(Base):
    __tablename__ = "daily_selection"

    id = Column(Integer, primary_key=True, index=True)
    game_date = Column(Date, nullable=False, unique=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)

    movie = relationship("Movie", back_populates="daily_selection")
