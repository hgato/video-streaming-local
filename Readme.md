## Run command

```bash
docker compose -p vsl -f docker-compose.yml -f docker-compose.gateway.yml -f docker-compose.auth.yml -f docker-compose.websocket.yml -f docker-compose.web.yml -f docker-compose.video-lifecycle-db.yml up -d
```