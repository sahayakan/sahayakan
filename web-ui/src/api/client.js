const API_URL = import.meta.env.VITE_API_URL || '/api';

async function request(path, options = {}) {
  const headers = { ...options.headers };
  if (options.body) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
};

export const WS_URL = API_URL.startsWith('http')
  ? API_URL.replace(/^http/, 'ws')
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${API_URL}`;
