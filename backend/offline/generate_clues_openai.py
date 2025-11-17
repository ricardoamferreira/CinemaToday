# backend/offline/generate_clues_openai.py

import json
from statistics import mean

import mlflow
from openai import OpenAI

from ..db import SessionLocal
from ..models import Movie

client = OpenAI()

PROMPT_VERSION = "v3"
MODEL_NAME = "gpt-5-mini"

SYSTEM_PROMPT = """
You generate guessing-game clues for cinema films.

Rules:
- Output exactly 4 clues.
- Clues start very vague and get more specific.
- In terms of difficulty level, from 1 to 10, the first clue needs to be difficulty 10, 
the second difficulty 8, the third difficulty 5, and the fourth difficulty 3.
- Never include the film title, actor names, or director names.
- Refer to plot, themes, setting, genre, or iconic imagery.
- Avoid big spoilers.
- Each clue must be a single sentence under 35 words.
- Respond ONLY in JSON with structure:
  {"clues": ["clue 1", "clue 2", "clue 3", "clue 4"]}.
"""


def generate_clues_for_movie(title: str, overview: str | None) -> list[str]:
    """Call OpenAI once and return a list of 4 clues."""
    user_prompt = f"""
Film title: "{title}"

Short description:
{overview or "No description available."}

Generate clues now.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        # temperature=0.6,
        max_completion_tokens=2000,
        response_format={"type": "json_object"},
        reasoning_effort="low",
    )

    content = response.choices[0].message.content

    if not content or not content.strip():
        raise RuntimeError(f"Model returned empty content: {response}")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to parse LLM response as JSON. Raw content: {content!r}"
        ) from exc

    clues = data.get("clues", [])
    clues = [c.strip() for c in clues if isinstance(c, str)]

    if len(clues) != 4:
        raise RuntimeError(f"Expected 4 clues, got {len(clues)}: {clues!r}")

    return clues


def run_openai_clue_experiment(num_movies: int = 3) -> None:
    session = SessionLocal()
    try:
        movies = session.query(Movie).limit(num_movies).all()
        if not movies:
            print("No movies found in DB. Seed first.")
            return

        with mlflow.start_run(run_name="openai_clue_generation"):
            mlflow.log_param("model_name", MODEL_NAME)
            mlflow.log_param("prompt_version", PROMPT_VERSION)
            mlflow.log_param("num_movies", len(movies))

            all_lengths: list[float] = []
            artifact_lines: list[str] = []

            for movie in movies:
                clues = generate_clues_for_movie(movie.title, movie.overview)
                # For now we ONLY log them, no DB writes
                artifact_lines.append(f"Movie: {movie.title}")
                for idx, clue in enumerate(clues):
                    words = len(clue.split())
                    all_lengths.append(float(words))
                    artifact_lines.append(f"  [{idx}] ({words} words) {clue}")
                artifact_lines.append("")

            if all_lengths:
                mlflow.log_metric("avg_clue_length", float(mean(all_lengths)))
                mlflow.log_metric("min_clue_length", float(min(all_lengths)))
                mlflow.log_metric("max_clue_length", float(max(all_lengths)))

            # Save generated clues as an artifact
            artifacts_path = "generated_clues_openai.txt"
            with open(artifacts_path, "w", encoding="utf-8") as f:
                f.write("\n".join(artifact_lines))

            mlflow.log_artifact(artifacts_path)

            print("OpenAI clue generation run logged.")
    finally:
        session.close()


if __name__ == "__main__":
    run_openai_clue_experiment()
