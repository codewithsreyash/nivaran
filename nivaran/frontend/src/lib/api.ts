import axios from 'axios';

// Dynamically determine backend URL via environment variable or default to localhost
const getBaseURL = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (typeof window !== 'undefined' && window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000';
  }
  return 'http://localhost:8000';
};

const api = axios.create({
  baseURL: getBaseURL(),
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    // Only redirect if not already on the login page / attempting login
    const isLoginRequest = err.config?.url?.includes('/api/auth/login');
    if (err.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authAPI = {
  login: (username: string, password: string) => {
    const params = new URLSearchParams({ username, password });
    return api.post('/api/auth/login', params, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
  },
  logout: () => api.post('/api/auth/logout'),
  me: () => api.get('/api/auth/me'),
};

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const dashboardAPI = {
  get: (signal?: AbortSignal) => api.get('/api/dashboard', { signal }),
};

// ── Institutions ──────────────────────────────────────────────────────────────
export const institutionsAPI = {
  list: (params?: Record<string, any>) => api.get('/api/institutions', { params }),
  get: (id: number) => api.get(`/api/institutions/${id}`),
  create: (data: any) => api.post('/api/institutions', data),
  update: (id: number, data: any) => api.patch(`/api/institutions/${id}`, data),
};

// ── Complaints ────────────────────────────────────────────────────────────────
export const complaintsAPI = {
  list: (params?: Record<string, any>, signal?: AbortSignal) => api.get('/api/complaints', { params, signal }),
  get: (id: number) => api.get(`/api/complaints/${id}`),
  create: (data: any) => api.post('/api/complaints', data),
  update: (id: number, data: any) => api.patch(`/api/complaints/${id}`, data),
  transfer: (id: number, data: any) => api.post(`/api/complaints/${id}/transfer`, data),
  addAction: (id: number, data: any) => api.post(`/api/complaints/${id}/actions`, data),
  getActions: (id: number) => api.get(`/api/complaints/${id}/actions`),
  detectOverlaps: (id: number) => api.post(`/api/complaints/${id}/detect-overlaps`),
  getOverlaps: (id: number) => api.get(`/api/complaints/${id}/overlaps`),
  calculatePriority: (id: number) => api.post(`/api/complaints/${id}/calculate-priority`),
  priorityHistory: (id: number) => api.get(`/api/complaints/${id}/priority-history`),
  priorityOverride: (id: number, data: any) => api.post(`/api/complaints/${id}/priority-override`, data),
  assess: (id: number) => api.post(`/api/complaints/${id}/assess`),
  getAssessment: (id: number) => api.get(`/api/complaints/${id}/assessment`),
  addClarification: (id: number, data: any) => api.post(`/api/complaints/${id}/clarifications`, data),
  getAssignments: (id: number) => api.get(`/api/complaints/${id}/assignments`),
  reassign: (id: number, data: any) => api.post(`/api/complaints/${id}/reassign`, data),
  getInactivityWarnings: (id: number) => api.get(`/api/complaints/${id}/inactivity-warnings`),
};

// ── Priority Queue ────────────────────────────────────────────────────────────
export const priorityAPI = {
  queue: (params?: Record<string, any>) => api.get('/api/priority-queue', { params }),
};

// ── Overlaps ──────────────────────────────────────────────────────────────────
export const overlapsAPI = {
  list: (params?: Record<string, any>) => api.get('/api/overlaps', { params }),
  decision: (id: number, data: any) => api.post(`/api/overlaps/${id}/decision`, data),
};

// ── Deadlines / Notifications ─────────────────────────────────────────────────
export const deadlinesAPI = {
  get: () => api.get('/api/deadlines'),
};

export const notificationsAPI = {
  list: (params?: Record<string, any>, signal?: AbortSignal) => api.get('/api/notifications', { params, signal }),
  markRead: (id: number) => api.patch(`/api/notifications/${id}/read`),
};

// ── Users ─────────────────────────────────────────────────────────────────────
export const usersAPI = {
  list: () => api.get('/api/users'),
  create: (data: any) => api.post('/api/users', data),
  update: (id: number, data: any) => api.patch(`/api/users/${id}`, data),
};

// ── Bureaus ───────────────────────────────────────────────────────────────────
export const bureausAPI = {
  list: () => api.get('/api/bureaus'),
};

// ── Audit ─────────────────────────────────────────────────────────────────────
export const auditAPI = {
  list: (params?: Record<string, any>) => api.get('/api/audit-logs', { params }),
};

// ── Reports ───────────────────────────────────────────────────────────────────
export const reportsAPI = {
  complaints: (params?: Record<string, any>) => api.get('/api/reports/complaints', { params }),
  priority: (params?: Record<string, any>) => api.get('/api/reports/priority', { params }),
  export: (format: 'csv' | 'json' = 'csv', params?: Record<string, any>) =>
    api.get('/api/reports/export', {
      params: { format, ...params },
      responseType: format === 'csv' ? 'blob' : 'json',
    }),
};

// ── Inactivity Monitoring ─────────────────────────────────────────────────────
export const inactivityAPI = {
  getWarnings: (params?: Record<string, any>) => api.get('/api/inactivity/warnings', { params }),
  getExceptions: (params?: Record<string, any>) => api.get('/api/inactivity/exceptions', { params }),
  triggerMonitor: () => api.post('/api/inactivity/trigger-monitor'),
};

// ── Relationship Graph ─────────────────────────────────────────────────────────
export const graphAPI = {
  get: (params?: Record<string, any>) => api.get('/api/graph', { params }),
  getAnalytics: () => api.get('/api/graph/analytics'),
};

export default api;
