# Docker setup

The image serves Django, the API, and the frontend SPA through Gunicorn on port
8080. On startup it applies migrations and runs the idempotent lesson seed.

## Build

```bash
docker build -t handsign:local .
```

## Configure

```bash
cp .env.example .env
```

For a local container, review at least:

```env
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:8080
DATABASE_PATH=/app/data/db.sqlite3
GEMINI_FEEDBACK_ENABLED=false
```

Replace `SECRET_KEY` before any shared or public deployment. Add Gemini and
Stripe keys only when those features are needed.

## Run with persistent data

```bash
docker volume create handsign-data
docker run --name handsign \
  --env-file .env \
  -p 8080:8080 \
  -v handsign-data:/app/data \
  handsign:local
```

Open <http://localhost:8080/>.

Run in the background by adding `-d`.

## Logs and administration

```bash
docker logs -f handsign
docker exec -it handsign python manage.py createsuperuser
docker exec -it handsign python manage.py check
docker exec -it handsign python manage.py test
```

## Video guides

Large/local video files should usually be mounted rather than baked into the
image:

```bash
docker run --name handsign \
  --env-file .env \
  -p 8080:8080 \
  -v handsign-data:/app/data \
  -v /absolute/path/to/raw_videos:/app/raw_videos:ro \
  handsign:local
```

Store URLs in `Word.video_url_ru` and `Word.video_url_en`, for example
`/raw_videos/help-ru.mp4` and `/raw_videos/help-en.mp4`.

English and Czech UI select the English guide; Russian UI selects the Russian
guide. Missing assets show an intentional placeholder.

## Stop, restart, and update

```bash
docker stop handsign
docker start handsign
```

To deploy a rebuilt image while preserving the named volume:

```bash
docker stop handsign
docker rm handsign
docker build -t handsign:local .
docker run -d --name handsign \
  --env-file .env \
  -p 8080:8080 \
  -v handsign-data:/app/data \
  handsign:local
```

Removing the container does not remove the named `handsign-data` volume. Do not
delete that volume unless the database is intentionally being discarded.

## Production considerations

The included container is a useful single-instance baseline, not a complete
production platform.

- Put it behind an HTTPS reverse proxy; webcam access requires a secure origin.
- Restrict `ALLOWED_HOSTS` and CORS.
- Persist `/app/data` or use a managed database.
- Arrange backups before upgrades.
- Review Gunicorn worker count for the available memory/CPU.
- Configure SMTP, Stripe webhooks, observability, and secret storage.
- Do not expose Django debug mode.
- Do not commit `.env` or licensed video datasets.

## Health check

```bash
curl http://localhost:8080/api/v1/health/
```

Expected response:

```json
{"status":"ok","service":"HandSign AI Tutor Backend","version":"1.0.0"}
```
