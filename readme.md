# Video streaming local

This project is intended as experimental streaming service. Main goal is to create a streaming service "inside-out". 
It does not store chunks for streaming, it makes chunks on the runtime instead. This is beneficial for saving the space
but in reality ineffective for user-friendliness.

Architecture explanation is in `/docs` folder.

Information about usage is below.

This is experimental code for architecture testing. Big chunks are generated with AI and are of low quality.
This project is not intended for production usage without severe testing and configuring.

## Installation notes

Relies on repository https://github.com/hgato/auth-service-python-fast-api. Code must be placed in `/services/auth` directory.

## Endpoints

All requests go through Traefik on port `80`.

### Auth — `/api/auth`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/auth/register` | — | Register a new user |
| `POST` | `/api/auth/token` | — | Login, returns `access_token` + `refresh_token` |
| `POST` | `/api/auth/token/refresh` | — | Exchange a refresh token for a new access token |
| `GET`  | `/api/auth/verify` | JWT | Verify the current access token and return user info |

### Videos — `/api/videos`

| Method | Path                                | Auth | Description |
|--------|-------------------------------------|------|-------------|
| `GET`  | `/api/videos/videos?search=<query>` | JWT | List videos; optionally filter by name or year |
| `POST` | `/api/videos/videos/{id}/prepare`   | JWT | Trigger processing pipeline for a video |

> Paths under `/api/videos/internal` are blocked at the gateway (403).

### WebSocket — `/api/ws`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `WS` | `/api/ws` | JWT (query param `?jwt=`) | Socket.io connection; emits `video:ready` with `{ video_id, manifest_url }` when a video finishes processing |

### Streaming — `/stream/videos`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/stream/videos/{video_item_id}/master.m3u8` | — | HLS master playlist from the `videos-ready` bucket |
| `GET` | `/stream/videos/{video_item_id}/{resolution}.m3u8` | — | Per-resolution HLS playlist |
| `GET` | `/stream/videos/{video_item_id}/{segment}.ts` | — | HLS video segment |

---

## Run command

```bash
docker compose -p vsl \
  -f docker-compose.yml \
  -f docker-compose.gateway.yml \
  -f docker-compose.auth.yml \
  -f docker-compose.kafka.yml \
  -f docker-compose.minio.yml \
  -f docker-compose.websocket.yml \
  -f docker-compose.videos.yml \
  -f docker-compose.video-processing.yml \
  -f docker-compose.web.yml \
  -f docker-compose.ingest-cli.yml
  up -d
```

## Ingesting a Video

The `ingest-cli` service is a long-running container that you interact with via `docker exec`. It uploads a video file to object storage, renames it, and registers it in the videos service.

### 1. Place file
s in the ingest data directory

Copy your video file and a JSON metadata file into `data/ingest/`:

```
data/ingest/
├── my-movie.mp4
└── my-movie.json
```

**JSON format:**

```json
{
  "file": "my-movie.mp4",
  "name": "My Movie",
  "year": 2024
}
```

| Field  | Type   | Description                                       |
|--------|--------|---------------------------------------------------|
| `file` | string | Filename of the video in the `/data` directory    |
| `name` | string | Display name for the video                        |
| `year` | number | Release year                                      |

### 2. Run the ingest command

```bash
docker exec ingest-cli python -m src.main my-movie.json
```

The CLI will:
1. Upload the video to MinIO (`videos-original` bucket)
2. Call the renamer service to rename and move it to `videos-processed`
3. Register the video record in the videos service
