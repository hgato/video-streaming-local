import json
import os
import sys
from pathlib import Path

import requests
from minio import Minio
from minio.error import S3Error

RENAMER_URL = os.environ.get("RENAMER_URL", "http://renamer-service:8000")
VIDEOS_URL = os.environ.get("VIDEOS_URL", "http://videos-service:8001")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
BUCKET_ORIGINAL = "videos-original"
DATA_DIR = Path("/data")


def get_minio_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <input.json>")
        print("  The JSON file and the video file must be placed in /data.")
        print("  JSON format: {\"file\": \"video.mp4\", \"name\": \"My Video\", \"year\": 2024}")
        sys.exit(1)

    json_path = DATA_DIR / sys.argv[1]
    with open(json_path) as f:
        data = json.load(f)

    file = data["file"]
    name = data["name"]
    year = str(data["year"])

    video_path = DATA_DIR / file
    if not video_path.exists():
        print(f"Error: video file not found at {video_path}")
        sys.exit(1)

    print(f"Uploading {file!r} to MinIO bucket {BUCKET_ORIGINAL!r}")
    client = get_minio_client()
    ensure_bucket(client, BUCKET_ORIGINAL)
    try:
        client.fput_object(BUCKET_ORIGINAL, file, str(video_path))
    except S3Error as e:
        print(f"Error uploading to MinIO: {e}")
        sys.exit(1)
    print(f"Uploaded {file!r}")

    print(f"Renaming {file!r} -> {name!r} ({year})")
    resp = requests.post(f"{RENAMER_URL}/", json={"file": file, "name": name, "year": int(year)})
    resp.raise_for_status()
    renamed = resp.json()["renamed"]
    print(f"Renamed to {renamed!r}")

    print("Saving video record")
    resp = requests.post(
        f"{VIDEOS_URL}/internal/videos",
        json={"name": name, "year": year, "filename": renamed},
    )
    resp.raise_for_status()
    video = resp.json()
    print(f"Done: id={video['id']} name={video['name']} year={video['year']} filename={renamed}")


if __name__ == "__main__":
    main()
