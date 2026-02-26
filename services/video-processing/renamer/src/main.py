import os
import uuid
from pathlib import PurePosixPath

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error

app = FastAPI(title="Renamer Service")

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")

BUCKET_ORIGINAL = "videos-original"
BUCKET_PROCESSED = "videos-processed"


def get_minio_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


class RenameRequest(BaseModel):
    file: str
    name: str
    year: int


@app.post("/")
def rename_video(req: RenameRequest):
    extension = PurePosixPath(req.file).suffix
    if not extension:
        raise HTTPException(status_code=400, detail="File has no extension")

    short_hash = uuid.uuid4().hex[:8]
    new_name = f"{req.name} ({req.year}).{short_hash}{extension}"

    client = get_minio_client()

    try:
        client.stat_object(BUCKET_ORIGINAL, req.file)
    except S3Error as e:
        raise HTTPException(status_code=400, detail=f"File not found in {BUCKET_ORIGINAL}: {req.file}. Error: {e}")

    try:
        client.copy_object(
            BUCKET_PROCESSED,
            new_name,
            CopySource(BUCKET_ORIGINAL, req.file),
        )
        client.remove_object(BUCKET_ORIGINAL, req.file)
    except S3Error as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"original": req.file, "renamed": new_name}
