/**
 * HandSign backend adapter.
 *
 * Change the API URL from Profile → Backend connection, or define
 * <meta name="api-base" content="https://api.example.com/api/v1">.
 * Every method has an explicit demo fallback so the frontend remains usable
 * while Django is offline. Responses using a fallback contain `demo: true`.
 */

const DEFAULT_API_BASE = '/api/v1';

class HttpError extends Error {
  constructor(message, status, payload, isJson = false) { super(message); this.name = 'HttpError'; this.status = status; this.payload = payload; this.isJson = isJson; }
}

function apiBase() {
  const fromMeta = document.querySelector('meta[name="api-base"]')?.content;
  return (localStorage.getItem('handsign_api_base') || fromMeta || DEFAULT_API_BASE).replace(/\/$/, '');
}

function demoFallbackEnabled() {
  return document.querySelector('meta[name="api-demo-fallback"]')?.content === 'true';
}

function authHeaders() {
  const token = localStorage.getItem('handsign_access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function cookie(name) {
  return document.cookie.split('; ').find(part => part.startsWith(`${name}=`))?.split('=').slice(1).join('=') || '';
}

async function request(path, { method = 'GET', body, formData, timeout = 8000, fallback } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(`${apiBase()}${path}`, {
      method,
      credentials: 'include',
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...authHeaders(),
        ...(method !== 'GET' && cookie('csrftoken') ? { 'X-CSRFToken': decodeURIComponent(cookie('csrftoken')) } : {}),
        ...(formData ? {} : { 'Content-Type': 'application/json' })
      },
      body: formData || (body ? JSON.stringify(body) : undefined)
    });
    const isJson = response.headers.get('content-type')?.includes('application/json');
    const payload = response.status === 204 ? {} : isJson ? await response.json().catch(() => ({})) : {};
    if (!response.ok) {
      let msg = payload.error || payload.detail || payload.message;
      if (!msg && typeof payload === 'object') {
        const firstVal = Object.values(payload)[0];
        msg = Array.isArray(firstVal) ? firstVal[0] : String(firstVal);
      }
      throw new HttpError(msg || `API error ${response.status}`, response.status, payload, isJson);
    }
    if (payload.access) localStorage.setItem('handsign_access_token', payload.access);
    else if (payload.token) localStorage.setItem('handsign_access_token', payload.token);
    return { ...payload, demo: Boolean(payload.demo) };
  } catch (error) {
    const staticHostMiss = error instanceof HttpError && demoFallbackEnabled() && !error.isJson && [404, 405, 501].includes(error.status);
    if (fallback !== undefined && (!(error instanceof HttpError) || staticHostMiss)) {
      console.info(`[HandSign demo] ${method} ${path}:`, error.message);
      return { ...(typeof fallback === 'function' ? fallback() : fallback), demo: true };
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export const Api = {
  getBaseUrl: apiBase,
  setBaseUrl(url) {
    const next = new URL(url, location.origin);
    const current = new URL(apiBase(), location.origin);
    const localDev = ['localhost','127.0.0.1','::1'].includes(next.hostname);
    if (next.protocol !== 'https:' && next.origin !== location.origin && !localDev) throw new Error('Use HTTPS for a remote API.');
    if (next.origin !== current.origin) localStorage.removeItem('handsign_access_token');
    localStorage.setItem('handsign_api_base', url.replace(/\/$/, ''));
  },
  async health() {
    return request('/health/', { timeout: 3500 });
  },
  async register(data) {
    localStorage.removeItem('handsign_access_token');
    return request('/auth/register/', {
      method: 'POST', body: data,
      fallback: { user: { name: data.name || 'Alex', email: data.email }, access: 'demo-token' }
    });
  },
  async login(data) {
    localStorage.removeItem('handsign_access_token');
    return request('/auth/login/', {
      method: 'POST', body: data,
      fallback: { user: { name: 'Alex', email: data.email }, access: 'demo-token' }
    });
  },
  async lessons() {
    return request('/lessons/', { fallback: { results: [] } });
  },
  async progress() {
    return request('/me/progress/', { fallback: { streak: 7, completed: 12, accuracy: 86 } });
  },
  async updateProfile(data) {
    return request('/me/', { method: 'PATCH', body: data, fallback: { user: data } });
  },
  async evaluateSign({ lesson, landmarks = [], faceMetrics = [], language = 'en' }) {
    return request('/practice/evaluate/', {
      method: 'POST', body: { lesson, landmarks, face_metrics: faceMetrics, language },
      fallback: { score: 86, feedback: 'Your hand shape looks right. Try raising your hand slightly closer to your temple.' }
    });
  },
  async translateClip({ clip, landmarks = [], durationMs, language = 'en' }) {
    const data = new FormData();
    if (clip?.size) data.append('clip', clip, clip.type.includes('mp4') ? 'gesture.mp4' : 'gesture.webm');
    data.append('landmarks', JSON.stringify(landmarks));
    data.append('duration_ms', String(durationMs));
    data.append('language', language);
    return request('/translate/', {
      method: 'POST', formData: data, timeout: 30000,
      fallback: { text: 'Hello, I would like some water, please.', confidence: 0.82 }
    });
  },
  async createCheckout() {
    return request('/billing/checkout/', {
      method: 'POST', body: { price_code: 'family_monthly' },
      fallback: { url: null }
    });
  },
  async getFriends() {
    return request('/friends/', { fallback: { friends: [], requests: [], suggestions: [] } });
  },
  async sendFriendRequest(usernameOrId) {
    const payload = typeof usernameOrId === 'number' ? { to_user_id: usernameOrId } : { username: usernameOrId };
    return request('/friends/request/', { method: 'POST', body: payload, fallback: { status: 'pending' } });
  },
  async respondToFriendRequest(friendshipId, action) {
    return request('/friends/respond/', { method: 'POST', body: { friendship_id: friendshipId, action }, fallback: { message: 'Friend request updated.' } });
  },
  async lessonDetail(id) {
    return request(`/lessons/${id}/`, { fallback: { reference_landmarks: [] } });
  }
};
