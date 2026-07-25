# AI Tutor Znakové řeči - Backend API & Frontend SPA

Robustní Python/Django backend a interaktivní Vanilla JS SPA frontend navržený pro výuku americké znakové řeči (ASL) a překlad znaků v reálném čase. Aplikace je optimalizována pro výuku rodičů dětí s opožděným vývojem řeči nebo autismem.

---

## Hlavní Funkce (Core Features)

### 🧠 1. MediaPipe Evaluace a Gemini AI Zpětná Vazba
- **Landmark Normalization**: Vyhodnocovací algoritmus normalizuje 21 3D souřadnic ruky ( wrist-centered centrování, škálování na velikost dlaně) a provádí časové resamplování (lineární interpolace) pro nezávislost na vzdálenosti od kamery a rychlosti pohybu.
- **Gemini AI Diagnostics**: V případě chybně provedeného znaku analyzuje přesné odchylky jednotlivých prstů a dotazuje Google Gemini API, které uživateli vrací empatické, konkrétní rady v češtině.

### 📺 2. Lekce s Ukázkovým Videem (WLASL) & Ghost Overlay
- **Local Serving**: Systém lokálně streamuje původní mp4 videa ze složky `raw_videos/` přímo do prohlížeče.
- **Auto-Open Tutorial**: Při vstupu do lekce se uživateli automaticky otevře přehrávač videa ve smyčce (loop).
- **Watch Example**: Během samotného cvičení s kamerou lze video kdykoliv znovu spustit tlačítkem *"Watch Video Example"*.
- **Digital Ghost Overlay**: Přímo přes obraz webkamery uživatele se promítá poloprůhledný, animovaný skelet ruky ("duch") správného provedení znaku. Uživatel tak získává okamžitou motorickou korekci zobrazenou v reálném čase.

### 👥 3. Sociální Systém (Přátelé, Streaks & Doporučení)
- **Gamified Streaks**: Výpočet denních sérií (streak) na základě dat o splněných cvičeních.
- **Žebříček (Streaks Scoreboard)**: Seznam přátel je automaticky seřazen podle jejich denních sérií pro posílení motivace.
- **Suggestions (Doporučení)**: Systém doporučuje ostatní uživatele aplikace, které si lze přidat jedním kliknutím.
- **Requests & Approvals**: Podpora schvalování a odmítání příchozích žádostí o přátelství v reálném čase.

### 💳 4. Stripe Paywall & Předplatné
- **Stripe Checkout**: Integrované platební brány pro nákup plného přístupu.
- **Stripe Webhooks**: Bezpečné automatické odemykání prémiových lekcí po úspěšném zpracování platby.

---

## 💼 Business Model & Monetizace

HandSign je navržen jako vysoce životaschopný produkt se zaměřením na specifický a bonitní trh:
- **Cílová skupina**: Rodiče dětí s komunikačními bariérami (autismus, opožděný vývoj řeči, sluchová postižení). Tito rodiče mají extrémní motivaci naučit se znakovou řeč rychle, aby mohli se svými dětmi komunikovat doma.
- **Monetizační model**: Jednorázový poplatek nebo předplatné ve výši **$10 USD (cca 230 Kč)** za neomezený přístup pro celou rodinu ("Family Unlimited Access"). Zpracování plateb probíhá plně automatizovaně přes zabezpečené rozhraní Stripe.
- **Důkazy o tržbách**: Platební toky jsou integrované do Stripe dashboardu a simulovatelné v testovacím režimu pro doložení reálných konverzí pro účely hodnocení poroty.

---

## 🚀 Budoucí rozvoj & Vize (Future Vision)

Pro účely soutěže a budoucího rozvoje platformy jsou navržena tato technická a obsahová rozšíření:
1. **Sledování obličeje a postavení (NMMs - Non-Manual Markers)**: Znakový jazyk není pouze o rukou, ale velkou roli hraje mimika a pohyb ramen. Budoucí verze rozšíří MediaPipe model o detekci mimických bodů a náklonu těla, přičemž Gemini AI bude hodnotit celkovou přirozenost projevu.
2. **Adaptivní výuka (Adaptive Learning)**: Pokud systém detekuje, že uživatel opakovaně chybuje v konkrétní oblasti (např. nedovřený palec u písmene D), algoritmus mu automaticky do výukového plánu zařadí izolační cvičení zaměřená přesně na tuto motorickou korekci.
3. **Situační scénáře**: Přechod od izolovaných slovíček k tématickým konverzačním celkům ("Hraní v parku", "Čas na oběd"), což umožní rodičům aplikovat znaky v reálném životě okamžitě.
4. **Kulturní kontext neslyšících**: Integrace rad ohledně kultury neslyšících (např. jak správně navázat oční kontakt) přímo do doporučení od Gemini AI, aby se uživatelé učili jazyk v celkovém sociálním kontextu.

---

## Přehled API Endpoints (`/api/v1/`)

Všechny API požadavky a odpovědi komunikují v JSON formátu a vyžadují autorizační hlavičku pro zabezpečené sekce:  
`Authorization: Bearer <auth_token>`

### 🔑 Autentizace
- `POST /api/v1/auth/register/` – Registrace nového uživatele.
- `POST /api/v1/auth/login/` – Přihlášení uživatele.

### 📚 Lekce a Pokrok
- `GET /api/v1/lessons/` – Získání seznamu dostupných lekcí (včetně odkazů na ukázková videa).
- `GET /api/v1/me/progress/` – Získání statistik uživatele (denní série, přesnost, aktivní dny v týdnu).
- `GET /api/v1/me/` – Získání a aktualizace detailů profilu (včetně nahrání vlastního avataru).

### 🤖 Vyhodnocení a Překlad
- `POST /api/v1/practice/evaluate/` – Odeslání MediaPipe landmarků pro vyhodnocení konkrétního slova.
- `POST /api/v1/translate/` – Odeslání video klipu a landmarků pro překlad v reálném čase.

### 👥 Sociální Funkce (Přátelé)
- `GET /api/v1/friends/` – Vrací seznam přátel, příchozí žádosti a doporučené uživatele.
- `POST /api/v1/friends/request/` – Odeslání žádosti o přátelství (přijímá `username` nebo `to_user_id`).
- `POST /api/v1/friends/respond/` – Schválení (`accept`) nebo zamítnutí (`reject`) žádosti (přijímá `friendship_id`).

### 💳 Platby
- `POST /api/v1/billing/checkout/` – Vytvoření Stripe Checkout relace.

---

## Lokální Spuštění (Docker Setup)

Nejsnazší cesta pro lokální spuštění celé aplikace:

1. **Vytvoření konfiguračního souboru `.env`:**
   Vytvořte v kořeni soubor `.env` podle předlohy `.env.example` a vyplňte klíče `GEMINI_API_KEY` a `STRIPE_SECRET_KEY`.

2. **Sestavení Docker obrazu:**
   ```bash
   docker build -t signy-backend .
   ```

3. **Spuštění kontejneru:**
   ```bash
   docker run -d --name signy-app -p 8080:8080 signy-backend
   ```
   Aplikace bude běžet na adrese `http://localhost:8080/`.

4. **Nahrání ukázkových videí do kontejneru:**
   ```bash
   docker cp raw_videos signy-app:/app/raw_videos
   ```

5. **Import WLASL databáze gest (limit 150 videí):**
   ```bash
   docker exec signy-app python manage.py import_raw_videos --limit 150
   ```

---

## Spuštění mimo Docker (Vývojářský Režim)

1. **Aktivace virtuálního prostředí:**
   ```bash
   .\venv\Scripts\activate
   ```
2. **Instalace závislostí:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Spuštění migrací a naplnění dat:**
   ```bash
   python manage.py migrate
   python manage.py seed_lessons
   ```
4. **Spuštění vývojového serveru:**
   ```bash
   python manage.py runserver 8080
   ```
