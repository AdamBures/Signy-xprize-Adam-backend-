# HandSign

HandSign is a Django application for guided American Sign Language (ASL)
practice. It includes a responsive single-page frontend, on-device MediaPipe
hand and face tracking, landmark-based lesson evaluation, optional Gemini
coaching, accounts, progress, friends, and Stripe checkout.

## What works

- Guided lessons and a searchable lesson library.
- Browser camera capture with MediaPipe Hands (21 landmarks).
- Optional **Help** mode with a centered animated reference hand and movement
  arrow. The guide is hidden by default and does not interfere with assessment.
- Automatic attempt capture: after a stable sequence has been recorded, the UI
  confirms that the learner can lower their hands and unlocks the check button.
- One- and two-hand lesson support. Two-hand reference frames contain 42 ordered
  landmarks and the tracker waits until both hands are visible.
- Non-manual facial marker capture for lessons that require it. The seed data
  currently enables this for `Happy`, `Sad`, and `Sleep`; fingerspelling
  letters do not require facial expression.
- Normalized, time-resampled hand comparison on the Django backend.
- Gemini-generated coaching when `GEMINI_API_KEY` is configured.
- Authentication, user progress, friends, profile avatars, and Stripe Checkout.
- Free-form clip capture and translation endpoint. Without Gemini it returns an
  explicit demo result with zero confidence rather than pretending recognition
  succeeded.

Camera inference runs in the browser. An evaluation request sends landmark
coordinates and compact facial measurements, not raw camera frames. Translation
can additionally send a recorded clip when the user explicitly starts recording.

## Requirements

- Python **3.11** (recommended; the pinned MediaPipe release does not support
  every newer Python version)
- A modern Chromium/Firefox browser
- Internet access on first browser use for MediaPipe assets served by jsDelivr
- Camera access via `localhost` or HTTPS
- Optional: Docker

## Local development

### Linux/macOS (Bash or Zsh)

```bash
git clone https://github.com/AdamBures/Signy-xprize-Adam-backend-.git
cd Signy-xprize-Adam-backend-

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cp .env.example .env
python manage.py migrate
python manage.py seed_lessons
python manage.py runserver 8080
```

### Fish shell

```fish
python3.11 -m venv .venv
source .venv/bin/activate.fish
python -m pip install -r requirements.txt

cp .env.example .env
python manage.py migrate
python manage.py seed_lessons
python manage.py runserver 8080
```

Open <http://localhost:8080/>.

Activation is optional. The unambiguous form is:

```bash
.venv/bin/python manage.py runserver 8080
```

Do not use `pip --break-system-packages` on Arch Linux. If `pip` reports an
externally managed environment, the virtual environment is not active.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_lessons
python manage.py runserver 8080
```

## Docker

```bash
cp .env.example .env
docker build -t handsign .
docker run --rm --name handsign-app --env-file .env -p 8080:8080 handsign
```

The container applies migrations and seeds lessons on startup. To persist the
SQLite database and local videos between container recreations:

```bash
mkdir -p .docker-data raw_videos
docker run --rm --name handsign-app \
  --env-file .env \
  -e DATABASE_PATH=/app/data/db.sqlite3 \
  -p 8080:8080 \
  -v "$PWD/.docker-data:/app/data" \
  -v "$PWD/raw_videos:/app/raw_videos" \
  handsign
```

Without `DATABASE_PATH` and the `/app/data` mount, container data is ephemeral.

## Configuration

Copy `.env.example` to `.env`:

```dotenv
SECRET_KEY=replace-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.6-flash
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
FRONTEND_URL=http://localhost:8080
# Optional, especially for Docker:
DATABASE_PATH=/app/data/db.sqlite3
```

Gemini and Stripe keys are optional for camera practice and local evaluation.
Never commit `.env`.

Create an administrator explicitly (the seed command never creates a default
password):

```bash
python manage.py createsuperuser
```

Admin is available at <http://localhost:8080/admin/>.

## Tracking and evaluation

`tracker.js` runs MediaPipe Hands continuously and keeps a rolling 2.6-second
landmark sequence. Face Mesh runs only for lessons marked `requires_face`, which
reduces unnecessary camera processing.

The tracker keeps the last complete attempt after the hands leave the frame.
This is important for two-hand signs: the learner does not need to hold the sign
while reaching for the mouse. The lesson displays **Sign captured** before the
check button becomes available.

Reference data can be either:

- MediaPipe image coordinates in the `0..1` range, or
- wrist-centered normalized coordinates produced by the seed/import pipeline.

The help renderer computes the reference bounding box and fits it into the
camera guide, so negative or wrist-centered values no longer draw off-screen.
Help only affects rendering; evaluation always uses the unmodified landmark
sequence.

The backend centers each hand at the wrist, scales by palm size, resamples the
sequence, and compares corresponding landmarks. For marked lessons, facial
metrics contribute 20% of the final score.

The evaluator intentionally allows normal differences in hand anatomy, camera
angle, signing speed, and dominant hand. A score of 60% completes an attempt;
feedback is limited to the two clearest corrections.

ASL non-manual markers carry grammatical and emotional information, but they
are not universally required for every word, number, or alphabet letter.
Configure them per lesson through:

- `requires_face`
- `required_hands` (`1` or `2`)
- `reference_face_metrics`
- `guidance`

## Importing lesson videos

Place videos in `raw_videos/`, then run:

```bash
python manage.py import_raw_videos --limit 150
```

Other available commands include:

```bash
python manage.py video_to_landmarks path/to/video.mp4 "Lesson name"
python manage.py import_video_folder path/to/folder
```

Imported videos must have a clearly visible hand. Review automatically extracted
landmarks and lesson names before publishing them.

## Main API

All endpoints are under `/api/v1/`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health/` | Service health |
| POST | `/auth/register/` | Registration |
| POST | `/auth/login/` | Login |
| GET | `/lessons/` | Lesson list |
| GET | `/lessons/<id>/` | Lesson, guide, face flags, reference landmarks |
| POST | `/practice/evaluate/` | Evaluate hand and optional face metrics |
| POST | `/translate/` | Translate a recorded sequence |
| GET | `/me/progress/` | User progress |
| GET/PATCH | `/me/` | Profile |
| GET/POST | `/friends/...` | Friends and requests |
| POST | `/billing/checkout/` | Stripe Checkout session |

Authenticated requests accept:

```text
Authorization: Bearer <token>
```

## Tests

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

Before pushing:

```bash
git status --short
git diff --check
python manage.py test
```

## Production notes

- Set `DEBUG=False`, a strong `SECRET_KEY`, and restrictive `ALLOWED_HOSTS`.
- Serve the site over HTTPS; browsers block camera access on insecure remote
  origins.
- Pin or self-host the MediaPipe browser assets if offline operation or strict
  supply-chain control is required.
- Replace SQLite for concurrent production workloads.
- Configure Stripe webhooks and a real privacy policy before accepting payments.
- Do not treat the current landmark-distance evaluator as a certified linguistic
  assessment. Validate lesson references and non-manual marker thresholds with
  qualified ASL users or instructors.
