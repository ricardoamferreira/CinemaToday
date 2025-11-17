# backend/main.py

from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func

from .db import SessionLocal
from .models import Clue, DailySelection, Movie

app = FastAPI(title="CinemaToday API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------
# Pydantic models
# --------------------------------------------------------------------


class TodayGameResponse(BaseModel):
    game_date: date
    movie_slug: str
    total_clues: int
    current_clue_index: int
    current_clue_text: str
    solved: bool
    poster_url: str | None = None


class GuessRequest(BaseModel):
    movie_slug: str
    guess: str
    current_clue_index: int


class GuessResponse(BaseModel):
    correct: bool
    finished: bool
    next_clue_index: int
    next_clue_text: Optional[str]
    reveal_title: Optional[str]
    reveal_poster_url: Optional[str]
    message: str


# --------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------


def normalise_title(value: str) -> str:
    """Lowercase and strip non-alphanumeric chars so 'Jaws ' and 'jaws!!!' both match."""
    return "".join(ch.lower() for ch in value if ch.isalnum())


# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/today-game", response_model=TodayGameResponse)
def get_today_game() -> TodayGameResponse:
    """
    Return a random game from the movies table.

    For now this picks a random movie every time, ignoring the calendar.
    """
    session = SessionLocal()
    try:
        movie = (
            session.query(Movie)
            .filter(Movie.is_active.is_(True))
            .order_by(func.random())
            .first()
        )
        if not movie:
            raise HTTPException(status_code=404, detail="No movies available.")

        clues = (
            session.query(Clue)
            .filter(Clue.movie_id == movie.id)
            .order_by(Clue.order_index.asc())
            .all()
        )
        if not clues:
            raise HTTPException(status_code=500, detail="No clues for selected movie.")

        first_clue = clues[0]

        return TodayGameResponse(
            game_date=date.today(),
            movie_slug=movie.slug,
            total_clues=len(clues),
            current_clue_index=first_clue.order_index,
            current_clue_text=first_clue.text,
            solved=False,
            poster_url=movie.poster_url,
        )
    finally:
        session.close()


@app.post("/guess", response_model=GuessResponse)
def submit_guess(payload: GuessRequest) -> GuessResponse:
    """
    Check a guess for a given movie_slug using data from the database.
    """
    session = SessionLocal()
    try:
        movie = session.query(Movie).filter(Movie.slug == payload.movie_slug).first()

        if not movie:
            raise HTTPException(status_code=400, detail="Unknown movie slug.")

        clues = (
            session.query(Clue)
            .filter(Clue.movie_id == movie.id)
            .order_by(Clue.order_index.asc())
            .all()
        )
        if not clues:
            raise HTTPException(status_code=500, detail="No clues for this movie.")

        if payload.current_clue_index < 0 or payload.current_clue_index >= len(clues):
            raise HTTPException(status_code=400, detail="Invalid clue index.")

        normalised_guess = normalise_title(payload.guess)
        normalised_title = normalise_title(movie.title)

        # Correct
        if normalised_guess == normalised_title:
            return GuessResponse(
                correct=True,
                finished=True,
                next_clue_index=payload.current_clue_index,
                next_clue_text=None,
                reveal_title=movie.title,
                reveal_poster_url=movie.poster_url,
                message="Nice! You got it right.",
            )

        # Wrong, see if we have another clue
        next_index = payload.current_clue_index + 1

        if next_index < len(clues):
            next_clue = clues[next_index]
            return GuessResponse(
                correct=False,
                finished=False,
                next_clue_index=next_index,
                next_clue_text=next_clue.text,
                reveal_title=None,
                reveal_poster_url=None,
                message="Nope, have another clue.",
            )

        # Out of clues
        return GuessResponse(
            correct=False,
            finished=True,
            next_clue_index=payload.current_clue_index,
            next_clue_text=None,
            reveal_title=movie.title,
            reveal_poster_url=movie.poster_url,
            message=f"Out of clues! The film was {movie.title}.",
        )
    finally:
        session.close()
