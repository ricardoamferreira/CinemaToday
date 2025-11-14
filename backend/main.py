# backend/main.py

from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="CinemaThisWeek API")

# --------------------------------------------------------------------
# Hard-coded movie stub for now
# Later this will come from Postgres + ingestion/LLM pipeline
# --------------------------------------------------------------------


MOVIE_TITLE = "Jaws"
MOVIE_SLUG = "daily-movie-stub"
MOVIE_POSTER_URL = (
    "https://i.ebayimg.com/images/g/8~QAAOSwyQtVoRQC/s-l1200.jpg"  # placeholder for now
)

MOVIE_CLUES: List[str] = [
    "A quiet coastal town is disrupted by an unusual threat.",
    "The danger lurks beneath the surface, unseen but deadly.",
    "A small-town sheriff, a marine biologist, and a fisherman join forces.",
    "An iconic poster shows a swimmer above a large open mouth full of teeth.",
]

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
    Return today's game state.

    For now this always returns the same hard-coded movie and the first clue.
    """
    if not MOVIE_CLUES:
        raise HTTPException(
            status_code=500, detail="No clues configured for today's movie."
        )

    return TodayGameResponse(
        game_date=date.today(),
        movie_slug=MOVIE_SLUG,
        total_clues=len(MOVIE_CLUES),
        current_clue_index=0,
        current_clue_text=MOVIE_CLUES[0],
        solved=False,
    )


@app.post("/guess", response_model=GuessResponse)
def submit_guess(payload: GuessRequest) -> GuessResponse:
    """
    Check a guess for today's movie and return either:
    - success + reveal, or
    - next clue, or
    - game over + reveal if out of clues.
    """
    # Check movie slug matches the current game
    if payload.movie_slug != MOVIE_SLUG:
        raise HTTPException(
            status_code=400, detail="Unknown movie slug for today's game."
        )

    # Validate clue index
    if payload.current_clue_index < 0 or payload.current_clue_index >= len(MOVIE_CLUES):
        raise HTTPException(status_code=400, detail="Invalid clue index.")

    normalised_guess = normalise_title(payload.guess)
    normalised_title = normalise_title(MOVIE_TITLE)

    # Correct answer
    if normalised_guess == normalised_title:
        return GuessResponse(
            correct=True,
            finished=True,
            next_clue_index=payload.current_clue_index,
            next_clue_text=None,
            reveal_title=MOVIE_TITLE,
            reveal_poster_url=MOVIE_POSTER_URL,
            message="Congrats! You got it right.",
        )

    # Incorrect answer, check if there are more clues
    next_index = payload.current_clue_index + 1

    # There is another clue available
    if next_index < len(MOVIE_CLUES):
        return GuessResponse(
            correct=False,
            finished=False,
            next_clue_index=next_index,
            next_clue_text=MOVIE_CLUES[next_index],
            reveal_title=None,
            reveal_poster_url=None,
            message="Nope, have another clue.",
        )

    # No more clues: game over, reveal the film
    return GuessResponse(
        correct=False,
        finished=True,
        next_clue_index=payload.current_clue_index,
        next_clue_text=None,
        reveal_title=MOVIE_TITLE,
        reveal_poster_url=MOVIE_POSTER_URL,
        message=f"Out of clues! The film was {MOVIE_TITLE}.",
    )
