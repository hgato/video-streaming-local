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

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET`  | `/api/videos?search=<query>` | JWT | List videos; optionally filter by name or year |
| `POST` | `/api/videos/{id}/prepare` | JWT | Trigger processing pipeline for a video |

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
  up -d
```