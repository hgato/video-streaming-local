import glob
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

CHUNKING_TOPIC = "video-pipeline.03-chunking"
FINALIZING_TOPIC = "video-pipeline.04-finalizing"

BUCKET = "videos-ready"

RESOLUTION_MAP = {
    "2160p": {"bandwidth": 14000000, "width": 3840, "height": 2160},
    "1080p": {"bandwidth": 5000000,  "width": 1920, "height": 1080},
    "720p":  {"bandwidth": 2800000,  "width": 1280, "height": 720},
    "480p":  {"bandwidth": 1400000,  "width": 854,  "height": 480},
    "360p":  {"bandwidth": 800000,   "width": 640,  "height": 360},
}


def create_consumer():
    return Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "video-chunker",
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


def segment_video(input_path, tmpdir, resolution, time_seconds):
    segment_pattern = os.path.join(tmpdir, f"{resolution}_%03d.ts")
    playlist_path = os.path.join(tmpdir, f"{resolution}.m3u8")

    cmd = [
        "ffmpeg", "-i", input_path,
        "-c", "copy",
        "-f", "hls",
        "-hls_time", str(time_seconds),
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", segment_pattern,
        playlist_path,
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg stderr: {result.stderr}")
        raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}")

    return playlist_path


def generate_master_playlist(tmpdir, resolutions):
    lines = ["#EXTM3U"]
    for resolution in resolutions:
        info = RESOLUTION_MAP.get(resolution)
        if info is None:
            continue
        lines.append(
            f"#EXT-X-STREAM-INF:BANDWIDTH={info['bandwidth']},"
            f"RESOLUTION={info['width']}x{info['height']}"
        )
        lines.append(f"{resolution}.m3u8")

    master_path = os.path.join(tmpdir, "master.m3u8")
    with open(master_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return master_path


def handle_message(msg, minio_client, producer):
    payload = json.loads(msg.value().decode("utf-8"))

    metadata = payload.get("metadata", {})
    chunking = payload.get("chunking", {})
    files = payload.get("files", [])

    user_id = metadata.get("user_id", "")
    video_id = metadata.get("video_id", "")
    video_item_id = metadata.get("video_item_id", "")
    time_seconds = chunking.get("time_seconds", 6)

    print(f"Processing video_item_id={video_item_id}, files={files}")

    with tempfile.TemporaryDirectory() as tmpdir:
        processed_resolutions = []

        for file in files:
            resolution = file.replace(".mp4", "")
            object_name = f"{video_item_id}/{file}"

            input_path = os.path.join(tmpdir, file)
            minio_client.fget_object(BUCKET, object_name, input_path)
            print(f"Downloaded {BUCKET}/{object_name}")

            segment_video(input_path, tmpdir, resolution, time_seconds)
            processed_resolutions.append(resolution)

            # Upload .ts segments
            for ts_file in sorted(glob.glob(os.path.join(tmpdir, f"{resolution}_*.ts"))):
                ts_name = os.path.basename(ts_file)
                minio_client.fput_object(BUCKET, f"{video_item_id}/{ts_name}", ts_file)
                print(f"Uploaded {BUCKET}/{video_item_id}/{ts_name}")

            # Upload per-resolution playlist
            m3u8_path = os.path.join(tmpdir, f"{resolution}.m3u8")
            minio_client.fput_object(BUCKET, f"{video_item_id}/{resolution}.m3u8", m3u8_path)
            print(f"Uploaded {BUCKET}/{video_item_id}/{resolution}.m3u8")

            # Delete source .mp4 from MinIO
            minio_client.remove_object(BUCKET, object_name)
            print(f"Deleted {BUCKET}/{object_name}")

        # Generate and upload master playlist
        master_path = generate_master_playlist(tmpdir, processed_resolutions)
        minio_client.fput_object(BUCKET, f"{video_item_id}/master.m3u8", master_path)
        print(f"Uploaded {BUCKET}/{video_item_id}/master.m3u8")

    # Produce to finalizing topic
    finalizing_message = {
        "metadata": {
            "user_id": user_id,
            "video_id": video_id,
            "video_item_id": video_item_id,
        },
        "manifest_filename": "master.m3u8",
    }

    producer.produce(
        FINALIZING_TOPIC,
        value=json.dumps(finalizing_message).encode("utf-8"),
    )
    producer.flush()

    print(f"Forwarded message to {FINALIZING_TOPIC} with video_item_id={video_item_id}")


def main():
    minio_client = create_minio_client()
    print(f"Connected to MinIO at {MINIO_ENDPOINT}")

    consumer = create_consumer()
    producer = create_producer()
    consumer.subscribe([CHUNKING_TOPIC])
    print(f"Subscribed to {CHUNKING_TOPIC}, waiting for messages...")

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
