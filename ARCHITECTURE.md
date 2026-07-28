# Architecture and extension guide

This document is the technical map for developers and AI coding agents working
on HandSign.

## Request flow

```text
Browser camera
  -> tracker.js / MediaPipe Hands
  -> captured landmark frames
  -> app.js practice state
  -> api.js
  -> POST /api/v1/practice/evaluate/
  -> evaluation/evaluator.py
  -> score + deterministic/optional Gemini advice
  -> UserProgress + XPEntry
  -> refreshed profile, lesson cards, streak, XP, and coins
```

Free translation is a separate flow:

```text
MediaRecorder clip + sampled landmarks
  -> POST /api/v1/translate/
  -> evaluation/gemini_client.py
  -> configured Gemini models in order
  -> translated text or a typed friendly error
```

## Frontend ownership

### `app.js`

Owns SPA route rendering, session state, lesson grouping, profile UI, camera
workflow, capture readiness, evaluation requests, progress hydration,
translation recording, localization hooks, and user-facing error states.

Important invariants:

- `state.lesson` is the current word and is persisted so refresh does not jump
  to a different word.
- Two-hand capture must not be replaced by a one-hand frame.
- Captured frames remain available while the learner lowers their hands.
- Next-word navigation unlocks only after a score above 15%.
- A lesson is mastered at 60%, matching backend `success`.
- Profile selects use the custom select controller. Do not reintroduce native
  open/focus assumptions; browsers do not expose native dropdown open state.
- After changing a skin tone, lesson emoji are recomputed from `EMOJI_MAP`.

### `tracker.js`

Wraps MediaPipe Hands, video readiness, landmark delivery, and tracking status.
It can detect up to two hands. Keep provider initialization idempotent: route
changes and camera restarts must not create parallel tracker loops.

### `api.js`

Centralizes API base URL, Bearer authentication, timeouts, multipart uploads,
JSON errors, and demo fallback behavior. New API calls should be added here
rather than using ad-hoc `fetch()` in UI components.

### `i18n.js`

Contains English fallbacks and Russian/Czech dictionaries plus lesson-specific
tips, positions, and movements. Text rendered before `I18n.apply()` must use
stable English source keys. When adding navigation entries, explicitly provide
distinct translations; do not translate Lessons and Words to the same label.

### Asset cache versions

`index.html` loads versioned `styles.css`, `app.js`, `api.js`, and `tracker.js`.
`app.js` imports a versioned `i18n.js`. Increment the relevant version after
changes so testers do not run stale browser assets.

## Backend ownership

### `lessons`

- `Category`: ordered content grouping.
- `Word`: lesson content, guide URLs, hand/face requirements, reference
  landmarks, guidance, premium status, and optional prerequisite.
- `UserProgress`: unique personal best/completion pair per user and word.
- `seed_lessons`: canonical built-in catalog and reference examples.

A reference frame contains 21 points for one hand or 42 points for two hands.
Keep `required_hands` consistent with the reference shape.

### `evaluation`

`evaluator.py` normalizes landmarks and compares temporal sequences. Two-hand
evaluation accounts for hand ordering and mirroring so MediaPipe’s changing
left/right detection does not force a zero score.

`EvaluateSignView`:

1. Resolves a word by ID, name, or slug.
2. Rejects incomplete captures with HTTP 422.
3. Calculates the deterministic score.
4. Saves the personal best and completion state.
5. Awards 60 XP and 10 coins only for a strict personal-best improvement.
6. Records activity for streaks.
7. Requests optional Gemini coaching after persistence.
8. Falls back to localized deterministic advice if coaching fails.

Do not move progress persistence after the external AI call. External outages
must never lose a learner’s result.

`gemini_client.py` deduplicates the primary and fallback model list and returns
the first non-empty response. Translation maps total model failure to a typed
`ai_unavailable` response.

### `users`

The custom user stores subscription state, avatar, level, daily goal, onboarding
state, XP, coins, temporary premium expiry, country, pronouns, and skin tone.

`XPEntry` is also the source of streak activity. Zero-amount entries are
intentional: they record practice without incorrectly granting XP.

## Progress and unlocking rules

| Rule | Current value |
| --- | --- |
| Next word becomes available | score > 15% |
| Word counts as completed/mastered | score >= 60% |
| Reward condition | score strictly exceeds saved personal best |
| Reward | 60 XP and 10 coins |
| Repeat/equal/lower attempt | 0 XP and 0 coins |
| Streak activity | any authenticated evaluated attempt |

Keep frontend and backend constants aligned when changing these rules. Add
tests before changing reward semantics because duplicate rewards are easy to
introduce through retries.

## Localized sign guides

Guide selection is intentionally based on interface language:

| UI language | Guide field |
| --- | --- |
| Russian | `video_url_ru` |
| English | `video_url_en`, then `video_url` |
| Czech | `video_url_en`, then `video_url` |

The preference toolbar displays `🤟 RU` or `🤟 EN`. The guide button remains
visible when the asset is missing and opens an explanatory placeholder.

When adding another language, decide whether it uses a new sign language or an
existing guide before changing the schema. Spoken UI language and sign language
are not automatically equivalent.

## Error contract

Expected operational failures should return JSON with a stable `code` and a
human-readable `error`. The frontend maps transport, camera, incomplete
capture, unclear sign, and AI outage errors to calm recovery instructions.

Avoid displaying model names, stack traces, HTTP internals, or raw exception
messages to learners. Log technical context on the server.

## Safe extension patterns

### Add a word

1. Add/update it in `seed_lessons.py` or through an administrative content
   workflow.
2. Set `required_hands` and `requires_face`.
3. Add guidance text.
4. Provide a correctly shaped reference sequence.
5. Add RU/EN guide URLs if available.
6. Add emoji and translations if required.
7. Test direct practice, refresh persistence, next navigation, and progress.

### Change evaluation

1. Add evaluator unit tests for one hand, two hands, mirrored input, hand-order
   swaps, incomplete capture, and temporal speed differences.
2. Keep normalized values independent of camera distance.
3. Do not silently accept malformed frame sizes.
4. Run real browser capture checks after unit tests.

### Add a Gemini model

Prefer `.env` configuration. Do not hardcode a single model inside a view.
Preserve timeouts, fallback order, and typed outage responses.

### Add a profile preference

Add the model field and migration, serializer/view support, frontend state,
profile control, localization, persistence test, and refresh test. For dropdown
preferences use the existing custom-select component.
