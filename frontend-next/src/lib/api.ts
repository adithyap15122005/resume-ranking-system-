import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import Cookies from "js-cookie";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

// ── Request: attach Bearer token ─────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = Cookies.get("access_token") || localStorage.getItem("access_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response: handle 401 refresh flow ────────────────────────────────────────
let isRefreshing = false;
let failedQueue: Array<{ resolve: (v: unknown) => void; reject: (e: unknown) => void }> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }
      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = Cookies.get("refresh_token") || localStorage.getItem("refresh_token");
      if (!refreshToken) {
        isRefreshing = false;
        if (typeof window !== "undefined") window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${API_URL}/api/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const { access_token, refresh_token: newRefresh } = data;
        Cookies.set("access_token", access_token, { expires: 1 });
        Cookies.set("refresh_token", newRefresh, { expires: 7 });
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", newRefresh);
        api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
        processQueue(null, access_token);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        Cookies.remove("access_token");
        Cookies.remove("refresh_token");
        localStorage.clear();
        if (typeof window !== "undefined") window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  signup: (data: {
    email: string;
    username: string;
    full_name: string;
    password: string;
    role?: string;
    organization_name?: string;
  }) => api.post("/api/auth/signup", data).then((r) => r.data),

  login: (email: string, password: string) =>
    api.post("/api/auth/login", { email, password }).then((r) => r.data),

  refresh: (refresh_token: string) =>
    api.post("/api/auth/refresh", { refresh_token }).then((r) => r.data),

  logout: () => api.post("/api/auth/logout").then((r) => r.data),

  me: () => api.get("/api/auth/me").then((r) => r.data),

  updateProfile: (data: { full_name?: string; avatar_url?: string }) =>
    api.put("/api/auth/me", data).then((r) => r.data),

  forgotPassword: (email: string) =>
    api.post("/api/auth/forgot-password", { email }).then((r) => r.data),

  resetPassword: (token: string, new_password: string) =>
    api.post("/api/auth/reset-password", { token, new_password }).then((r) => r.data),

  verifyEmail: (token: string) =>
    api.post(`/api/auth/verify-email?token=${token}`).then((r) => r.data),
};

// ── Resumes ───────────────────────────────────────────────────────────────────
export const resumeApi = {
  upload: (
    files: File[],
    onProgress?: (pct: number) => void
  ) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return api
      .post("/api/resumes/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
        },
      })
      .then((r) => r.data);
  },

  list: (params?: { page?: number; page_size?: number; search?: string; pinned_only?: boolean }) =>
    api.get("/api/resumes/", { params }).then((r) => r.data),

  get: (id: string) => api.get(`/api/resumes/${id}`).then((r) => r.data),

  delete: (id: string) => api.delete(`/api/resumes/${id}`),

  pin: (id: string) => api.put(`/api/resumes/${id}/pin`).then((r) => r.data),

  updateNotes: (id: string, notes: string) =>
    api.put(`/api/resumes/${id}/notes`, { notes }).then((r) => r.data),

  getIntelligence: (id: string) =>
    api.get(`/api/resumes/${id}/intelligence`).then((r) => r.data),

  search: (q: string, top_k = 10) =>
    api.get("/api/resumes/search/semantic", { params: { q, top_k } }).then((r) => r.data),
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobApi = {
  create: (data: {
    title: string;
    description: string;
    department?: string;
    location?: string;
    employment_type?: string;
    experience_level?: string;
    salary_min?: number;
    salary_max?: number;
    required_skills?: string[];
    preferred_skills?: string[];
    experience_requirement?: string;
    education_requirement?: string;
  }) => api.post("/api/jobs/", data).then((r) => r.data),

  list: (status?: string) =>
    api.get("/api/jobs/", { params: status ? { status } : {} }).then((r) => r.data),

  get: (id: string) => api.get(`/api/jobs/${id}`).then((r) => r.data),

  update: (id: string, data: Record<string, unknown>) =>
    api.put(`/api/jobs/${id}`, data).then((r) => r.data),

  delete: (id: string) => api.delete(`/api/jobs/${id}`),

  rank: (id: string, minScore = 0) =>
    api.post(`/api/jobs/${id}/rank`, null, { params: { min_score: minScore } }).then((r) => r.data),

  getRankings: (id: string) =>
    api.get(`/api/jobs/${id}/rankings`).then((r) => r.data),

  movePipeline: (jobId: string, resumeId: string, pipeline_stage: string) =>
    api.put(`/api/jobs/${jobId}/pipeline/${resumeId}`, { pipeline_stage }).then((r) => r.data),

  getAnalytics: (id: string) => api.get(`/api/jobs/${id}/analytics`).then((r) => r.data),
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analyticsApi = {
  dashboard: () => api.get("/api/analytics/dashboard").then((r) => r.data),
  hiringFunnel: () => api.get("/api/analytics/hiring-funnel").then((r) => r.data),
  skillDemand: () => api.get("/api/analytics/skill-demand").then((r) => r.data),
  candidateDistribution: () =>
    api.get("/api/analytics/candidate-distribution").then((r) => r.data),
  modelPerformance: () => api.get("/api/analytics/model-performance").then((r) => r.data),
};

// ── Training ──────────────────────────────────────────────────────────────────
export const trainingApi = {
  // Step 1: Dataset Upload
  uploadDataset: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post("/api/training/datasets/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
        },
      })
      .then((r) => r.data);
  },

  listDatasets: () => api.get("/api/training/datasets").then((r) => r.data),
  getDataset: (id: string) => api.get(`/api/training/datasets/${id}`).then((r) => r.data),

  // Step 2: EDA
  analyzeDataset: (datasetId: string) =>
    api.post(`/api/training/datasets/${datasetId}/analyze`).then((r) => r.data),

  // Step 3: Feature Engineering
  engineerFeatures: (datasetId: string, targetColumn: string) =>
    api.post(`/api/training/datasets/${datasetId}/engineer`, null, {
      params: { target_column: targetColumn },
    }).then((r) => r.data),

  // Step 4: Training
  startExperiment: (body: {
    dataset_id: string;
    name: string;
    target_column: string;
    algorithms?: string[];
    feature_columns?: string[];
  }) => api.post("/api/training/experiments", body).then((r) => r.data),

  getExperiment: (experimentId: string) =>
    api.get(`/api/training/experiments/${experimentId}`).then((r) => r.data),

  listExperiments: () => api.get("/api/training/experiments").then((r) => r.data),

  // Step 5: Model Leaderboard & Deployment
  listModels: () => api.get("/api/training/models").then((r) => r.data),
  getProductionModel: () => api.get("/api/training/models/production").then((r) => r.data),
  deployModel: (modelId: string) =>
    api.post(`/api/training/models/${modelId}/deploy`).then((r) => r.data),
  setExperimental: (modelId: string) =>
    api.post(`/api/training/models/${modelId}/set-experimental`).then((r) => r.data),
  deleteModel: (modelId: string) =>
    api.delete(`/api/training/models/${modelId}`).then((r) => r.data),

  // Continuous Learning
  recordOutcome: (body: {
    resume_id: string;
    job_id: string;
    ranking_result_id?: string;
    interview_score?: number;
    hiring_decision: string;
    offer_extended?: boolean;
    offer_accepted?: boolean;
    notes?: string;
  }) => api.post("/api/training/outcomes", body).then((r) => r.data),
  listOutcomes: () => api.get("/api/training/outcomes").then((r) => r.data),

  // Legacy (keep for compatibility)
  datasets: () => api.get("/api/training/datasets").then((r) => r.data),
};

// ── Chat ──────────────────────────────────────────────────────────────────────
export const chatApi = {
  send: (body: { message: string; job_id?: string; resume_id?: string; session_id?: string }) =>
    api.post("/api/chat/", body).then((r) => r.data),
  history: (session_id: string) =>
    api.get("/api/chat/history", { params: { session_id } }).then((r) => r.data),
};

export default api;
