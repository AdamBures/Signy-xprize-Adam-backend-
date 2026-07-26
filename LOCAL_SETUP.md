# Jak u sebe lokálně spustit HandSign (Verze 1.1)

Tady je rychlý návod, jak u sebe lokálně rozběhnout HandSign aplikaci. Je to postavené na Pythonu a Djangu, takže stačí projekt jen naklonovat, nahodit databázi a spustit.

---

### 1. Stažení kódu
Otevři si terminál (na Windows např. PowerShell nebo příkazový řádek) a stáhni si projekt přes Git:
\\ash
git clone <URL-K-VAŠEMU-REPOZITÁŘI>
cd Signy-xprize-Adam-backend-
\Následně se přepni do správné verze (pokud ještě nejsi):
\\ash
git checkout Version-1.1
\
### 2. Nastavení přístupových klíčů (Prostředí)
Aby fungovala AI a platby, aplikace potřebuje tajné klíče. V hlavní složce projektu (tam kde je soubor manage.py) vytvoř textový soubor s názvem .env.

Do tohoto .env souboru vlož tyto řádky a doplň klíče (které dostaneš bokem):
\\env
GEMINI_API_KEY=tvuj_gemini_klic
STRIPE_SECRET_KEY=tvuj_stripe_secret_klic
STRIPE_WEBHOOK_SECRET=tvuj_stripe_webhook_klic
\
### 3. Vytvoření virtuálního prostředí a instalace
Nejlepší je oddělit si Python knihovny, aby se ti to nepletlo s jinými projekty. Ve stejné složce spusť:
\\ash
python -m venv venv
\Pak virtuální prostředí aktivuj (na Windows):
\\ash
.\venv\Scripts\activate
\*(Pokud jsi na Macu nebo Linuxu, použij: source venv/bin/activate)*

Jakmile jsi uvnitř (v terminálu uvidíš na začátku řádku nápis \(venv)\), nainstaluj vše potřebné:
\\ash
pip install -r requirements.txt
\
### 4. Příprava databáze a nahrání lekcí
Teď vytvoříme lokální databázi a naplníme ji výukovou strukturou aplikace. Spusť postupně tyto dva příkazy:
\\ash
python manage.py migrate
python manage.py seed_lessons
\
**Máš videa? (Volitelné):**
Pokud máš k dispozici složku raw_videos, vlož ji přímo do hlavní složky projektu. Poté můžeš videa naimportovat do databáze (zpracuje se jich např. prvních 150):
\\ash
python manage.py import_raw_videos --limit 150
\
### 5. Spuštění serveru! 🚀
Všechno je připraveno, stačí to nahodit:
\\ash
python manage.py runserver 8080
\
Nyní si jen otevři prohlížeč a běž na adresu: **http://localhost:8080/**
Tím se ti otevře celá frontendová aplikace a můžeš ji začít používat!

---

*(Poznámka k testování plateb: Pokud chceš zkoušet Stripe webhooky lokálně, budeš si muset zapnout Stripe CLI přes \stripe listen --forward-to localhost:8080/api/v1/billing/stripe-webhook/\, jinak ti ale vše ostatní poběží samo.)*
