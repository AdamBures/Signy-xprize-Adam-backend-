# Jak u sebe spustit HandSign přes Docker (Verze 1.1)

Pokud u sebe nemáš složku aw_videos\ a chceš celou aplikaci rozběhnout přes Docker (což je mnohem snazší na údržbu), použij tento postup:

---

### 1. Stažení kódu
Naklonuj si repozitář s projektem a přepni se do správné verze:
\\ash
git clone <URL-K-VAŠEMU-REPOZITÁŘI>
cd Signy-xprize-Adam-backend-
git checkout Version-1.1
\
### 2. Vytvoření konfiguračního souboru (.env)
Aby ti uvnitř Dockeru fungovala komunikace s umělou inteligencí a platbami, vytvoř přímo ve složce projektu (vedle souboru \Dockerfile\) textový soubor \.env\. 

Vlož do něj tyto řádky a doplň klíče:
\\env
GEMINI_API_KEY=tvuj_gemini_klic
STRIPE_SECRET_KEY=tvuj_stripe_secret_klic
STRIPE_WEBHOOK_SECRET=tvuj_stripe_webhook_klic
\
### 3. Vytvoření Docker obrazu (Build)
Ujisti se, že máš zapnutý Docker Desktop (nebo službu Docker). V terminálu ve složce s projektem spusť tento příkaz, kterým aplikaci sestavíš:
\\ash
docker build -t handsign-app .
\*(Tohle chvilku potrvá, protože se stáhne Python a nainstalují se všechny závislosti.)*

### 4. Spuštění kontejneru 🚀
Nyní aplikaci spusť a propoď ji s portem 8080:
\\ash
docker run -d --name handsign-container -p 8080:8080 --env-file .env handsign-app
\
**A je hotovo!** Kontejner sám na pozadí připraví databázi (\migrate\) a automaticky ji naplní testovacími lekcemi (\seed_lessons\).

Nyní si jen otevři prohlížeč a běž na adresu: **http://localhost:8080/**

---

### Poznámky na okraj:
* **Absence aw_videos\:** Nevadí, že nemáš složku aw_videos\. Aplikace poběží i bez ní, akorát ve výukovém okně neuvidíš originální ukázková videa u lekcí (může tam být šedý obdélník). Vlastní rozpoznávání na kameře ti ale fungovat bude normálně!
* Jakmile bys videa získal, můžeš je do běžícího Dockeru nahrát takto:
  \\ash
  docker cp raw_videos handsign-container:/app/raw_videos
  docker exec handsign-container python manage.py import_raw_videos --limit 150
  \* Pro vypnutí aplikace stačí zadat: \docker stop handsign-container