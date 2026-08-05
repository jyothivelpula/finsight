import api from "./client";
import type {
  AIChatResponse,
  AnalyticsDashboard,
  Budget,
  Category,
  Expense,
  Goal,
  Income,
  ReportResponse,
  TokenResponse,
  User,
} from "../types";

export const authApi = {
  register: (body: { email: string; full_name: string; password: string }) =>
    api.post<User>("/api/auth/register", body).then((r) => r.data),
  login: (body: { email: string; password: string }) =>
    api.post<TokenResponse>("/api/auth/login/json", body).then((r) => r.data),
  me: () => api.get<User>("/api/auth/me").then((r) => r.data),
  logout: () => api.post("/api/auth/logout").then((r) => r.data),
};

export const financeApi = {
  categories: () => api.get<Category[]>("/api/finance/categories").then((r) => r.data),
  createCategory: (body: { name: string; type?: string }) =>
    api.post<Category>("/api/finance/categories", body).then((r) => r.data),

  incomes: (params?: Record<string, string | number>) =>
    api.get<Income[]>("/api/finance/income", { params }).then((r) => r.data),
  createIncome: (body: object) =>
    api.post<Income>("/api/finance/income", body).then((r) => r.data),
  updateIncome: (id: number, body: object) =>
    api.put<Income>(`/api/finance/income/${id}`, body).then((r) => r.data),
  deleteIncome: (id: number) => api.delete(`/api/finance/income/${id}`),

  expenses: (params?: Record<string, string | number>) =>
    api.get<Expense[]>("/api/finance/expenses", { params }).then((r) => r.data),
  createExpense: (body: object) =>
    api.post<Expense>("/api/finance/expenses", body).then((r) => r.data),
  updateExpense: (id: number, body: object) =>
    api.put<Expense>(`/api/finance/expenses/${id}`, body).then((r) => r.data),
  deleteExpense: (id: number) => api.delete(`/api/finance/expenses/${id}`),

  budgets: (year: number, month: number) =>
    api.get<Budget[]>("/api/finance/budgets", { params: { year, month } }).then((r) => r.data),
  createBudget: (body: object) =>
    api.post<Budget>("/api/finance/budgets", body).then((r) => r.data),
  updateBudget: (id: number, body: object) =>
    api.put<Budget>(`/api/finance/budgets/${id}`, body).then((r) => r.data),
  deleteBudget: (id: number) => api.delete(`/api/finance/budgets/${id}`),

  goals: () => api.get<Goal[]>("/api/finance/goals").then((r) => r.data),
  createGoal: (body: object) =>
    api.post<Goal>("/api/finance/goals", body).then((r) => r.data),
  updateGoal: (id: number, body: object) =>
    api.put<Goal>(`/api/finance/goals/${id}`, body).then((r) => r.data),
  deleteGoal: (id: number) => api.delete(`/api/finance/goals/${id}`),
};

export const analyticsApi = {
  dashboard: (year?: number, month?: number) =>
    api
      .get<AnalyticsDashboard>("/api/analytics/dashboard", { params: { year, month } })
      .then((r) => r.data),
};

export const aiApi = {
  ask: (
    question: string,
    history?: { role: "user" | "assistant"; content: string }[],
    year?: number,
    month?: number,
  ) =>
    api
      .post<AIChatResponse>(
        "/api/ai/ask",
        { question, history: history ?? [] },
        { params: { year, month } },
      )
      .then((r) => r.data),
};

export const reportsApi = {
  generate: (body: {
    report_type: string;
    year: number;
    month?: number;
    format: string;
  }) => api.post<ReportResponse>("/api/reports/generate", body).then((r) => r.data),
  downloadUrl: (path: string) =>
    `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${path}`,
};
