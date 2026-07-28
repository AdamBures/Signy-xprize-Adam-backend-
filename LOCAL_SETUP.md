# Local development setup

This guide starts the current HandSign application locally. Django serves both
the REST API and the frontend SPA, so a separate frontend development server is
not required.

## Prerequisites

- Python 3.11 or newer
- Git
- A modern Chromium, Chrome, Edge, or Firefox browser
- A webcam for real hand-tracking checks
- Optional: Node.js for JavaScript syntax checks and browser automation

## Clone

Your fork:

```bash
git clone https://github.com/n1xone/Signy-xprize-Adam-backend-.git
cd Signy-xprize-Adam-backend-
```

Upstream repository:

```bash
git remote add upstream https://github.com/AdamBures/Signy-xprize-Adam-backend-.git
git fetch upstream
```

Check the branch and local changes before integrating upstream work:

```bash
git status
git branch --show-current
git log --oneline --decorate -10
```

Do not overwrite a dirty working tree. Commit or stash intentional work first.

## Virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuration

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The minimal development configuration needs no external keys. Keep:

```env
DEBUG=True
ALLOWED_HOSTS=*
GEMINI_FEEDBACK_ENABLED=false
```

To enable free translation, set `GEMINI_API_KEY`. The translator tries
`GEMINI_MODEL` first and then each model in `GEMINI_MODELS`. A failed external
model produces a friendly UI error and does not affect lesson progress.

To enable generated coaching advice, additionally set:

```env
GEMINI_FEEDBACK_ENABLED=true
```

Deterministic coaching is preferred for ordinary development and automated
tests because it is fast and does not consume API quota.

## Database and lesson data

```bash
python manage.py migrate
python manage.py seed_lessons
```

`seed_lessons` is idempotent and currently creates or updates the built-in ASL
catalog. It does not create an administrator or a default password.

Create an administrator explicitly if needed:

```bash
python manage.py createsuperuser
```

To keep a test database outside the repository:

```bash
DATABASE_PATH=/tmp/handsign.sqlite3 python manage.py migrate
DATABASE_PATH=/tmp/handsign.sqlite3 python manage.py seed_lessons
DATABASE_PATH=/tmp/handsign.sqlite3 python manage.py runserver 8080
```

On Windows, set `DATABASE_PATH` in `.env` instead.

## Start

```bash
python manage.py runserver 8080
```

Open:

- Application: <http://127.0.0.1:8080/>
- Health check: <http://127.0.0.1:8080/api/v1/health/>
- Admin: <http://127.0.0.1:8080/admin/>

Use `127.0.0.1`, `localhost`, or HTTPS. Browsers normally block camera access
on insecure remote origins.

## First manual check

1. Register a user rather than relying only on guest mode.
2. Open Lessons and start a one-hand word.
3. Allow camera access, keep the full hand visible, and complete an attempt.
4. Confirm the score appears in Profile and survives a refresh.
5. Repeat with a two-hand word and keep both hands visible until capture.
6. Confirm Next sign unlocks above 15%.
7. Improve the personal best and confirm `+60 XP · +10 coins`.
8. Repeat with an equal/lower score and confirm no additional reward.
9. Switch RU/EN/CS and verify the guide badge: RU uses RU; EN/CS use EN.
10. Open both profile dropdowns multiple times and click outside to confirm
    their arrows and focus state reset.

## Video guides

Use these fields on a `Word`:

```text
video_url_ru  Russian UI
video_url_en  English and Czech UI
video_url     legacy English fallback
```

For local files, place videos under `raw_videos/` and use a URL such as:

```text
/raw_videos/help-en.mp4
```

After changing the model, create and apply a migration. Do not hardcode video
selection logic in the UI; `guideVideoForLesson()` already implements the
language rule.

Several import/conversion commands exist under
`lessons/management/commands/`. Inspect a command’s `--help` before using it:

```bash
python manage.py import_raw_videos --help
python manage.py import_video_folder --help
python manage.py video_to_landmarks --help
```

These commands may depend on local datasets and can modify many database rows.
Use a disposable database first.

## Stripe development

Set test credentials in `.env`, then forward Stripe events:

```bash
stripe listen --forward-to localhost:8080/api/v1/billing/stripe-webhook/
```

Copy the webhook secret printed by Stripe CLI into
`STRIPE_WEBHOOK_SECRET`, restart Django, and use Stripe test cards only.

## Troubleshooting

### Camera does not start

- Use localhost/127.0.0.1 or HTTPS.
- Allow camera permission in browser settings.
- Close other applications using the camera.
- Reload after changing permission.
- Check the browser console for MediaPipe loading errors.

### Two-hand sign stays unavailable

- Keep both hands completely in the guide.
- Avoid one hand covering the other.
- Hold the final pose; the UI waits before automatic evaluation.
- Confirm the word has `required_hands=2` and 42-point reference frames.

### Gemini translation fails

- Confirm `GEMINI_API_KEY` is loaded into the Django process.
- Confirm at least one configured model is available for that API project.
- Inspect the Django log; models are tried in order.
- A `502 ai_unavailable` response is expected when every model fails.

### Changes do not appear

The app uses versioned root assets. Increment the query version in `index.html`
when changing `app.js` or `styles.css`, and update the `i18n.js` import version
in `app.js` when changing translations. Then hard-refresh the browser.

### Database should be reset

Prefer a new database path instead of deleting an existing database:

```bash
DATABASE_PATH=/tmp/handsign-clean.sqlite3 python manage.py migrate
DATABASE_PATH=/tmp/handsign-clean.sqlite3 python manage.py seed_lessons
```
