import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta

import redis
from confluent_kafka import Consumer, Producer, KafkaError
from minio import Minio

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
REDIS_HOST = os.environ.get("REDIS_HOST", "video-lifecycle-db")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")

INGEST_TOPIC = "video-pipeline.01-ingest"
TRANSCODE_TOPIC = "video-pipeline.02-transcode"
FINALIZING_TOPIC = "video-pipeline.04-finalizing"

BUCKET = "videos-ready"
CLEANUP_INTERVAL = 600


def create_consumer():
    return Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "lifecycle-manager",
        "auto.offset.reset": "earliest",
    })


def create_producer():
    return Producer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    })


def create_minio_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def handle_message(msg, r, producer):
    payload = json.loads(msg.value().decode("utf-8"))

    video_item_id = str(uuid.uuid4())
    expires_on = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()

    metadata = payload.get("metadata", {})
    output_config = payload.get("output_config", {})

    r.hset(f"video:{video_item_id}", mapping={
        "user_id": metadata.get("user_id", ""),
        "video_id": metadata.get("video_id", ""),
        "source_filename": metadata.get("source_filename", ""),
        "manifest_filename": "",
        "config": json.dumps(output_config),
        "expires_on": expires_on,
    })

    print(f"Saved video:{video_item_id} to Redis (expires_on={expires_on})")

    payload.setdefault("metadata", {})
    payload["metadata"]["video_item_id"] = video_item_id

    producer.produce(
        TRANSCODE_TOPIC,
        value=json.dumps(payload).encode("utf-8"),
    )
    producer.flush()

    print(f"Forwarded message to {TRANSCODE_TOPIC} with video_item_id={video_item_id}")


def handle_finalizing_message(msg, r):
    payload = json.loads(msg.value().decode("utf-8"))

    metadata = payload.get("metadata", {})
    video_item_id = metadata.get("video_item_id", "")
    manifest_filename = payload.get("manifest_filename", "")

    if not video_item_id:
        print("Finalizing message missing video_item_id, skipping")
        return

    key = f"video:{video_item_id}"
    if not r.exists(key):
        print(f"No Redis entry found for {key}, skipping finalizing update")
        return

    r.hset(key, "manifest_filename", manifest_filename)
    print(f"Updated {key} with manifest_filename={manifest_filename}")


def cleanup_expired_videos(r, minio_client):
    keys = r.keys("video:*")
    now = datetime.now(timezone.utc)

    for key in keys:
        expires_on = r.hget(key, "expires_on")
        if not expires_on:
            continue

        try:
            expiry = datetime.fromisoformat(expires_on)
        except ValueError:
            print(f"Invalid expires_on for {key}: {expires_on}")
            continue

        if expiry >= now:
            continue

        video_item_id = key.removeprefix("video:")
        prefix = f"{video_item_id}/"

        try:
            objects = list(minio_client.list_objects(BUCKET, prefix=prefix, recursive=True))
            if objects:
                from minio.deleteobjects import DeleteObject
                delete_list = [DeleteObject(obj.object_name) for obj in objects]
                errors = list(minio_client.remove_objects(BUCKET, delete_list))
                for err in errors:
                    print(f"MinIO delete error: {err}")
                print(f"Removed {len(objects)} object(s) from {BUCKET}/{prefix}")
            else:
                print(f"No objects found in {BUCKET}/{prefix}")
        except Exception as e:
            print(f"Error cleaning MinIO for {video_item_id}: {e}")

        r.delete(key)
        print(f"Deleted expired Redis key {key}")


def cleanup_loop(r, minio_client):
    while True:
        time.sleep(CLEANUP_INTERVAL)
        print("Running expired video cleanup...")
        try:
            cleanup_expired_videos(r, minio_client)
        except Exception as e:
            print(f"Cleanup error: {e}")
        print("Cleanup cycle complete")


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r.ping()
    print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")

    minio_client = create_minio_client()
    print(f"MinIO client configured for {MINIO_ENDPOINT}")

    cleanup_thread = threading.Thread(target=cleanup_loop, args=(r, minio_client), daemon=True)
    cleanup_thread.start()
    print("Started cleanup thread")

    consumer = create_consumer()
    producer = create_producer()
    consumer.subscribe([INGEST_TOPIC, FINALIZING_TOPIC])
    print(f"Subscribed to {INGEST_TOPIC} and {FINALIZING_TOPIC}, waiting for messages...")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Kafka error: {msg.error()}")
                continue

            topic = msg.topic()
            if topic == INGEST_TOPIC:
                handle_message(msg, r, producer)
            elif topic == FINALIZING_TOPIC:
                handle_finalizing_message(msg, r)
            else:
                print(f"Unknown topic: {topic}")
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
