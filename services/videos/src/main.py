import json
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.broker import get_producer
from src.db import connect_db, close_db, get_db

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


@app.post("/videos/{id}/prepare", status_code=200)
async def prepare_video(id: str):
    db = get_db()
    video = await db["videos"].find_one({"id": id})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    payload = {
        "metadata": {
            "video_id": id,
            "source_filename": video["filename"],
        },
        "output_config": HARDCODED_OUTPUT_CONFIG,
    }

    producer = get_producer()
    producer.produce(INGEST_TOPIC, value=json.dumps(payload).encode("utf-8"))
    producer.flush()

    return {}
