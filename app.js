import { Api } from './api.js';
import { I18n } from './i18n.js';

const APP_ROUTES = new Set(['home', 'dashboard', 'library', 'progress', 'profile', 'practice', 'translate']);
const savedUser = (() => { try { return JSON.parse(localStorage.getItem('handsign_user')); } catch { return null; } })();
const state = {
  route: routeFromHash(), cameraStream: null, lesson: 'Hello',
  recorder: null, recordedChunks: [], recordingStartedAt: 0,
  timerId: null, autoStopTimer: null, landmarkTimer: null, landmarkFrames: [], returnRoute: 'dashboard',
  user: savedUser || { name:'Alex Morgan', email:'alex@example.com' }, lastModalFocus:null
};

const icons = {
  hand: `<svg viewBox="0 0 24 24" fill="none"><path d="M7.5 13V5.8a1.5 1.5 0 0 1 3 0V11m0-5.9a1.5 1.5 0 0 1 3 0V11m0-4.7a1.5 1.5 0 0 1 3 0V12m0-3.5a1.5 1.5 0 0 1 3 0v6.1c0 4-2.8 7.4-6.8 7.4h-1.3c-2.5 0-4.7-1.2-6-3.2L3 15.2a1.6 1.6 0 0 1 2.4-2l2.1 1.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  globe: `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7"/><path d="M3.5 12h17M12 3c2.2 2.45 3.25 5.45 3.25 9S14.2 18.55 12 21M12 3C9.8 5.45 8.75 8.45 8.75 12S9.8 18.55 12 21" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  close: '×'
};

const navIcons = {
  dashboard:`<svg viewBox="0 0 24 24" fill="none"><path d="m4 10 8-6 8 6v9a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1v-9Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>`,
  library:`<svg viewBox="0 0 24 24" fill="none"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v17H6.5A2.5 2.5 0 0 0 4 22V5.5Zm16 0A2.5 2.5 0 0 0 17.5 3H13v17h4.5A2.5 2.5 0 0 1 20 22V5.5Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>`,
  translate:`<svg viewBox="0 0 24 24" fill="none"><path d="M7 7h10m0 0-3-3m3 3-3 3M17 17H7m0 0 3 3m-3-3 3-3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  progress:`<svg viewBox="0 0 24 24" fill="none"><path d="M5 19V9m7 10V5m7 14v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,
  profile:`<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.8"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`
};

const EMOJI_MAP = {
  'Milk': '🥛', 'Water': '🚰', 'Eat / Food': '🍎', 'Drink': '🥤', 'Apple': '🍎', 'Cookie': '🍪',
  'Mother': '👩', 'Father': '👨', 'Baby / Child': '👶', 'Brother': '👦', 'Sister': '👧',
  'Help': '🫴', 'Please': '🙏', 'Thank You': '🤟', 'Yes': '👍', 'No': '👎',
  'More': '👐', 'Finished / All Done': '✨', 'Home': '🏠', 'Love': '❤️',
  'Happy': '😊', 'Sad': '😢', 'Play': '🎮', 'Sleep': '😴', 'Stop': '✋', 'Want': '🤲'
};

let lessons = [
  { name:'Milk', emoji:'🥛', level:'Beginner', time:'3 min', score:'New' },
  { name:'Water', emoji:'🚰', level:'Beginner', time:'4 min', score:'New' },
  { name:'Mother', emoji:'👩', level:'Essential', time:'5 min', score:'New' },
  { name:'Father', emoji:'👨', level:'Essential', time:'4 min', score:'New' }
];

async function fetchLessonsFromApi() {
  try {
    const data = await Api.lessons();
    if (data.results && data.results.length > 0) {
      lessons = data.results.map(w => ({
        name: w.name,
        emoji: EMOJI_MAP[w.name] || (w.name.startsWith('Letter') ? '🔤' : '🤟'),
        level: w.level || (w.is_premium ? 'Essential' : 'Beginner'),
        time: w.time || '4 min',
        score: w.score || 'New'
      }));
      const grid = document.querySelector('#libraryGrid');
      if (grid) {
        grid.innerHTML = `<div class="lessons-grid library-lessons">${lessons.map(l=>`<article class="lesson-card" tabindex="0" role="button" data-lesson="${l.name}"><div class="lesson-visual"><span class="level">${l.level}</span>${l.emoji}</div><div class="lesson-info"><h3>${l.name}</h3><div class="lesson-meta"><span>◷ ${l.time}</span><span>${l.score}</span></div></div></article>`).join('')}</div>`;
        bindLessonCards();
      }
    }
  } catch (e) {
    console.info('Lessons fetch info:', e);
  }
}

function isAuthenticated() {
  return Boolean(localStorage.getItem('handsign_access_token'));
}

function routeFromHash() {
  const loggedIn = isAuthenticated();
  if (!location.hash.startsWith('#/')) return loggedIn ? 'dashboard' : 'home';
  const route = location.hash.slice(2).split('/')[0] || (loggedIn ? 'dashboard' : 'home');
  if ((route === 'home' || route === '') && loggedIn) return 'dashboard';
  return APP_ROUTES.has(route) ? route : (loggedIn ? 'dashboard' : 'home');
}
function escapeHtml(value=''){return String(value).replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));}

function isDark(){ return document.documentElement.dataset.theme === 'dark'; }
function preferenceControls(){
  const languages=[['en','EN','English'],['ru','RU','Русский'],['cs','CS','Čeština']];
  return `<div class="preference-controls"><button type="button" class="icon-btn preference-button" data-theme-toggle aria-label="Toggle theme" title="${I18n.t(isDark()?'Light':'Dark')}">${isDark()?'☀':'☾'}</button><div class="language-switcher"><button type="button" class="language-trigger" data-language-toggle aria-haspopup="menu" aria-expanded="false" aria-label="Change language">${icons.globe}<strong>${I18n.current.toUpperCase()}</strong><span class="language-chevron">⌄</span></button><div class="language-menu" role="menu" aria-label="Change language">${languages.map(([code,short,label])=>`<button type="button" role="menuitemradio" aria-checked="${I18n.current===code}" class="language-option ${I18n.current===code?'active':''}" data-language-option="${code}"><span class="language-code">${short}</span><span>${label}</span><span class="language-check">${I18n.current===code?'✓':''}</span></button>`).join('')}</div></div></div>`;
}
function brand(){
  const target = isAuthenticated() ? 'dashboard' : 'home';
  return `<a class="brand" href="#/${target}" data-route="${target}"><span class="brand-mark">${icons.hand}</span><span>HandSign</span></a>`;
}

function nav(){ return `<header class="wrap nav">${brand()}<nav class="nav-links" aria-label="Primary navigation"><a href="#how" data-scroll="how">How it works</a><a href="#lessons" data-scroll="lessons">Lessons</a><button class="nav-link-button" data-route="translate">Free translate</button><a href="#pricing" data-scroll="pricing">Pricing</a></nav><div class="nav-actions">${preferenceControls()}<button class="btn btn-ghost" data-modal="login">Log in</button><button class="btn btn-dark nav-start" data-start>Start learning</button><button class="icon-btn mobile-menu" aria-label="Open menu" aria-controls="mobileDropdown" aria-expanded="false" data-mobile-menu>☰</button></div><div class="mobile-dropdown" id="mobileDropdown"><button data-scroll="how">How it works</button><button data-scroll="lessons">Lessons</button><button data-route="translate">Free translate</button><button data-scroll="pricing">Pricing</button><button data-modal="login">Log in</button></div></header>`; }

function lessonCards(extra='', limit=lessons.length){ return `<div class="lessons-grid ${extra}">${lessons.slice(0,limit).map(l=>`<article class="lesson-card" tabindex="0" role="button" data-lesson="${l.name}"><div class="lesson-visual"><span class="level">${l.level}</span>${l.emoji}</div><div class="lesson-info"><h3>${l.name}</h3><div class="lesson-meta"><span>◷ ${l.time}</span><span>${l.score}</span></div></div></article>`).join('')}</div>`; }

function home(){ return `<div class="shell">${nav()}
  <main>
    <section class="hero"><div class="wrap hero-grid"><div><span class="eyebrow">AI-powered ASL learning</span><h1>Small signs.<br><span class="highlight">Big connections.</span></h1><p class="lead">Learn practical American Sign Language with real-time, judgment-free feedback — built for the everyday moments that matter most.</p><div class="hero-actions"><button class="btn btn-dark" data-start>Start your first lesson <span>→</span></button><button class="btn btn-ghost" data-scroll="how">See how it works</button></div><div class="trust"><div class="avatars"><span class="avatar a1">MK</span><span class="avatar a2">JS</span><span class="avatar a3">AL</span></div><div><strong>Loved by early tester families</strong>Practice anytime. Learn at your pace.</div></div></div>
    <div class="hero-visual"><div class="camera-card"><div class="person"><div class="person-body"><div class="hair"></div><div class="head"></div><div class="shirt-neck"></div><span class="hand one">✋</span><span class="hand two">🤚</span></div></div><div class="camera-ui"><span class="live-pill"><i class="live-dot"></i> Hand tracking</span><span class="live-pill">● LIVE</span></div><div class="focus-corners"></div></div><div class="score-float"><small>Accuracy</small><div class="score">94%</div><small>Great form!</small></div><div class="lesson-float"><div class="lesson-top"><span>LESSON 01</span><b>2:14</b></div><div class="lesson-word">Hello 👋</div><div class="progress"><i style="width:68%"></i></div></div></div></div></section>
    <section class="logos"><div class="wrap">Designed to connect with<div class="logo-row"><span class="partner"><b>G</b> Google Cloud</span><span class="partner"><b>◇</b> MediaPipe</span><span class="partner"><b>✦</b> Gemini</span><span class="partner"><b>S</b> Stripe</span></div></div></section>
    <section id="how" class="section section-white"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Made for real life</span><h2>From camera on to confident in three simple steps.</h2></div><p class="section-sub">No special equipment or prior experience. HandSign works right in your browser and meets you where you are.</p></div><div class="steps"><article class="step"><span class="step-no">01 — PICK</span><span class="step-icon">☝️</span><h3>Choose a useful word</h3><p>Start with what your family needs today — from “more” and “milk” to feelings and routines.</p></article><article class="step"><span class="step-no">02 — PRACTICE</span><span class="step-icon">🤟</span><h3>Sign to your camera</h3><p>Our hand tracking follows your movement privately, directly in your browser, in real time.</p></article><article class="step"><span class="step-no">03 — CONNECT</span><span class="step-icon">✨</span><h3>Get kind, clear feedback</h3><p>Receive specific coaching on hand shape, placement and motion — then celebrate your progress.</p></article></div></div></section>
    <section class="translator-banner"><div class="wrap translator-banner-inner"><div><span class="eyebrow">Free sign translator</span><h2>Show it. We’ll put it into words.</h2><p>Turn on your camera, sign naturally, and get a text translation you can copy or hear aloud.</p></div><button class="btn btn-lime" data-route="translate">Open free translator →</button></div></section>
    <section id="lessons" class="section"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Explore lessons</span><h2>Start with words that open doors.</h2></div><button class="btn btn-ghost" data-route="library">View all lessons →</button></div>${lessonCards('',4)}</div></section>
    <section id="stories" class="quote"><div class="wrap quote-inner"><div class="quote-portrait">👩🏽<span class="quote-bubble">Day 18 · 12 signs learned</span></div><div><span class="eyebrow">A little win, a huge moment</span><blockquote>“The first time Leo signed ‘more’ at dinner, we both understood each other without a meltdown. I cried happy tears.”</blockquote><cite><strong>Maya & Leo</strong><br>HandSign pilot family</cite></div></div></section>
    <section id="pricing" class="cta"><div class="wrap cta-box"><span class="eyebrow">Your first lesson is free</span><h2>A new way to understand each other starts here.</h2><p>Five minutes, one useful sign, and supportive feedback. No credit card required.</p><button class="btn btn-dark" data-start>Try HandSign free →</button></div></section>
  </main><footer class="footer"><div class="wrap footer-inner">${brand()}<span>© 2026 HandSign. <span>Built with care for every communicator.</span></span><span class="footer-links"><button data-info="privacy">Privacy</button><button data-info="accessibility">Accessibility</button><button data-info="support">Support</button></span></div></footer></div>`; }

const sideItems = [
  ['dashboard','Home'], ['library','Lessons'], ['translate','Translate'],
  ['progress','Progress'], ['profile','Profile']
];
function sidebar(){const activeRoute=state.route==='practice'?'library':state.route;return `<aside class="sidebar">${brand()}<nav class="side-nav" aria-label="Application navigation">${sideItems.map(([route,label])=>`<button class="side-link ${activeRoute===route?'active':''}" data-route="${route}" aria-label="${label}" title="${label}" aria-current="${activeRoute===route?'page':'false'}"><span class="side-icon">${navIcons[route]}</span><span class="side-label">${label}</span></button>`).join('')}</nav><button class="side-footer" data-route="progress"><b>7 day streak 🔥</b><p>Practice one lesson today to keep it going.</p></button></aside>`;}
function appHeader(title,subtitle){
  const avatar = state.user.avatar || '';
  const isImage = avatar.startsWith('data:image') || avatar.startsWith('http');
  const userAvatarHtml = isImage
    ? `<img src="${avatar}" alt="Avatar">`
    : `<span>${avatar || '👤'}</span>`;

  return `
    <header class="app-top">
      <div class="greeting">
        <h1>${title}</h1>
        <p>${subtitle}</p>
      </div>
      <div class="user-row">
        ${preferenceControls()}
        <span class="streak">🔥 7 day streak</span>
        <div class="profile-dropdown-wrapper" style="position:relative;">
          <button class="profile-trigger" aria-label="Open user menu" data-profile-toggle>
            ${userAvatarHtml}
          </button>
          <div class="profile-menu" id="profileDropdown" style="display:none;position:absolute;right:0;top:calc(100% + 8px);border-radius:14px;padding:8px;z-index:1000;min-width:185px;">
            <div style="padding:8px 12px;border-bottom:1px solid var(--line);margin-bottom:6px;">
              <strong style="display:block;font-size:14px;">${escapeHtml(state.user.name)}</strong>
              <small style="font-size:12px;display:block;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(state.user.email)}</small>
            </div>
            <button type="button" class="btn btn-ghost" data-route="profile" style="width:100%;text-align:left;justify-content:flex-start;padding:8px 12px;font-size:14px;">
              ⚙ Profile & Settings
            </button>
            <button type="button" class="btn text-button" data-logout style="width:100%;text-align:left;justify-content:flex-start;padding:8px 12px;font-size:14px;color:#ff806a;">
              🚪 Sign out
            </button>
          </div>
        </div>
      </div>
    </header>
  `;
}
function appShell(content,title,subtitle){return `<div class="app-layout">${sidebar()}<main class="app-main">${appHeader(title,subtitle)}${content}</main></div>`;}
function immersiveShell(content){return `<div class="app-layout immersive-layout">${sidebar()}<div class="immersive-main">${content}</div></div>`;}

function dashboard(){const firstName=escapeHtml(state.user.name?.split(' ')[0]||'Alex');const greeting=`${I18n.t('Good morning')}, ${firstName} 👋`;return appShell(`<div class="dash-grid"><section class="continue"><span class="eyebrow">Continue learning</span><h2>Everyday essentials</h2><p>Lesson 3 of 8 · You're learning words that make daily routines easier.</p><div class="progress"><i style="width:37%"></i></div><button class="btn btn-lime" data-lesson="More">Continue lesson →</button></section><section class="stat-card"><span class="eyebrow">Weekly goal</span><div class="stat-ring"><strong>5 / 7</strong></div><p style="text-align:center;color:var(--muted);font-size:13px">Two more days to reach your goal</p></section></div><section class="dashboard-section"><div class="dashboard-title"><h2>Recommended for you</h2><button class="btn btn-ghost small-btn" data-route="library">See all</button></div>${lessonCards('dashboard-lessons',4)}</section>`,greeting,'Ready for one small step forward?');}
function library(){return appShell(`<div class="filter-row"><button class="filter active" data-filter="all">All lessons</button><button class="filter" data-filter="Beginner">Beginner</button><button class="filter" data-filter="Essential">Essential</button><button class="filter" data-filter="Everyday">Everyday</button></div><div id="libraryGrid">${lessonCards('library-lessons')}</div>`,'Lesson library','Practical signs, organized into small and friendly lessons.');}
function progressPage(){return appShell(`<div class="metric-grid"><article class="metric"><span>Signs learned</span><strong>12</strong><small>+4 this week</small></article><article class="metric"><span>Average accuracy</span><strong>86%</strong><small>↑ 7% this month</small></article><article class="metric"><span>Practice time</span><strong>48m</strong><small>Across 9 sessions</small></article></div><section class="progress-panel"><div class="dashboard-title"><h2>Your week</h2><span class="muted">Goal: 5 minutes a day</span></div><div class="week-bars">${['M','T','W','T','F','S','S'].map((d,i)=>`<div><i style="height:${[55,82,45,92,68,30,15][i]}%"></i><span>${d}</span></div>`).join('')}</div></section>`,'Your progress','Every practice session is a meaningful step.');}
function profilePage(){
  const isSubscribed = state.user.is_subscribed;
  const avatar = state.user.avatar || '👤';
  const isCustomImage = avatar.startsWith('data:image') || avatar.startsWith('http');
  const avatarPreviewHtml = isCustomImage
    ? `<img id="avatarPreviewDisplay" src="${avatar}" style="width:54px;height:54px;border-radius:50%;object-fit:cover;border:2px solid var(--lime,#a6f0c6);">`
    : `<span id="avatarPreviewDisplay" style="font-size:36px;background:var(--bg-subtle,#f0f4ec);padding:8px;border-radius:50%;line-height:1;display:inline-block;">${avatar}</span>`;

  return appShell(`
    <div class="settings-grid">
      <section class="settings-card">
        <span class="eyebrow">Profile</span>
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;">
          ${avatarPreviewHtml}
          <div>
            <h2 style="margin:0;">${escapeHtml(state.user.name)}</h2>
            <p class="muted" style="margin:0;">${escapeHtml(state.user.email)}</p>
          </div>
        </div>
        <div class="button-row">
          <button class="btn text-button" data-logout>Sign out</button>
        </div>
      </section>

      <section class="settings-card">
        <span class="eyebrow">Account Settings</span>
        <h2>User Details & Custom Avatar</h2>
        <form class="api-form" id="userSettingsForm">
          <label class="field">Your Name
            <input id="userNameInput" type="text" value="${escapeHtml(state.user.name)}" required>
          </label>
          <label class="field">Email Address
            <input id="userEmailInput" type="email" value="${escapeHtml(state.user.email)}" required>
          </label>
          
          <label class="field">Upload Custom Avatar Image
            <input id="userAvatarFileInput" type="file" accept="image/*" style="padding:10px;width:100%;">
          </label>

          <label class="field">Or Select Preset Icon
            <select id="userAvatarInput" style="width:100%;padding:10px;font-size:16px;">
              <option value="" ${isCustomImage?'selected':''}>Custom Uploaded Image</option>
              <option value="👤" ${avatar==='👤'?'selected':''}>👤 Default Profile</option>
              <option value="👩" ${avatar==='👩'?'selected':''}>👩 Woman</option>
              <option value="👨" ${avatar==='👨'?'selected':''}>👨 Man</option>
              <option value="👧" ${avatar==='👧'?'selected':''}>👧 Girl</option>
              <option value="👦" ${avatar==='👦'?'selected':''}>👦 Boy</option>
              <option value="🦊" ${avatar==='🦊'?'selected':''}>🦊 Fox</option>
              <option value="🦁" ${avatar==='🦁'?'selected':''}>🦁 Lion</option>
              <option value="🐼" ${avatar==='🐼'?'selected':''}>🐼 Panda</option>
            </select>
          </label>
          <div style="border-top:1px solid var(--line);margin-top:12px;padding-top:12px;">
            <label class="field">New Password (optional)
              <input id="userNewPasswordInput" type="password" placeholder="At least 6 characters" minlength="6">
            </label>
          </div>
          <div class="button-row" style="margin-top:12px;">
            <button class="btn btn-dark" type="submit">Save settings</button>
            <span class="connection-state" id="settingsSaveStatus"></span>
          </div>
        </form>
      </section>

      <section class="settings-card">
        <span class="eyebrow">Subscription & Plan</span>
        <h2>${isSubscribed ? 'Family Unlimited Access' : 'Free Explorer'}</h2>
        <p class="muted">${isSubscribed ? 'Your account has full access to all sign language lessons and AI coaching.' : 'Four starter lessons and free sign translator previews.'}</p>
        ${isSubscribed ? '<span style="color:#28a745;font-weight:bold;">Active Subscription ✓</span>' : '<button class="btn btn-lime" data-checkout>Upgrade to Family ($10)</button>'}
      </section>
    </div>
  `,'Profile & settings','Manage your user account, security and custom avatar.');
}

function practice(){ const l=lessons.find(x=>x.name===state.lesson)||lessons[0],back=state.returnRoute==='home'?'home':'library'; return immersiveShell(`<main class="practice"><section class="practice-camera"><div class="camera-empty" id="cameraEmpty"><div><div class="big-icon">${l.emoji}</div><h2>Ready when you are</h2><p>Turn on your camera and place your upper body inside the guide.</p></div></div><video id="camera" autoplay muted playsinline></video><div class="practice-overlay"><header class="practice-head"><button class="icon-btn" data-route="${back}" aria-label="Go back">←</button><div class="practice-head-actions"><span class="live-pill"><i class="live-dot"></i> Private on-device tracking</span>${preferenceControls()}</div></header><div class="tracking-box"></div></div></section><aside class="practice-side"><span class="eyebrow">Guided lesson · Beginner</span><h1>${l.name}</h1><p>Watch the example, then mirror the movement. Keep your hand relaxed and clearly visible.</p><div class="demo-sign">${l.emoji}</div><div class="tips"><span>💡</span><span><strong>Quick tip</strong><br>Face your palm forward and make the motion gently, not too fast.</span></div><div class="feedback" id="feedback"></div><div class="practice-actions"><button class="btn btn-dark" id="cameraToggle">Turn on camera</button><button class="btn btn-ghost" id="checkSign">Check my sign</button></div></aside></main>`);}

function translatePage(){const back=state.returnRoute==='home'?'home':'dashboard';return immersiveShell(`<main class="practice translate-page"><section class="practice-camera"><div class="camera-empty" id="cameraEmpty"><div><div class="big-icon">🤟</div><h2>Your signing space</h2><p>Turn on the camera, then press “Start signing”. Use natural pauses between phrases.</p></div></div><video id="camera" autoplay muted playsinline></video><div class="practice-overlay"><header class="practice-head"><button class="icon-btn" data-route="${back}" aria-label="Go back">←</button><div class="practice-head-actions"><span class="live-pill" id="recordingPill"><i class="live-dot"></i> Ready to translate</span>${preferenceControls()}</div></header><div class="tracking-box"></div><div class="record-timer" id="recordTimer">00:00</div></div></section><aside class="practice-side translator-side"><span class="eyebrow">Free translation · ASL → English</span><h1>Sign freely</h1><p>Show a phrase of up to 20 seconds. HandSign sends the captured sequence to <code>POST /translate/</code> and returns plain text.</p><div class="translation-result empty" id="translationResult"><span>Translation will appear here</span><strong>...</strong></div><div class="translation-tools"><button class="tool-button" id="copyTranslation" disabled>Copy text</button><button class="tool-button" id="speakTranslation" disabled>Read aloud</button></div><div class="privacy-note">🔒 <span>Camera data is used only for this translation. In demo mode, no clip leaves your browser.</span></div><div class="practice-actions"><button class="btn btn-dark" id="cameraToggle">Turn on camera</button><button class="btn btn-lime" id="recordToggle">Start signing</button></div></aside></main>`);}

function modal(type){
  const info = {
    privacy:['Privacy by design','The frontend keeps camera processing local until you explicitly request an evaluation or translation. Connect your own privacy policy before launch.'],
    accessibility:['Accessibility','Keyboard navigation, visible focus states and readable contrast are included. Add signed video alternatives with your lesson content.'],
    support:['We’re here to help','If the camera is not working, check browser permissions first. Account and billing support can be connected to your support desk before public launch.']
  };
  if(type==='profile')return `<div class="modal-backdrop" id="modal"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle"><button class="icon-btn modal-close" data-close aria-label="Close">${icons.close}</button><span class="eyebrow">HandSign</span><h2 id="modalTitle">Edit profile</h2><p>Keep your learning profile up to date.</p><form class="form" id="profileForm"><label class="field">Your name<input name="name" required value="${escapeHtml(state.user.name)}"></label><label class="field">Email address<input name="email" required type="email" value="${escapeHtml(state.user.email)}"></label><button class="btn btn-dark" type="submit">Save changes</button></form></section></div>`;
  if(info[type]) return `<div class="modal-backdrop" id="modal"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle"><button class="icon-btn modal-close" data-close aria-label="Close">${icons.close}</button><span class="eyebrow">HandSign</span><h2 id="modalTitle">${info[type][0]}</h2><p>${info[type][1]}</p><button class="btn btn-dark" data-close>Got it</button></section></div>`;
  return `<div class="modal-backdrop" id="modal"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle"><button class="icon-btn modal-close" data-close aria-label="Close">${icons.close}</button><span class="eyebrow">Welcome to HandSign</span><h2 id="modalTitle">${type==='login'?'Good to see you again.':'Let’s learn your first sign.'}</h2><p>${type==='login'?'Continue right where you left off.':'Create your free account — no credit card needed.'}</p><form class="form" id="authForm" data-auth-type="${type}">${type==='login'?'':`<label class="field">Your name<input name="name" required placeholder="Alex"></label>`}<label class="field">Email address<input name="email" required type="email" placeholder="you@example.com"></label><label class="field">Password<input name="password" required type="password" minlength="6" placeholder="At least 6 characters"></label><button class="btn btn-dark" type="submit">${type==='login'?'Log in':'Create free account'} →</button></form></section></div>`;
}

function render(){
  stopCamera();
  const views = { home, dashboard, library, progress:progressPage, profile:profilePage, practice, translate:translatePage };
  document.querySelector('#app').innerHTML = (views[state.route] || home)();
  I18n.apply(document.querySelector('#app')); bind(); window.scrollTo(0,0);
  fetchLessonsFromApi();
  if(state.route==='dashboard') hydrateDashboard();
  if(state.route==='progress') hydrateProgressPage();
}
async function hydrateDashboard(){
  try {
    const data = await Api.progress();
    const streak = document.querySelector('.streak');
    if (streak && data.streak !== undefined) streak.textContent = `🔥 ${data.streak} ${I18n.t('day streak')}`;
    const sideStreak = document.querySelector('.side-footer b');
    if (sideStreak && data.streak !== undefined) sideStreak.textContent = `${data.streak} ${I18n.t('day streak')} 🔥`;

    const continueDesc = document.querySelector('.continue p');
    if (continueDesc && data.completed !== undefined) {
      continueDesc.textContent = `Completed ${data.completed} signs · Practice every day to build your vocabulary!`;
    }
    const continueBar = document.querySelector('.continue .progress i');
    if (continueBar && data.completed !== undefined) {
      const pct = Math.min(100, Math.round((data.completed / 36) * 100));
      continueBar.style.width = `${Math.max(5, pct)}%`;
    }
    const statRing = document.querySelector('.stat-ring strong');
    if (statRing && data.completed !== undefined) {
      statRing.textContent = `${Math.min(7, data.completed)} / 7`;
    }
  } catch (e) {
    console.info('Dashboard hydration info:', e);
  }
}
async function hydrateProgressPage(){
  try {
    const data = await Api.progress();
    const metrics = document.querySelectorAll('.metric-grid .metric strong');
    if (metrics.length >= 3) {
      if (data.completed !== undefined) metrics[0].textContent = String(data.completed);
      if (data.accuracy !== undefined) metrics[1].textContent = `${data.accuracy}%`;
      if (data.practice_time !== undefined) metrics[2].textContent = data.practice_time;
    }
    const streak = document.querySelector('.streak');
    if (streak && data.streak !== undefined) streak.textContent = `🔥 ${data.streak} ${I18n.t('day streak')}`;
    const sideStreak = document.querySelector('.side-footer b');
    if (sideStreak && data.streak !== undefined) sideStreak.textContent = `${data.streak} ${I18n.t('day streak')} 🔥`;

    if (Array.isArray(data.week_bars)) {
      const barElements = document.querySelectorAll('.week-bars i');
      barElements.forEach((bar, idx) => {
        if (data.week_bars[idx] !== undefined) {
          bar.style.height = `${Math.max(5, data.week_bars[idx])}%`;
        }
      });
    }
  } catch (e) {
    console.info('Progress hydration info:', e);
  }
}
function go(route){ if(!APP_ROUTES.has(route)) route='home';if(['translate','practice'].includes(route)&&!['translate','practice'].includes(state.route))state.returnRoute=state.route;const hash=`#/${route}`; if(location.hash===hash){state.route=route;render();}else location.hash=hash; }
function closeModal(){const m=document.querySelector('#modal');if(!m)return;m.remove();state.lastModalFocus?.focus?.();state.lastModalFocus=null;}
function showModal(type){ state.lastModalFocus=document.activeElement;document.querySelector('#modal')?.remove(); document.body.insertAdjacentHTML('beforeend',modal(type)); I18n.apply(document.querySelector('#modal')); bindModal();requestAnimationFrame(()=>document.querySelector('#modal input, #modal [data-close]')?.focus()); }
function bindModal(){
  const m=document.querySelector('#modal');
  m?.addEventListener('click',e=>{if(e.target===m||e.target.closest('[data-close]'))closeModal();});
  m?.addEventListener('keydown',e=>{if(e.key!=='Tab')return;const items=[...m.querySelectorAll('button:not(:disabled),input:not(:disabled),a[href]')];if(!items.length)return;const first=items[0],last=items.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}});
  document.querySelector('#profileForm')?.addEventListener('submit',async e=>{e.preventDefault();const form=e.currentTarget,button=form.querySelector('button[type="submit"]'),data=Object.fromEntries(new FormData(form));button.disabled=true;button.textContent=I18n.t('Saving…');try{const result=await Api.updateProfile(data);state.user=result.user||data;localStorage.setItem('handsign_user',JSON.stringify(state.user));closeModal();render();toast('Profile updated.');}catch(error){button.disabled=false;button.textContent=I18n.t('Save changes');toast(error.message);}});
  document.querySelector('#authForm')?.addEventListener('submit',async e=>{
    e.preventDefault(); const form=e.currentTarget, button=form.querySelector('button[type="submit"]');
    const data=Object.fromEntries(new FormData(form)); button.disabled=true; button.textContent=I18n.t('Connecting…');
    try { const result=form.dataset.authType==='login'?await Api.login(data):await Api.register(data);if(result.user){state.user={...state.user,...result.user};localStorage.setItem('handsign_user',JSON.stringify(state.user));} closeModal(); toast(result.demo?'Demo account ready — connect Django in Profile.':'Welcome to HandSign!'); setTimeout(()=>go('dashboard'),350); }
    catch(error){ button.disabled=false; button.textContent=I18n.t('Try again'); toast(error.message); }
  });
}
function toast(msg){ const el=document.querySelector('#toast'); el.textContent=I18n.t(msg); el.classList.add('show'); clearTimeout(toast.timer); toast.timer=setTimeout(()=>el.classList.remove('show'),3200); }

async function startCamera(){
  const video=document.querySelector('#camera'), empty=document.querySelector('#cameraEmpty'), btn=document.querySelector('#cameraToggle');
  if(!navigator.mediaDevices?.getUserMedia){toast('Camera requires localhost or HTTPS.');return false;}
  try{state.cameraStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:1280},height:{ideal:720}},audio:false});video.srcObject=state.cameraStream;empty.style.display='none';btn.textContent=I18n.t('Turn off camera');return true;}
  catch{toast('Camera access was blocked. Allow it in browser settings.');return false;}
}
async function toggleCamera(){ const video=document.querySelector('#camera'), empty=document.querySelector('#cameraEmpty'), btn=document.querySelector('#cameraToggle'); if(state.cameraStream){stopCamera();video.srcObject=null;empty.style.display='grid';btn.textContent=I18n.t('Turn on camera');return false;} const ok=await startCamera();if(ok)toast('Camera is ready.');return ok; }
function stopCamera(){
  clearInterval(state.timerId); clearInterval(state.landmarkTimer);clearTimeout(state.autoStopTimer);state.autoStopTimer=null;
  if(state.recorder?.state==='recording') { state.recorder.onstop=null; state.recorder.stop(); }
  state.recorder=null;
  if(state.cameraStream){state.cameraStream.getTracks().forEach(t=>t.stop());state.cameraStream=null;}
}

function setFeedback(box,heading,message=''){
  box.replaceChildren();const strong=document.createElement('strong');strong.textContent=heading;box.append(strong);
  if(message){box.append(document.createElement('br'),document.createTextNode(message));}
}
function setTranslationResult(box,label,text){
  box.replaceChildren();const meta=document.createElement('span'),value=document.createElement('strong');meta.textContent=label;value.textContent=text;box.append(meta,value);box.dataset.text=text;
}

async function evaluateSign(){
  const box=document.querySelector('#feedback'), btn=document.querySelector('#checkSign');
  if(!state.cameraStream){const ready=await startCamera();if(ready)toast('Camera is ready. Show the sign, then check it again.');return;}
  btn.disabled=true;btn.textContent=I18n.t('Analyzing…');box.style.display='block';setFeedback(box,I18n.t('Looking at your movement…'));
  const landmarks=window.HandSignLandmarkProvider?.getSequence?.() || [];
  try{const result=await Api.evaluateSign({lesson:state.lesson,landmarks,language:I18n.current});setFeedback(box,`${result.score}% ${I18n.t('match')}${result.demo?` · ${I18n.t('Demo')}`:''}`,I18n.t(result.feedback));toast(result.demo?'Demo feedback shown — API endpoint is ready to connect.':'Sign analyzed successfully.');}
  catch(error){setFeedback(box,I18n.t('Could not analyze'),error.message);}
  finally{btn.disabled=false;btn.textContent=I18n.t('Check my sign');}
}

async function startRecording(){
  if(!state.cameraStream && !(await startCamera())) return;
  if(!window.MediaRecorder){toast('This browser does not support gesture recording.');return;}
  state.recordedChunks=[]; state.landmarkFrames=[]; state.recordingStartedAt=Date.now();
  const mime=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(MediaRecorder.isTypeSupported);
  state.recorder=new MediaRecorder(state.cameraStream,mime?{mimeType:mime}:undefined);
  state.recorder.ondataavailable=e=>{if(e.data.size)state.recordedChunks.push(e.data);};
  state.recorder.onstop=submitTranslation;
  state.recorder.start(250);
  state.landmarkTimer=setInterval(()=>{const frame=window.HandSignLandmarkProvider?.getFrame?.();if(frame)state.landmarkFrames.push({t:Date.now()-state.recordingStartedAt,points:frame});},100);
  const button=document.querySelector('#recordToggle'),pill=document.querySelector('#recordingPill'),cameraButton=document.querySelector('#cameraToggle');button.textContent=I18n.t('Stop & translate');button.classList.add('recording');cameraButton.disabled=true;pill.innerHTML=`<i class="record-dot"></i> ${I18n.t('Recording your signs')}`;
  updateTimer(); state.timerId=setInterval(updateTimer,250);
  const activeRecorder=state.recorder;clearTimeout(state.autoStopTimer);state.autoStopTimer=setTimeout(()=>{if(state.recorder===activeRecorder&&activeRecorder.state==='recording')stopRecording();},20000);
}
function updateTimer(){const seconds=Math.floor((Date.now()-state.recordingStartedAt)/1000);const el=document.querySelector('#recordTimer');if(el)el.textContent=`00:${String(seconds).padStart(2,'0')}`;}
function stopRecording(){if(state.recorder?.state!=='recording')return;clearInterval(state.timerId);clearInterval(state.landmarkTimer);clearTimeout(state.autoStopTimer);state.autoStopTimer=null;state.recorder.stop();const button=document.querySelector('#recordToggle');if(button){button.disabled=true;button.textContent=I18n.t('Translating…');}const pill=document.querySelector('#recordingPill');if(pill)pill.textContent=I18n.t('AI is reading the sequence…');}
async function submitTranslation(){
  const durationMs=Date.now()-state.recordingStartedAt; const clip=new Blob(state.recordedChunks,{type:state.recorder?.mimeType||'video/webm'}); const resultBox=document.querySelector('#translationResult');
  if(!resultBox) return;
  try{const result=await Api.translateClip({clip,landmarks:state.landmarkFrames,durationMs,language:I18n.current});const translatedText=result.demo?I18n.t(result.text):result.text;resultBox.classList.remove('empty');setTranslationResult(resultBox,`${I18n.t(result.demo?'Demo translation':'Translation')} · ${Math.round((result.confidence||0)*100)}% ${I18n.t('confidence')}`,translatedText);document.querySelector('#copyTranslation').disabled=false;document.querySelector('#speakTranslation').disabled=false;toast(result.demo?'Demo result shown — connect POST /translate/ for real recognition.':'Translation complete.');}
  catch(error){resultBox.classList.remove('empty');setTranslationResult(resultBox,I18n.t('Translation failed'),error.message);}
  finally{const button=document.querySelector('#recordToggle'),cameraButton=document.querySelector('#cameraToggle');if(button){button.disabled=false;button.textContent=I18n.t('Sign another phrase');button.classList.remove('recording');}if(cameraButton)cameraButton.disabled=false;const pill=document.querySelector('#recordingPill');if(pill)pill.innerHTML=`<i class="live-dot"></i> ${I18n.t('Ready to translate')}`;state.recorder=null;}
}

async function saveUserSettings(e){
  e.preventDefault();
  const status=document.querySelector('#settingsSaveStatus');
  if(status){status.textContent=I18n.t('Saving…');status.className='connection-state';}
  const name=document.querySelector('#userNameInput').value;
  const email=document.querySelector('#userEmailInput').value;
  const presetAvatar=document.querySelector('#userAvatarInput').value;
  const fileInput=document.querySelector('#userAvatarFileInput');
  const new_password=document.querySelector('#userNewPasswordInput').value;

  let avatar = presetAvatar;
  if(fileInput && fileInput.files && fileInput.files[0]){
    avatar = await new Promise((resolve)=>{
      const reader=new FileReader();
      reader.onload=()=>resolve(reader.result);
      reader.onerror=()=>resolve(presetAvatar||'👤');
      reader.readAsDataURL(fileInput.files[0]);
    });
  }

  try{
    const updated=await Api.updateProfile({name,email,avatar,new_password});
    state.user={...state.user,...updated};
    localStorage.setItem('handsign_user',JSON.stringify(state.user));
    if(status){status.textContent=I18n.t('Profile updated.');status.classList.add('connected');}
    toast(I18n.t('Profile updated.'));
    render();
  }catch(error){
    if(status){status.textContent=I18n.t(error.message);status.classList.add('offline');}
    toast(I18n.t(error.message));
  }
}

function filterLessons(level,button){document.querySelectorAll('.filter').forEach(x=>x.classList.remove('active'));button.classList.add('active');const selected=level==='all'?lessons:lessons.filter(x=>x.level===level);const grid=document.querySelector('#libraryGrid');grid.innerHTML=`<div class="lessons-grid library-lessons">${selected.map(l=>`<article class="lesson-card" tabindex="0" role="button" data-lesson="${l.name}"><div class="lesson-visual"><span class="level">${l.level}</span>${l.emoji}</div><div class="lesson-info"><h3>${l.name}</h3><div class="lesson-meta"><span>◷ ${l.time}</span><span>${l.score}</span></div></div></article>`).join('')}</div>`;I18n.apply(grid);bindLessonCards();}
async function checkout(){const btn=document.querySelector('[data-checkout]');btn.disabled=true;btn.textContent=I18n.t('Opening checkout…');try{const result=await Api.createCheckout();if(result.url){const target=new URL(result.url,location.origin);if(target.origin===location.origin||target.hostname==='checkout.stripe.com')location.assign(target.href);else throw new Error('Unexpected checkout URL.');}else{toast('Stripe endpoint is ready; demo mode does not open payment.');btn.disabled=false;btn.textContent=I18n.t('Upgrade to Family');}}catch(error){toast(error.message);btn.disabled=false;btn.textContent=I18n.t('Upgrade to Family');}}
function logout(){localStorage.removeItem('handsign_access_token');localStorage.removeItem('handsign_user');state.user={name:'Alex Morgan',email:'alex@example.com'};toast('Signed out.');go('home');}
function bindLessonCards(){document.querySelectorAll('[data-lesson]').forEach(el=>{el.onclick=()=>{state.lesson=el.dataset.lesson;go('practice');};el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();el.click();}};});}
function updatePreferenceUrl(key,value){const url=new URL(location.href);url.searchParams.set(key,value);history.replaceState(null,'',`${url.pathname}${url.search}${url.hash}`);}
function toggleTheme(){
  const next=isDark()?'light':'dark'; document.documentElement.dataset.theme=next; localStorage.setItem('handsign_theme',next);
  document.querySelector('meta[name="theme-color"]').content=next==='dark'?'#0b1714':'#f5f7f2';
  updatePreferenceUrl('theme',next);
  document.querySelectorAll('[data-theme-toggle]').forEach(button=>{button.textContent=next==='dark'?'☀':'☾';button.title=I18n.t(next==='dark'?'Light':'Dark');});
}
function changeLanguage(language){
  I18n.set(language);updatePreferenceUrl('lang',language);I18n.apply(document.querySelector('#app'));const openModal=document.querySelector('#modal');if(openModal)I18n.apply(openModal);
  document.querySelectorAll('[data-language-toggle] strong').forEach(el=>el.textContent=language.toUpperCase());
  document.querySelectorAll('[data-language-option]').forEach(el=>{const active=el.dataset.languageOption===language;el.classList.toggle('active',active);el.setAttribute('aria-checked',String(active));el.querySelector('.language-check').textContent=active?'✓':'';});
  closeLanguageMenus();
}
function closeLanguageMenus(except=null){
  document.querySelectorAll('.language-switcher.open').forEach(switcher=>{
    if(switcher===except)return;
    const returnFocus=switcher.contains(document.activeElement);
    switcher.classList.remove('open');
    const trigger=switcher.querySelector('[data-language-toggle]');trigger?.setAttribute('aria-expanded','false');if(returnFocus)trigger?.focus();
  });
}
function closeMobileMenu(){document.querySelector('#mobileDropdown')?.classList.remove('open');document.querySelector('[data-mobile-menu]')?.setAttribute('aria-expanded','false');}

async function copyText(text){
  try{if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(text);else throw new Error('clipboard unavailable');}
  catch{const area=document.createElement('textarea');area.value=text;area.setAttribute('readonly','');area.style.position='fixed';area.style.opacity='0';document.body.append(area);area.select();const copied=document.execCommand('copy');area.remove();if(!copied)throw new Error(I18n.t('Could not copy the translation.'));}
}
function speakText(text){
  if(!('speechSynthesis' in window)){toast('Speech is not supported in this browser.');return;}
  speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(text);utterance.lang={en:'en-US',ru:'ru-RU',cs:'cs-CZ'}[I18n.current];speechSynthesis.speak(utterance);
}
function toggleLanguageMenu(button){
  const switcher=button.closest('.language-switcher'); const willOpen=!switcher.classList.contains('open');
  closeLanguageMenus(switcher); switcher.classList.toggle('open',willOpen); button.setAttribute('aria-expanded',String(willOpen));
  if(willOpen) requestAnimationFrame(()=>switcher.querySelector('.language-option.active')?.focus());
}

function toggleProfileMenu(){
  const menu = document.querySelector('#profileDropdown');
  if(!menu) return;
  menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
}
function closeProfileMenu(){
  const menu = document.querySelector('#profileDropdown');
  if(menu) menu.style.display = 'none';
}

function bind(){
  document.querySelectorAll('[data-start]').forEach(el=>el.onclick=()=>showModal('signup'));
  document.querySelectorAll('[data-modal]').forEach(el=>el.onclick=()=>{closeMobileMenu();closeProfileMenu();showModal(el.dataset.modal);});
  document.querySelectorAll('[data-info]').forEach(el=>el.onclick=()=>showModal(el.dataset.info));
  document.querySelectorAll('[data-route]').forEach(el=>el.onclick=e=>{e.preventDefault();closeProfileMenu();go(el.dataset.route);});
  document.querySelectorAll('[data-scroll]').forEach(el=>el.onclick=e=>{e.preventDefault();document.querySelector(`#${el.dataset.scroll}`)?.scrollIntoView({behavior:'smooth'});closeMobileMenu();closeProfileMenu();});
  document.querySelector('[data-mobile-menu]')?.addEventListener('click',e=>{const menu=document.querySelector('#mobileDropdown'),open=!menu.classList.contains('open');menu.classList.toggle('open',open);e.currentTarget.setAttribute('aria-expanded',String(open));});
  bindLessonCards();
  document.querySelectorAll('[data-filter]').forEach(el=>el.onclick=()=>filterLessons(el.dataset.filter,el));
  document.querySelector('[data-action="edit-profile"]')?.addEventListener('click',()=>showModal('profile'));
  document.querySelectorAll('[data-logout]').forEach(el=>el.addEventListener('click',()=>{ closeProfileMenu(); logout(); }));
  document.querySelector('#userSettingsForm')?.addEventListener('submit',saveUserSettings);
  document.querySelectorAll('[data-profile-toggle]').forEach(el=>el.addEventListener('click',e=>{e.stopPropagation();toggleProfileMenu();}));

  document.querySelector('[data-checkout]')?.addEventListener('click',checkout);
  document.querySelectorAll('[data-theme-toggle]').forEach(el=>el.addEventListener('click',toggleTheme));
  document.querySelectorAll('[data-language-toggle]').forEach(el=>el.addEventListener('click',e=>{e.stopPropagation();toggleLanguageMenu(el);}));
  document.querySelectorAll('[data-language-option]').forEach(el=>el.addEventListener('click',e=>{e.stopPropagation();changeLanguage(el.dataset.languageOption);}));
  document.querySelectorAll('[data-language-option]').forEach(el=>el.addEventListener('keydown',e=>{const options=[...el.closest('.language-menu').querySelectorAll('[data-language-option]')];const index=options.indexOf(el);if(['ArrowDown','ArrowRight'].includes(e.key)){e.preventDefault();options[(index+1)%options.length].focus();}if(['ArrowUp','ArrowLeft'].includes(e.key)){e.preventDefault();options[(index-1+options.length)%options.length].focus();}if(e.key==='Home'){e.preventDefault();options[0].focus();}if(e.key==='End'){e.preventDefault();options.at(-1).focus();}}));
  document.querySelector('#cameraToggle')?.addEventListener('click',toggleCamera);
  document.querySelector('#checkSign')?.addEventListener('click',evaluateSign);
  document.querySelector('#recordToggle')?.addEventListener('click',()=>state.recorder?.state==='recording'?stopRecording():startRecording());
  document.querySelector('#copyTranslation')?.addEventListener('click',async()=>{const text=document.querySelector('#translationResult')?.dataset.text;if(text){try{await copyText(text);toast('Translation copied.');}catch(error){toast(error.message);}}});
  document.querySelector('#speakTranslation')?.addEventListener('click',()=>{const text=document.querySelector('#translationResult')?.dataset.text;if(text)speakText(text);});
}

window.addEventListener('hashchange',()=>{const route=routeFromHash();if(route!==state.route){state.route=route;render();}});
document.addEventListener('click',event=>{
  if(!event.target.closest('.language-switcher'))closeLanguageMenus();
  if(!event.target.closest('.nav'))closeMobileMenu();
  if(!event.target.closest('.profile-dropdown-wrapper'))closeProfileMenu();
});
document.addEventListener('keydown',event=>{if(event.key==='Escape'){closeLanguageMenus();closeMobileMenu();closeProfileMenu();closeModal();}});
render();
