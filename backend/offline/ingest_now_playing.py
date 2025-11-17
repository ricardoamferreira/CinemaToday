# backend/offline/ingest_now_playing.py

import os
from typing import Any

import mlflow
import requests

from ..db import SessionLocal
from ..models import Movie

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3")
TMDB_IMAGE_BASE_URL = os.getenv(
    "TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p/w500"
)


def slugify(text: str) -> str:
    """Very simple slugify: lower, replace spaces with dashes, keep alnum and dashes."""
    import re

    text = text.lower().strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-]", "", text)
    # collapse multiple dashes
    text = re.sub(r"-{2,}", "-", text)
    return text


def fetch_now_playing(
    api_key: str,
    base_url: str,
    region: str = "GB",
    language: str = "en-GB",
    max_pages: int = 2,
) -> list[dict[str, Any]]:
    """Fetch 'now playing' films from TMDB for a region, with simple pagination."""
    all_results: list[dict[str, Any]] = []
    page = 1

    while page <= max_pages:
        resp = requests.get(
            f"{base_url}/movie/now_playing",
            params={
                "api_key": api_key,
                "region": region,
                "language": language,
                "page": page,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        all_results.extend(results)

        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1

    return all_results


def ingest_now_playing(
    region: str = "GB", language: str = "en-GB", max_pages: int = 2
) -> None:
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY is not set in backend/.env")

    # Fetch from TMDB first (so if this fails we never touch the DB)
    movies_raw = fetch_now_playing(
        api_key=TMDB_API_KEY,
        base_url=TMDB_BASE_URL,
        region=region,
        language=language,
        max_pages=max_pages,
    )

    top_movies = sorted(
        movies_raw,
        key=lambda item: float(item.get("popularity") or 0.0),
        reverse=True,
    )[:10]

    session = SessionLocal()
    try:
        with mlflow.start_run(run_name="ingest_now_playing_tmdb"):
            mlflow.log_param("api_source", "tmdb")
            mlflow.log_param("region", region)
            mlflow.log_param("language", language)
            mlflow.log_param("max_pages", max_pages)
            mlflow.log_metric("num_fetched", len(movies_raw))
            mlflow.log_metric("num_selected", len(top_movies))

            inserted = 0
            updated = 0
            runtime_titles: list[str] = []

            # Start with a clean slate so only top-N are active
            deactivated = session.query(Movie).update(
                {Movie.is_active: False}, synchronize_session=False
            )
            mlflow.log_metric("num_deactivated", float(deactivated or 0))

            for item in top_movies:
                tmdb_id = item.get("id")
                if tmdb_id is None:
                    continue

                tmdb_id_str = str(tmdb_id)

                title = item.get("title") or item.get("original_title")
                if not title:
                    continue

                overview = item.get("overview") or None
                poster_path = item.get("poster_path")
                poster_url = (
                    f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None
                )

                release_date = item.get("release_date") or ""
                year = release_date.split("-")[0] if release_date else ""

                base_slug = f"{title}-{year}" if year else title
                candidate_slug = slugify(base_slug)

                # Existing by external_id?
                existing = (
                    session.query(Movie)
                    .filter(Movie.external_id == tmdb_id_str)
                    .first()
                )

                if existing:
                    existing.title = title
                    existing.overview = overview
                    existing.poster_url = poster_url
                    existing.is_active = True
                    if not existing.slug:
                        existing.slug = candidate_slug
                    updated += 1
                    runtime_titles.append(existing.title)
                    continue

                # If no external-id match, ensure slug is unique
                slug = candidate_slug
                slug_clash = session.query(Movie).filter(Movie.slug == slug).first()
                if slug_clash:
                    slug = f"{candidate_slug}-{tmdb_id_str}"

                movie = Movie(
                    external_id=tmdb_id_str,
                    title=title,
                    slug=slug,
                    poster_url=poster_url,
                    overview=overview,
                    is_active=True,
                )
                session.add(movie)
                inserted += 1
                runtime_titles.append(title)

            session.commit()

            mlflow.log_metric("num_inserted", inserted)
            mlflow.log_metric("num_updated", updated)

            # Save a small artifact listing ingested/updated titles
            artifact_path = "ingested_movies.txt"
            with open(artifact_path, "w", encoding="utf-8") as f:
                for t in runtime_titles:
                    f.write(f"{t}\n")

            mlflow.log_artifact(artifact_path)

            print(
                f"Ingested now playing from TMDB (top {len(top_movies)}). "
                f"Inserted={inserted}, Updated={updated}, Total raw={len(movies_raw)}"
            )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    ingest_now_playing()
