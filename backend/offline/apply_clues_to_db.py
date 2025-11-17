# backend/offline/apply_clues_to_db.py

from statistics import mean

import mlflow
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Clue, Movie
from .generate_clues_openai import (
    MODEL_NAME,
    PROMPT_VERSION,
    generate_clues_for_movie,
)


def _select_movies_for_clues(
    session: Session,
    num_movies: int | None,
    overwrite_existing: bool,
) -> list[Movie]:
    query = session.query(Movie)

    if not overwrite_existing:
        # Only movies with NO clues yet
        query = query.outerjoin(Clue, Clue.movie_id == Movie.id).filter(
            Clue.id.is_(None)
        )

    if num_movies is not None:
        query = query.limit(num_movies)

    return query.all()


def apply_generated_clues_to_db(
    num_movies: int | None = None,
    overwrite_existing: bool = False,
) -> None:
    """
    Generate GPT clues and write them to the DB.

    - By default (overwrite_existing=False), only movies with no clues are processed.
    - If overwrite_existing=True, clues are regenerated for all selected movies.
    """
    session = SessionLocal()
    try:
        movies = _select_movies_for_clues(
            session=session,
            num_movies=num_movies,
            overwrite_existing=overwrite_existing,
        )

        if not movies:
            print("No eligible movies found (maybe all already have clues).")
            return

        with mlflow.start_run(run_name="apply_openai_clues_to_db"):
            mlflow.log_param("model_name", MODEL_NAME)
            mlflow.log_param("prompt_version", PROMPT_VERSION)
            mlflow.log_param("num_movies", len(movies))
            mlflow.log_param("overwrite_existing", overwrite_existing)

            all_lengths: list[float] = []
            all_movie_clues: dict[str, dict] = {}

            for movie in movies:
                print(
                    f"Generating clues for: {movie.title} (overwrite={overwrite_existing})"
                )

                clues = generate_clues_for_movie(movie.title, movie.overview)

                if overwrite_existing:
                    # wipe any existing clues for this movie
                    session.query(Clue).filter(Clue.movie_id == movie.id).delete()

                # insert new clues (for overwrite_existing=False, there should be none already)
                for idx, clue_text in enumerate(clues):
                    words = len(clue_text.split())
                    all_lengths.append(float(words))

                    session.add(
                        Clue(
                            movie_id=movie.id,
                            order_index=idx,
                            text=clue_text,
                        )
                    )

                all_movie_clues[movie.slug] = {
                    "movie_id": movie.id,
                    "title": movie.title,
                    "overview": movie.overview,
                    "clues": clues,
                }

            session.commit()

            if all_lengths:
                mlflow.log_metric("avg_clue_length", float(mean(all_lengths)))
                mlflow.log_metric("min_clue_length", float(min(all_lengths)))
                mlflow.log_metric("max_clue_length", float(max(all_lengths)))

            mlflow.log_dict(all_movie_clues, "applied_clues.json")

            print(
                f"Applied GPT-generated clues to DB for {len(movies)} movies "
                f"(overwrite_existing={overwrite_existing})."
            )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # Default: only fill in missing clues
    apply_generated_clues_to_db()
    # To overwrite existing clues, use:
    # Force regeneration for ALL movies
    # apply_generated_clues_to_db(overwrite_existing=True)
