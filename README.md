# AI Tutor Znakové řeči - Backend API

Robustní backend v Python/Django navržený pro aplikaci AI Tutor Znakové řeči (ASL / ČZJ) pro výuku rodičů dětí s opožděným vývojem řeči nebo autismem.

## Hlavní funkce (Features)
- 🧠 **MediaPipe Vector Evaluation**: Matematické porovnání uživatelských souřadnic ruky (21 landmark bodů x, y, z) s referenčním vektorem. Normalizace škály, offsetu zápěstí a časové resamplování gesta.
- 🤖 **Gemini API Integration**: Automatické generování přirozených, povzbudivých rad v češtině pomocí Google Gemini API na základě přesné diagnostiky odchylek prstů.
- 💳 **Stripe Paywall Integration**: Podpora přístupu k lekcím pro bezplatné a prémiové uživatele s integrací Stripe Checkout a Webhooků.
- 📚 **Lekce a Vektory**: Databáze předpřipravených slovíček a kategorií se zapsanými referenčními vektory gest.
- 🐳 **Docker & Google Cloud Run ready**: Kompletní kontejnerizace s podporou Gunicorn a proměnných prostředí pro snadné nasazení do Google Cloud.

---

## Přehled API Endpoints (pro Frontend)

Všechny API endpointy přijímají a vracejí JSON.

### 1. Uživatelé a Autentizace (`/api/users/`)
- `POST /api/users/register/` - Registrace nového uživatele (`username`, `email`, `password`, `first_name`, `last_name`). Vrací auth `token`.
- `POST /api/users/login/` - Přihlášení uživatele (`username` / `email`, `password`). Vrací auth `token`.
- `GET /api/users/profile/` - Získání profilu přihlášeného uživatele (Header: `Authorization: Token <token>`).
- `POST /api/users/create-checkout-session/` - Vytvoří Stripe checkout relaci pro nákup plného přístupu.
- `POST /api/users/stripe-webhook/` - Stripe webhook endpoint pro příchozí platby.

### 2. Lekce a Slovíčka (`/api/lessons/`)
- `GET /api/lessons/categories/` - Seznam všech kategorií (Základní slova, Rodina, Jídlo & Pití, Abeceda).
- `GET /api/lessons/words/` - Seznam slovíček (podporuje filtr `?category=<id>`).
- `GET /api/lessons/words/<id>/` - Detail slovíčka včetně referenčních vektorů `reference_landmarks`.
- `GET /api/lessons/progress/` - Pokrok přihlášeného uživatele (skóre, dokončené lekce).

### 3. Vyhodnocování znaků z webkamery (`/api/evaluation/`)
- `POST /api/evaluation/evaluate/` - Odeslání nasnímaných landmarků z MediaPipe.

**Příklad požadavku (Request Body):**
```json
{
  "word_id": 1,
  "landmarks": [
    [
      {"x": 0.45, "y": 0.62, "z": -0.01},
      ... 21 landmarků ...
    ]
  ]
}
```

**Příklad odpovědi (Response Body):**
```json
{
  "word_id": 1,
  "word_name": "Mléko",
  "score": 85.5,
  "success": true,
  "feedback": "Skvělá práce! Znak pro 'Mléko' jsi provedl(a) správně. Pokračuj v dalším tréninku!",
  "issues": []
}
```

---

## Lokální Spuštění (Local Setup)

1. **Aktivace virtuálního prostředí:**
   ```bash
   .\venv\Scripts\activate
   ```

2. **Migrace databáze a naplnění dat:**
   ```bash
   python manage.py migrate
   python manage.py seed_lessons
   ```

3. **Spuštění serveru:**
   ```bash
   python manage.py runserver 8000
   ```
   Server poběží na `http://127.0.0.1:8000/`.

---

## Nasazení na Google Cloud Run (Production / Docker)

1. **Sestavení Docker obrazu:**
   ```bash
   gcloud builds submit --tag gcr.io/VASE_PROJECT_ID/signy-backend
   ```

2. **Nasazení na Cloud Run:**
   ```bash
   gcloud run deploy signy-backend \
     --image gcr.io/VASE_PROJECT_ID/signy-backend \
     --platform managed \
     --region europe-west1 \
     --allow-unauthenticated \
     --set-env-vars GEMINI_API_KEY=vaše_gemini_key,STRIPE_SECRET_KEY=vaše_stripe_key
   ```
