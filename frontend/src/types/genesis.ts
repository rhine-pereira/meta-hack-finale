export interface Employee {
  id: string;
  name: string;
  role: string;
  skill_level: number;    // 0-1
  morale: number;         // 0-1
  burnout_risk: number;   // 0-1
  is_toxic: boolean;
  annual_salary: number;
  months_employed: number;
  flight_risk: number;    // 0-1
}

export interface Customer {
  id: string;
  name: string;
  arr: number;
  satisfaction: number;   // 0-1
  churn_risk: number;     // 0-1
  wants_feature: string | null;
  months_active: number;
}

export interface Investor {
  id: string;
  name: string;
  thesis: string;
  check_size_min: number;
  check_size_max: number;
  sentiment: number;      // 0-1
  has_term_sheet: boolean;
  term_sheet_valuation: number | null;
  term_sheet_equity: number | null;
}

export interface Competitor {
  id: string;
  name: string;
  strength: number;       // 0-1
  funding: number;
  recent_move: string | null;
}

export interface PendingFeature {
  name: string;
  complexity: "low" | "medium" | "high";
  engineers_assigned: number;
  days_remaining: number;
  tech_debt_added: number;
}

export interface PersonalCrisis {
  id: string;
  target_role: string;
  description: string;
  severity: number;       // 0-1
  resolved: boolean;
  injected_day: number;
  ignored: boolean;
  resolution_quality: number;
}

export interface RewardBreakdown {
  company_valuation: number;
  series_a_success: number;
  runway_management: number;
  product_velocity: number;
  customer_retention: number;
  team_morale: number;
  cofounder_alignment: number;
  personal_crisis_handling: number;
  decision_coherence: number;
  company_brain_quality: number;
  pivot_execution: number;
  total: number;
}

export interface GameEvent {
  day: number;
  text: string;
  type: "positive" | "negative" | "warning" | "special" | "neutral";
}

export interface WorldState {
  day: number;
  episode_id: string;
  difficulty: string;
  max_days: number;
  cash: number;
  mrr: number;
  valuation: number;
  burn_rate_daily: number;
  equity_sold: number;
  series_a_closed: boolean;
  product_maturity: number;
  tech_debt: number;
  features_shipped: number;
  uptime: number;
  pending_features: PendingFeature[];
  employees: Employee[];
  customers: Customer[];
  investors: Investor[];
  competitors: Competitor[];
  company_brain: Record<string, string>;
  personal_crises: PersonalCrisis[];
  cofounder_morale: Record<string, number>;
  cofounder_alignment: number;
  pivot_count: number;
  pivot_in_progress: boolean;
  pivot_direction: string | null;
  model_id: string | null;
  reward_breakdown_history: RewardBreakdown[];
}

export interface FounderGenome {
  profile: Record<string, number>;
  metadata: {
    episode_count: number;
    avg_difficulty: number;
    avg_days_survived: number;
    strengths: string[];
    weaknesses: string[];
    timestamp: string;
  };
}

export interface GenomeExport {
  model_id: string;
  genome: FounderGenome;
  artifacts: {
    json: string;
    png: string;
  };
}

export type AgentRoleId = "ceo" | "cto" | "sales" | "people" | "cfo";
export type RoleController = "ai" | "human";

export interface HumanActionEntry {
  day: number;
  role: string;
  action: string;
  details: string | Record<string, unknown>;
}

export interface ComparisonExport {
  compared_models: string[];
  comparison: Record<string, FounderGenome>;
  artifacts: {
    png: string;
  };
}
