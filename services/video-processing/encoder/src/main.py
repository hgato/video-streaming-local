import json
import os
import subprocess
import tempfile

from confluent_kafka import Consumer, Producer, KafkaError
from minio import Minio

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")

TRANSCODE_TOPIC = "video-pipeline.02-transcode"
CHUNKING_TOPIC = "video-pipeline.03-chunking"

SOURCE_BUCKET = "videos-processed"
DEST_BUCKET = "videos-ready"

RESOLUTION_MAP = {
    "2160p": 2160,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
}


def create_consumer():
    return Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "video-encoder",
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


def ensure_bucket(minio_client, bucket_name):
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
        print(f"Created bucket: {bucket_name}")


def encode_video(input_path, output_path, height):
    cmd = [
        "ffmpeg", "-i", input_path,
        "-vf", f"scale=-2:{height}",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-y",
        output_path,
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg stderr: {result.stderr}")
        raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}")


def handle_message(msg, minio_client, producer):
    payload = json.loads(msg.value().decode("utf-8"))

    metadata = payload.get("metadata", {})
    output_config = payload.get("output_config", {})

    source_filename = metadata.get("source_filename", "")
    video_item_id = metadata.get("video_item_id", "")
    user_id = metadata.get("user_id", "")
    video_id = metadata.get("video_id", "")
    resolutions = output_config.get("resolutions", ["1080p", "720p", "480p"])

    print(f"Processing video_item_id={video_item_id}, resolutions={resolutions}")

    ensure_bucket(minio_client, DEST_BUCKET)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "source.mp4")
        minio_client.fget_object(SOURCE_BUCKET, source_filename, input_path)
        print(f"Downloaded {SOURCE_BUCKET}/{source_filename}")

        encoded_files = []
        for resolution in resolutions:
            height = RESOLUTION_MAP.get(resolution)
            if height is None:
                print(f"Unknown resolution: {resolution}, skipping")
                continue

            output_filename = f"{resolution}.mp4"
            output_path = os.path.join(tmpdir, output_filename)

            encode_video(input_path, output_path, height)

            object_name = f"{video_item_id}/{output_filename}"
            minio_client.fput_object(DEST_BUCKET, object_name, output_path)
            print(f"Uploaded {DEST_BUCKET}/{object_name}")

            encoded_files.append(output_filename)

    chunking_message = {
        "metadata": {
            "user_id": user_id,
            "video_id": video_id,
            "video_item_id": video_item_id,
        },
        "chunking": {
            "format": output_config.get("format", "hls"),
            "time_seconds": output_config.get("time_seconds", 6),
        },
        "files": encoded_files,
    }

    producer.produce(
        CHUNKING_TOPIC,
        value=json.dumps(chunking_message).encode("utf-8"),
    )
    producer.flush()

    print(f"Forwarded message to {CHUNKING_TOPIC} with video_item_id={video_item_id}")


def main():
    minio_client = create_minio_client()
    print(f"Connected to MinIO at {MINIO_ENDPOINT}")

    consumer = create_consumer()
    producer = create_producer()
    consumer.subscribe([TRANSCODE_TOPIC])
    print(f"Subscribed to {TRANSCODE_TOPIC}, waiting for messages...")

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

            handle_message(msg, minio_client, producer)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
