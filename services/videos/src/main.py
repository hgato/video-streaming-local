import base64
import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.broker import get_producer
from src.db import connect_db, close_db, get_db

LIFECYCLE_MANAGER_URL = os.environ.get("LIFECYCLE_MANAGER_URL", "http://video-lifecycle-manager:8002")


def extract_user_id(authorization: str) -> str:
    try:
        token = authorization.removeprefix("Bearer ").strip()
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        return payload.get("id", "")
    except Exception:
        return ""

INGEST_TOPIC = "video-pipeline.01-ingest"

HARDCODED_OUTPUT_CONFIG = {
    "resolutions": ["1080p", "720p", "480p", "360p"],
    "format": "hls",
    "time_seconds": 6,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(title="Videos Service", lifespan=lifespan)


class VideoCreate(BaseModel):
    name: str
    year: str
    filename: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/internal/videos", status_code=201)
async def create_video(video: VideoCreate):
    db = get_db()
    video_id = str(uuid.uuid4())
    await db["videos"].insert_one({
        "id": video_id,
        "name": video.name,
        "year": video.year,
        "filename": video.filename,
    })
    return {"id": video_id, "name": video.name, "year": video.year}


@app.get("/videos")
async def list_videos(search: Optional[str] = None):
    db = get_db()
    query = {}
    if search:
        query = {"$or": [
            {"name": {"$regex": search, "$options": "i"}},
            {"year": {"$regex": search, "$options": "i"}},
        ]}
    cursor = db["videos"].find(query, {"_id": 0, "id": 1, "name": 1, "year": 1})
    videos = await cursor.to_list(length=None)
    return {"videos": videos}


@app.get("/videos/{id}/status")
async def get_video_status(id: str, x_consumer_username: str = Header(default="")):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{LIFECYCLE_MANAGER_URL}/videos/{id}/status",
            headers={"X-User-ID": x_consumer_username},
            timeout=5.0,
        )
    return resp.json()


@app.post("/videos/{id}/prepare", status_code=200)
async def prepare_video(id: str, authorization: str = Header(default="")):
    db = get_db()
    video = await db["videos"].find_one({"id": id})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    user_id = extract_user_id(authorization)

    payload = {
        "metadata": {
            "video_id": id,
            "user_id": user_id,
            "source_filename": video["filename"],
        },
        "output_config": HARDCODED_OUTPUT_CONFIG,
    }

    producer = get_producer()
    producer.produce(INGEST_TOPIC, value=json.dumps(payload).encode("utf-8"))
    producer.flush()

    return {}
