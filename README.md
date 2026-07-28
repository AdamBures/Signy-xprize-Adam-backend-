# HandSign

HandSign is a Django REST API and dependency-free JavaScript SPA for learning
American Sign Language (ASL). It provides guided lessons, browser-side hand
tracking, landmark-based evaluation, saved progress, streaks, rewards, a
Gemini-backed free-sign translator, profiles, friends, a leaderboard, and
optional Stripe premium access.

This document describes the current implementation. For deeper technical
details, see [ARCHITECTURE.md](ARCHITECTURE.md), [TESTING.md](TESTING.md), and
[HANDOFF.md](HANDOFF.md).

## Current behavior

- The frontend and API are served by the same Django application.
- MediaPipe runs in the browser. Camera frames are not continuously uploaded.
- A guided attempt sends captured hand landmarks to the evaluation endpoint.
- One- and two-hand signs are supported. Two-hand capture waits for a stable
  sequence and preserves the captured frames after the user lowers their hands.
- A score above 15% unlocks navigation to the next word.
- A score of 60% or more marks a word completed.
- Progress stores the personal best per user and word.
- Rewards are granted only when the personal best improves: 60 XP and 10 coins.
- Every authenticated attempt creates an activity entry for streak tracking,
  including attempts that do not improve the personal best.
- Gemini feedback is optional. Deterministic evaluation and progress saving
  continue working if Gemini is unavailable.
- Free translation tries configured Gemini models in order and returns a
  friendly error if all models fail.
- Russian UI uses Russian sign-guide videos. English and Czech UI use English
  sign-guide videos. A clear placeholder is shown when no video is available.
- UI languages: English, Russian, and Czech.

## Technology

- Python 3.11+
- Django 5 and Django REST Framework
- SQLite by default
- Vanilla JavaScript, HTML, and CSS
- MediaPipe Hands in the browser
- Google Gen AI SDK
- Stripe SDK
- Gunicorn and WhiteNoise for container deployment

## Quick start

Linux/macOS:

```bash
git clone https://github.com/n1xone/Signy-xprize-Adam-backend-.git
cd Signy-xprize-Adam-backend-
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_lessons
python manage.py runserver 8080
```

Windows PowerShell:

```powershell
git clone https://github.com/n1xone/Signy-xprize-Adam-backend-.git
cd Signy-xprize-Adam-backend-
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_lessons
python manage.py runserver 8080
```

Open <http://127.0.0.1:8080/>.

The application works without Gemini or Stripe credentials. Translation,
optional AI coaching, and real checkout require their respective keys.

Detailed local instructions are in [LOCAL_SETUP.md](LOCAL_SETUP.md). Docker
instructions are in [DOCKER_SETUP.md](DOCKER_SETUP.md).

## Environment variables

Copy `.env.example` to `.env`. Never commit real credentials.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django signing secret; replace in production |
| `DEBUG` | Django debug mode |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `CORS_ALLOWED_ORIGINS` | Documented allowed origins; current settings allow all origins during development |
| `DATABASE_PATH` | Optional SQLite database path |
| `GEMINI_API_KEY` | Enables Gemini translation and optional coaching |
| `GEMINI_FEEDBACK_ENABLED` | Set `true` to enable Gemini-generated attempt advice |
| `GEMINI_MODEL` | First Gemini model to try |
| `GEMINI_MODELS` | Comma-separated fallback model list |
| `STRIPE_SECRET_KEY` | Stripe server key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signature secret |
| `FRONTEND_URL` | Redirect base used by checkout |

Model availability changes over time. Keep `GEMINI_MODEL` and
`GEMINI_MODELS` aligned with models enabled for the project’s Gemini account.

## Important commands

```bash
# Database
python manage.py migrate
python manage.py makemigrations --check --dry-run

# Seed the built-in lesson catalog (safe to run repeatedly)
python manage.py seed_lessons

# Administrator account (never created by seed_lessons)
python manage.py createsuperuser

# Tests and static validation
python manage.py test
python manage.py check
node --check app.js
node --check api.js
node --check i18n.js
node --check tracker.js
git diff --check

# Production static assets
python manage.py collectstatic --noinput
```

## API overview

The primary client API is under `/api/v1/`. Protected endpoints accept:

```text
Authorization: Bearer <token>
```

| Method and path | Purpose |
| --- | --- |
| `GET /api/v1/health/` | Health check |
| `POST /api/v1/auth/register/` | Register and receive a token |
| `POST /api/v1/auth/login/` | Log in and receive a token |
| `GET /api/v1/lessons/` | Paginated word/lesson catalog |
| `GET /api/v1/lessons/<id>/` | Word detail and reference data |
| `GET /api/v1/me/` | Current profile |
| `PATCH /api/v1/me/` | Update profile and preferences |
| `GET /api/v1/me/progress/` | Saved best scores and summary |
| `POST /api/v1/practice/evaluate/` | Evaluate captured landmarks |
| `GET /api/v1/practice/quiz/` | Placement/practice quiz |
| `POST /api/v1/translate/` | Translate an uploaded sign clip |
| `GET /api/v1/friends/` | Friends, requests, and suggestions |
| `POST /api/v1/friends/request/` | Send a friend request |
| `POST /api/v1/friends/respond/` | Accept or reject a request |
| `GET /api/v1/leaderboard/` | XP leaderboard |
| `GET /api/v1/countries/` | Active leaderboard countries |
| `POST /api/v1/store/buy-premium/` | Buy temporary premium with coins |
| `POST /api/v1/billing/checkout/` | Create Stripe Checkout |
| `POST /api/v1/billing/stripe-webhook/` | Process Stripe events |

Legacy modular routes under `/api/users/`, `/api/lessons/`, and
`/api/evaluation/` remain available, but new frontend work should use
`/api/v1/`.

## Sign-guide videos

Each `Word` supports:

- `video_url_ru`: Russian sign-language guide, selected for Russian UI.
- `video_url_en`: English sign-language guide, selected for English/Czech UI.
- `video_url`: legacy/default English fallback.

URLs may be remote or local paths such as `/raw_videos/example.mp4`. Missing
videos do not break a lesson; the UI keeps written shape, position, and movement
instructions available.

The repository intentionally does not require a large video dataset. Coordinate
video assets with the project owner and do not commit licensed datasets without
permission.

## Repository map

```text
config/       Django settings and root URLs
evaluation/   Landmark scoring, Gemini fallback, evaluate/translate views
lessons/      Categories, words, progress, seed/import commands
users/        User model, auth, social, streak, rewards, billing
app.js        SPA routes, UI state, practice/translation flows
tracker.js    Browser MediaPipe integration and frame capture
api.js        Frontend API adapter and friendly transport handling
i18n.js       English/Russian/Czech UI and lesson text
styles.css    Responsive UI and themes
index.html    SPA entry point
```

## Security and production notes

- Set `DEBUG=False`, a strong `SECRET_KEY`, and restricted `ALLOWED_HOSTS`.
- Review CORS settings before public deployment; development currently permits
  all origins.
- Serve only over HTTPS so browsers permit camera access.
- Use a persistent database/volume. SQLite is suitable for local development,
  not a horizontally scaled deployment.
- Configure SMTP if reminder emails are required outside development.
- Configure Stripe webhook verification before enabling paid access.
- Review privacy, retention, and consent requirements before storing clips or
  biometric landmark data. The current guided evaluator stores scores, not raw
  attempt sequences.

## Status

The current baseline passes 21 Django tests and browser checks for profile
dropdown behavior, localized guide selection, one-hand capture, two-hand grace
capture, and progress flows. See [TESTING.md](TESTING.md) for the release
checklist and known hardware-dependent checks.
