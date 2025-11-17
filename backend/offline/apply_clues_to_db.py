# backend/offline/apply_clues_to_db.py

from statistics import mean

import mlflow

from ..db import SessionLocal
from ..models import Clue, Movie
from .generate_clues_openai import (
    MODEL_NAME,
    PROMPT_VERSION,
    generate_clues_for_movie,
)


def apply_generated_clues_to_db(num_movies: int | None = None) -> None:
    session = SessionLocal()
    try:
        query = session.query(Movie)
        if num_movies is not None:
            query = query.limit(num_movies)

        movies = query.all()
        if not movies:
            print("No movies found in DB. Seed first.")
            return

        with mlflow.start_run(run_name="apply_openai_clues_to_db"):
            mlflow.log_param("model_name", MODEL_NAME)
            mlflow.log_param("prompt_version", PROMPT_VERSION)
            mlflow.log_param("num_movies", len(movies))

            all_lengths: list[float] = []
            all_movie_clues: dict[str, dict] = {}

            for movie in movies:
                print(f"Generating clues for: {movie.title}")

                clues = generate_clues_for_movie(movie.title, movie.overview)

                # wipe existing clues for this movie
                session.query(Clue).filter(Clue.movie_id == movie.id).delete()

                # insert new clues
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

                # add to audit structure for MLflow
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

            # log all clues as a JSON artifact
            mlflow.log_dict(all_movie_clues, "applied_clues.json")

            print("Applied GPT-generated clues to DB.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    apply_generated_clues_to_db()
