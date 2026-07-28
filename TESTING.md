# Testing and release checklist

Run this checklist before handing the project to another developer, merging
upstream work, or deploying.

## Automated checks

Activate the virtual environment, then run:

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
node --check app.js
node --check api.js
node --check i18n.js
node --check tracker.js
git diff --check
```

Current baseline: 21 Django tests.

Expected warning logs in tests may include simulated Gemini model failures.
Those tests verify fallback behavior and are not failures when the suite ends
with `OK`.

## API smoke test

```bash
python manage.py migrate
python manage.py seed_lessons
python manage.py runserver 8080
```

In another terminal:

```bash
curl http://127.0.0.1:8080/api/v1/health/
curl http://127.0.0.1:8080/api/v1/lessons/
```

Verify register, login, profile, and progress using a disposable account.

## Browser matrix

At minimum test current Chromium and one other modern browser.

- Desktop width around 1440 px.
- Narrow/mobile width around 390 px.
- Light and dark themes.
- English, Russian, and Czech.
- Keyboard-only navigation.
- A real webcam on localhost or HTTPS.

## Critical user journeys

### Authentication and persistence

- Register and log in.
- Refresh on Dashboard, Lessons, Words, Practice, Progress, and Profile.
- Confirm the selected practice word survives refresh.
- Confirm logout clears protected state.

### One-hand practice

- Start camera and show a full gesture.
- Confirm the progress counter advances.
- Confirm Check becomes available after capture.
- Confirm a score and friendly feedback appear.
- Confirm score persists in Profile and lesson cards.

### Two-hand practice

- Select a word with `required_hands=2`.
- Confirm the guide says two hands.
- Keep both hands visible through the capture window.
- Lower hands only after the captured confirmation.
- Confirm evaluation does not collapse to zero because of hand order.
- Confirm automatic evaluation waits long enough to hold the final pose.

### Rewards and streak

- Establish a personal best.
- Improve it and confirm exactly 60 XP and 10 coins are granted.
- Submit an equal/lower result and confirm no additional reward.
- Refresh and confirm totals persist.
- Confirm practice creates streak activity without duplicate reward.

### Lessons and recommendations

- Confirm all seeded words appear across multiple sections.
- Confirm filters visibly change results.
- Confirm Recommended is populated from incomplete/easier-next content.
- Confirm score above 15% exposes Next sign.
- Confirm completed/mastered status starts at 60%.

### Translation

- Record a phrase with a valid Gemini key.
- Confirm Copy and Read aloud enable only for successful text.
- Test a deliberately invalid key or unavailable model.
- Confirm the learner sees a friendly recovery message, not an exception/model
  dump.
- Confirm configured fallback models are attempted in order in server logs.

### Profile UI

- Open and close each dropdown repeatedly.
- Click outside and confirm menu closes, active border clears, and arrow returns.
- Use Arrow Up/Down, Home, End, Enter, and Escape.
- Change skin tone, save, and confirm all supported hand emoji update.
- Refresh and confirm the preference persists.

### Localization and guide videos

- RU displays distinct `Уроки` and `Слова`, plus `🤟 RU`.
- CS displays distinct `Lekce` and `Slova`, plus `🤟 EN`.
- EN displays `Lessons` and `Words`, plus `🤟 EN`.
- RU opens `video_url_ru`.
- EN/CS open `video_url_en` or the legacy `video_url`.
- Missing video opens the intentional “coming soon” state.

## External services

These cannot be fully guaranteed by the local unit suite:

- Current Gemini model availability and quota.
- Stripe Checkout redirect and webhook delivery.
- SMTP delivery.
- Camera/browser/OS permission behavior.
- Accuracy across lighting, skin tones, camera quality, and signing styles.

Test external integrations in their sandbox/test modes before release.

## Regression policy

When fixing a bug:

1. Reproduce it with a focused automated test where practical.
2. Fix the smallest responsible layer.
3. Run the focused test.
4. Run the full suite and syntax checks.
5. Exercise the affected user journey in a browser.
6. Update documentation if behavior, configuration, or thresholds changed.
