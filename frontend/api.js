// Trade-Claw API Client — spricht gegen FastAPI Backend (app/main.py)

const STORAGE_KEYS = {
  baseUrl: 'tc.baseUrl',
  apiKey: 'tc.apiKey',
  sessionId: 'tc.sessionId',
  environment: 'tc.environment',
  brokerType: 'tc.brokerType',
};

// When the frontend is served from the same FastAPI app (the default
// deployment via the launcher), the API lives at the same origin. We pick
// that automatically so the user does not have to set anything by hand.
const _defaultBaseUrl = (() => {
  if (typeof location !== 'undefined' && location.origin && location.origin.startsWith('http')) {
    return location.origin;
  }
  return 'http://localhost:8000';
})();

const Config = {
  get baseUrl() { return localStorage.getItem(STORAGE_KEYS.baseUrl) || _defaultBaseUrl; },
  set baseUrl(v) { localStorage.setItem(STORAGE_KEYS.baseUrl, v); },
  get apiKey()  { return localStorage.getItem(STORAGE_KEYS.apiKey) || ''; },
  set apiKey(v) { localStorage.setItem(STORAGE_KEYS.apiKey, v); },
  get sessionId(){ return localStorage.getItem(STORAGE_KEYS.sessionId) || ''; },
  set sessionId(v){ localStorage.setItem(STORAGE_KEYS.sessionId, v); },
  get environment(){ return localStorage.getItem(STORAGE_KEYS.environment) || 'paper'; },
  set environment(v){ localStorage.setItem(STORAGE_KEYS.environment, v); },
  get brokerType(){ return localStorage.getItem(STORAGE_KEYS.brokerType) || ''; },
  set brokerType(v){ localStorage.setItem(STORAGE_KEYS.brokerType, v); },
  clear() { Object.values(STORAGE_KEYS).forEach(k => localStorage.removeItem(k)); },
  isReady() { return !!this.apiKey && !!this.sessionId; },
};

class ApiError extends Error {
  constructor(status, message, data) {
    super(message); this.status = status; this.data = data;
  }
}

async function request(path, { method = 'GET', body, query, auth = true, signal } = {}) {
  const url = new URL(path, Config.baseUrl);
  if (query) Object.entries(query).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const headers = { 'Content-Type': 'application/json' };
  if (auth && Config.apiKey) headers['X-API-Key'] = Config.apiKey;
  let res;
  try {
    res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined, signal });
  } catch (e) {
    throw new ApiError(0, `Network error: ${e.message} (CORS? Backend offline?)`, null);
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
  if (!res.ok) {
    const msg = (data && (data.error || data.detail)) || res.statusText || `HTTP ${res.status}`;
    throw new ApiError(res.status, typeof msg === 'string' ? msg : JSON.stringify(msg), data);
  }
  return data;
}

const Api = {
  // Health & Info
  health() { return request('/health', { auth: false }); },

  // Broker setup
  setupBroker({ broker_type, credentials, user_id, environment }) {
    return request('/api/v1/brokers/setup', {
      method: 'POST',
      body: { broker_type, credentials, user_id, environment: environment || 'paper' },
    });
  },

  // Quotes
  getQuote(symbol, amount) {
    const sid = Config.sessionId;
    return request(`/api/v1/brokers/${encodeURIComponent(sid)}/quote`, {
      query: { symbol, amount },
    });
  },

  // Orders
  submitOrder({ symbol, side, size, entry_price, stop_loss, take_profit, idempotency_key }) {
    return request('/api/v1/orders/submit', {
      method: 'POST',
      query: { session_id: Config.sessionId },
      body: { symbol, side, size, entry_price, stop_loss, take_profit, idempotency_key },
    });
  },
  getOrder(order_id) {
    return request(`/api/v1/orders/${encodeURIComponent(order_id)}`, {
      query: { session_id: Config.sessionId },
    });
  },
  cancelOrder(order_id) {
    return request(`/api/v1/orders/${encodeURIComponent(order_id)}/cancel`, {
      method: 'POST', query: { session_id: Config.sessionId },
    });
  },

  // Positions
  getPositions() {
    return request('/api/v1/positions', { query: { session_id: Config.sessionId } });
  },

  // Audit
  getAudit({ action, severity, limit = 50, offset = 0 } = {}) {
    return request('/api/v1/audit', {
      query: { session_id: Config.sessionId, action, severity, limit, offset },
    });
  },

  // Emergency halt — cancels every open order and flips the session to halted
  haltSession() {
    return request('/api/v1/halt', {
      method: 'POST', query: { session_id: Config.sessionId },
    });
  },

  // Phase 2 — Risk (no auth required server-side)
  riskStatus() { return request('/api/risk/status', { auth: false }); },
  preTradeCheck(payload) {
    return request('/api/risk/pre-trade-check', { method: 'POST', body: payload, auth: false });
  },

  // Backtest
  runBacktest(payload) {
    return request('/api/backtest', { method: 'POST', body: payload, auth: false });
  },

  // Correlation
  correlationAssets() {
    return request('/api/v1/correlation/assets', { auth: false });
  },
  correlationAnalyze({ asset_prices, threshold = 0.7 }) {
    return request('/api/v1/correlation/analyze', {
      method: 'POST', body: { asset_prices, threshold }, auth: false,
    });
  },

  // Macro events
  macroEvents({ category, limit = 50 } = {}) {
    return request('/api/v1/macro/events', {
      query: { category, limit }, auth: false,
    });
  },
  macroUpcoming({ hours = 72 } = {}) {
    return request('/api/v1/macro/upcoming', { query: { hours }, auth: false });
  },

  // Trade-grader
  gradeSetup(payload) {
    return request('/api/v1/ml/grade', { method: 'POST', body: payload, auth: false });
  },
};

// Polling helper — best practice: 5s for snapshot endpoints, with backoff on errors
function makePoller(fn, { interval = 5000, onData, onError } = {}) {
  let stopped = false; let timer = null; let backoff = interval;
  async function tick() {
    if (stopped) return;
    try {
      const data = await fn();
      backoff = interval;
      onData && onData(data);
    } catch (e) {
      backoff = Math.min(backoff * 2, 30000);
      onError && onError(e);
    } finally {
      if (!stopped) timer = setTimeout(tick, backoff);
    }
  }
  tick();
  return () => { stopped = true; if (timer) clearTimeout(timer); };
}

function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

Object.assign(window, { Api, ApiError, Config, makePoller, uuid });
