# backend/offline/generate_clues_dummy.py
from statistics import mean

import mlflow

from ..db import SessionLocal
from ..models import Clue, Movie


def run_dummy_clue_experiment() -> None:
    session = SessionLocal()
    try:
        movies = session.query(Movie).all()
        if not movies:
            print("No movies found in DB. Seed first.")
            return

        # Treat this as a "prompt version" even though we're not calling an LLM yet
        prompt_version = "dummy-v1"
        fake_model_name = "no-llm-yet"

        with mlflow.start_run(run_name="dummy_clue_quality_check"):
            mlflow.log_param("model_name", fake_model_name)
            mlflow.log_param("prompt_version", prompt_version)
            mlflow.log_param("num_movies", len(movies))

            clue_lengths = []

            for movie in movies:
                clues = (
                    session.query(Clue)
                    .filter(Clue.movie_id == movie.id)
                    .order_by(Clue.order_index.asc())
                    .all()
                )
                if not clues:
                    continue

                for c in clues:
                    length = len(c.text.split())
                    clue_lengths.append(length)

            if clue_lengths:
                mlflow.log_metric("avg_clue_length", float(mean(clue_lengths)))
                mlflow.log_metric("min_clue_length", float(min(clue_lengths)))
                mlflow.log_metric("max_clue_length", float(max(clue_lengths)))

            # Save a small text artifact with sample clues
            sample_lines = []
            for movie in movies[:3]:
                clues = (
                    session.query(Clue)
                    .filter(Clue.movie_id == movie.id)
                    .order_by(Clue.order_index.asc())
                    .all()
                )
                if not clues:
                    continue
                sample_lines.append(f"Movie: {movie.title}")
                for c in clues:
                    sample_lines.append(f"  [{c.order_index}] {c.text}")
                sample_lines.append("")

            artifacts_path = "sample_clues.txt"
            with open(artifacts_path, "w", encoding="utf-8") as f:
                f.write("\n".join(sample_lines))

            mlflow.log_artifact(artifacts_path)

            print("Dummy MLflow run logged.")
    finally:
        session.close()


if __name__ == "__main__":
    run_dummy_clue_experiment()
