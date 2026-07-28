# Project handoff

This file gives the next developer or AI agent enough context to continue
without reconstructing recent decisions.

## Baseline

- Working branch used during the bug-fix pass: `bughunt/adam-latest`.
- Upstream: `AdamBures/Signy-xprize-Adam-backend-`.
- Fork: `n1xone/Signy-xprize-Adam-backend-`.
- The working tree may contain intentional uncommitted changes. Always run
  `git status --short` and inspect the diff before editing, rebasing, or merging.
- Do not reset or overwrite local changes.

## Recently stabilized areas

- One- and two-hand capture, including grace time before automatic evaluation.
- Two-hand landmark normalization, hand-order permutation, and mirroring.
- Progress persistence and refresh behavior.
- Personal-best-only rewards: 60 XP and 10 coins.
- Streak activity separated from reward amount.
- Next-word navigation above 15%; mastery at 60%.
- Multi-model Gemini translation fallback and friendly outage messages.
- Progress-safe optional Gemini coaching.
- Lesson/recommendation population and course sections.
- Profile custom dropdowns with reliable arrow animation and keyboard behavior.
- Skin-tone propagation across supported hand emoji.
- Russian/English localized sign-guide selection and missing-video placeholders.
- Russian/Czech navigation and profile translation cleanup.

## Database changes

Apply all migrations:

```bash
python manage.py migrate
```

The latest lesson migration adds:

```text
Word.video_url_en
Word.video_url_ru
```

Do not remove legacy `video_url`; it remains the English fallback and supports
existing content.

## Content still required from the project team

The code supports localized guide videos, but the full video asset library is
not part of this repository. Coordinate:

- Russian sign-guide videos for Russian UI.
- English sign-guide videos for English and Czech UI.
- Licensing/attribution for all datasets.
- Reference landmark sequences recorded under consistent conditions.

Avoid inventing URLs or silently assigning an English video to the Russian
field.

## Known boundaries

- Recognition quality is bounded by reference landmark quality. The evaluator
  cannot infer a semantically correct sign from weak or synthetic references.
- Facial non-manual markers have schema/support hooks but need a broader
  validated dataset for production-quality scoring.
- Gemini is an external dependency; model names, quotas, and availability must
  be verified for the deployment account.
- The included Docker setup is a single-instance SQLite baseline.
- Browser camera automation validates capture mechanics with synthetic streams;
  final accuracy still requires real-user testing.
- Some product copy and business decisions (premium pricing, coin-store values,
  curriculum order) should be confirmed by the product owner.

## Before starting new work

```bash
git status --short
git diff --check
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

Read:

1. [README.md](README.md)
2. [ARCHITECTURE.md](ARCHITECTURE.md)
3. [TESTING.md](TESTING.md)
4. The files directly responsible for the requested feature

## Before handing off again

- Run the full checklist in [TESTING.md](TESTING.md).
- Record the branch and exact commit.
- List migrations and environment-variable changes.
- State which browser/camera journeys were manually tested.
- State whether Gemini, Stripe, and video assets were tested with real external
  accounts.
- Keep documentation consistent with actual thresholds and reward amounts.
- Never include `.env`, tokens, private video assets, or user databases.
