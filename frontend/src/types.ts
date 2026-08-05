export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  role: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Category {
  id: number;
  name: string;
  type: string;
  is_default: boolean;
}

export interface Income {
  id: number;
  source: string;
  amount: string | number;
  description: string | null;
  income_date: string;
  created_at: string;
}

export interface Expense {
  id: number;
  category_id: number;
  amount: string | number;
  description: string | null;
  merchant: string | null;
  expense_date: string;
  created_at: string;
}

export interface Budget {
  id: number;
  category_id: number;
  amount: string | number;
  year: number;
  month: number;
  spent: string | number;
  remaining: string | number;
  utilization: number;
  status: string;
}

export interface Goal {
  id: number;
  name: string;
  target_amount: string | number;
  current_amount: string | number;
  target_date: string | null;
  status: string;
  notes: string | null;
  completion_percentage: number;
  remaining_amount: string | number;
}

export interface FinancialSummary {
  total_income: string | number;
  total_expenses: string | number;
  net_savings: string | number;
  savings_rate: number;
  budget_usage: number;
  financial_health_score: number;
}

export interface CategoryAmount {
  category: string;
  amount: string | number;
  percentage: number;
}

export interface MonthlyPoint {
  period: string;
  income: string | number;
  expenses: string | number;
  savings: string | number;
}

export interface BudgetAnalyticsItem {
  category: string;
  budget: string | number;
  spent: string | number;
  remaining: string | number;
  utilization: number;
  status: string;
}

export interface GoalProgressItem {
  name: string;
  target_amount: string | number;
  current_amount: string | number;
  completion_percentage: number;
  status: string;
}

export interface AnalyticsDashboard {
  summary: FinancialSummary;
  income_by_source: CategoryAmount[];
  expense_by_category: CategoryAmount[];
  monthly_trends: MonthlyPoint[];
  budget_analytics: BudgetAnalyticsItem[];
  goal_progress: GoalProgressItem[];
  insights: string[];
  health_breakdown: Record<string, number>;
}

export interface AIChatResponse {
  answer: string;
  insights: string[];
  context_summary: Record<string, unknown>;
}

export interface ReportResponse {
  filename: string;
  download_path: string;
  report_type: string;
  format: string;
}
