# Sign Language AI Tutor - Backend API & Frontend SPA

A robust Python/Django backend and an interactive Vanilla JS SPA frontend designed for teaching American Sign Language (ASL) and translating signs in real time. The application is specifically optimized to help parents of children with delayed speech development or autism.

---

## Core Features

### 🧠 1. MediaPipe Evaluation & Gemini AI Feedback
- **Landmark Normalization**: Our evaluation algorithm normalizes 21 3D hand coordinates (wrist-centered scaling to palm size) and runs temporal resampling via linear interpolation. This ensures the engine doesn't care how far you are from the camera or how fast you move.
- **Gemini AI Diagnostics**: If you mess up a sign, the system analyzes the exact deviations of your individual fingers and pings the Google Gemini API to give you empathetic, highly specific advice on how to fix it.

### 📺 2. Video Lessons (WLASL) & Ghost Overlay
- **Local Serving**: We stream the original mp4 WLASL videos directly from the `raw_videos/` folder straight to the browser.
- **Auto-Open Tutorial**: Whenever you jump into a lesson, a looping video tutorial automatically pops up to show you the ropes.
- **Watch Example**: While you're practicing on camera, you can always pull the video back up by hitting the *"Watch Video Example"* button.
- **Digital Ghost Overlay**: A semi-transparent, animated skeletal hand (a "ghost") demonstrating the correct execution is projected directly over your webcam feed. It's essentially real-time motor correction drawn right on your screen.

### 👥 3. Social System (Friends, Streaks & Suggestions)
- **Gamified Streaks**: Daily streaks are automatically tracked based on the exercises you complete.
- **Streaks Scoreboard**: Your friend list doubles as a leaderboard that auto-sorts everyone by their daily streaks to keep motivation high.
- **Suggestions**: The system suggests other users you might want to connect with, which you can add with a single click.
- **Requests & Approvals**: Full real-time support for sending, accepting, and declining friend requests.

### 💳 4. Stripe Paywall & Subscriptions
- **Stripe Checkout**: Fully integrated payment gateways for purchasing premium access.
- **Stripe Webhooks**: Secure, automated unlocking of premium lessons the exact moment your payment clears.

### ⚡ 5. Scalable Architecture (Infinite Scroll & Pagination)
- **IntersectionObserver Infinite Scroll**: The client SPA leverages modern IntersectionObservers to deliver a flawless infinite scrolling experience across the entire app (Lesson Library, Leaderboards, Friend Lists).
- **Backend Pagination**: The Django REST Framework (DRF) serves data in pages. The social panel uses an advanced asynchronous pagination strategy that independently paginates accepted friends (`friends_page`) and pending requests (`requests_page`) inside a single API call, entirely eliminating massive JSON payloads.

---

## 💼 Business Model & Monetization

HandSign is built as a highly viable product targeting a specific, high-intent market:
- **Target Audience**: Parents of children with communication barriers (autism, delayed speech development, hearing impairments). These parents are incredibly motivated to learn sign language fast so they can actually communicate with their kids at home.
- **Monetization Model**: A flat fee or subscription of **$10 USD** for "Family Unlimited Access". Payments are fully automated through a secure Stripe interface.
- **Proof of Revenue**: The payment flows are wired directly into a Stripe dashboard and can be simulated in test mode to prove real conversion mechanics for the jury's evaluation.

---

## 🚀 Future Vision

For the sake of the competition and the platform's future growth, here's what we're building next:
1. **Face and Body Tracking (NMMs - Non-Manual Markers)**: Sign language isn't just about hands; facial expressions and shoulder movements are massive. Future versions will expand the MediaPipe model to detect facial landmarks and body tilt, allowing Gemini AI to evaluate the overall naturalness of your delivery.
2. **Adaptive Learning**: If the system notices you're repeatedly making the same mistake (e.g., leaving your thumb open on the letter D), the algorithm will automatically inject isolation exercises targeting that exact motor correction into your learning plan.
3. **Situational Scenarios**: We're moving from isolated vocabulary to thematic conversational blocks ("Playing at the park", "Lunchtime"), letting parents apply signs in real-life situations immediately.
4. **Deaf Culture Context**: We plan to weave Deaf culture tips (like how to properly maintain eye contact) straight into Gemini AI's feedback so users learn the language in its proper social context.

---

## API Endpoints Overview (`/api/v1/`)

All API requests and responses talk in JSON and require an authorization header for secured sections:  
`Authorization: Bearer <auth_token>`

### 🔑 Authentication
- `POST /api/v1/auth/register/` – Register a new user.
- `POST /api/v1/auth/login/` – Log a user in.

### 📚 Lessons & Progress
- `GET /api/v1/lessons/` – Fetch available lessons (including links to example videos).
- `GET /api/v1/me/progress/` – Fetch user stats (daily streak, accuracy, active days this week).
- `GET /api/v1/me/` – Fetch and update profile details (including custom avatar uploads).

### 🤖 Evaluation & Translation
- `POST /api/v1/practice/evaluate/` – Submit MediaPipe landmarks to evaluate a specific word.
- `POST /api/v1/translate/` – Submit a video clip and landmarks for real-time translation.

### 👥 Social Features (Friends & Leaderboard)
- `GET /api/v1/friends/` – Returns friends, incoming requests, and suggested users. Supports `friends_page` and `requests_page` params for smooth infinite scrolling.
- `POST /api/v1/friends/request/` – Send a friend request (accepts `username` or `to_user_id`).
- `POST /api/v1/friends/respond/` – Approve (`accept`) or decline (`reject`) a request (accepts `friendship_id`).
- `GET /api/v1/users/leaderboard/` – Fetch the global or local player leaderboard sorted by XP, with standard `page` pagination support.

### 💳 Billing
- `POST /api/v1/billing/checkout/` – Create a Stripe Checkout session.
- `POST /api/v1/billing/stripe-webhook/` – Stripe webhook endpoint for processing async payment events (e.g., `checkout.session.completed`).

---

## Running Locally (Docker Setup)

The absolute easiest way to get the whole stack running locally:

1. **Create the `.env` config file:**
   Create a `.env` file in the root directory based on `.env.example` and drop in your `GEMINI_API_KEY`, `STRIPE_SECRET_KEY`, and `STRIPE_WEBHOOK_SECRET`.

2. **Build the Docker image:**
   ```bash
   docker build -t signy-backend .
   ```

3. **Spin up the container:**
   ```bash
   docker run -d --name signy-app -p 8080:8080 signy-backend
   ```
   The app will be live at `http://localhost:8080/`.

4. **Upload example videos into the container:**
   ```bash
   docker cp raw_videos signy-app:/app/raw_videos
   ```

5. **Import the WLASL gesture database (limited to 150 videos):**
   ```bash
   docker exec signy-app python manage.py import_raw_videos --limit 150
   ```

---

## Running without Docker (Developer Mode)

1. **Activate your virtual environment:**
   ```bash
   .\venv\Scripts\activate
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run migrations and seed the database:**
   ```bash
   python manage.py migrate
   python manage.py seed_lessons
   ```
4. **Boot up the dev server:**
   ```bash
   python manage.py runserver 8080
   ```
