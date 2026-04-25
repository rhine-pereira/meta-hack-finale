import { create } from "zustand";
import { 
  WorldState, 
  Employee, 
  Customer, 
  Investor, 
  Competitor, 
  PendingFeature, 
  PersonalCrisis, 
  RewardBreakdown, 
  GameEvent,
  FounderGenome,
  GenomeExport,
  ComparisonExport
} from "@/types/genesis";
import { genesisClient } from "./genesis-client";

interface GenesisStore {
  // Session
  episodeId: string | null;
  difficulty: number;
  seed: number;
  day: number;
  maxDays: number;
  isRunning: boolean;
  serverOnline: boolean;

  // Company State
  cash: number;
  mrr: number;
  valuation: number;
  burnRateDaily: number;
  equitySold: number;
  seriesAClosed: boolean;

  // Product
  productMaturity: number;
  techDebt: number;
  featuresShipped: number;
  uptime: number;
  pendingFeatures: PendingFeature[];

  // Team
  employees: Employee[];
  candidatePool: any[];
  pendingHires: any[];
  cofounderMorale: Record<string, number>;
  cofounderAlignment: number;

  // Market
  customers: Customer[];
  investors: Investor[];
  competitors: Competitor[];

  // Reward
  currentReward: RewardBreakdown | null;
  rewardHistory: number[];

  // Events
  eventLog: GameEvent[];

  // Crises
  personalCrises: PersonalCrisis[];

  // Company Brain
  companyBrain: Record<string, string>;

  // Pivot
  pivotCount: number;
  pivotInProgress: boolean;
  pivotDirection: string | null;

  // Blockchain / Proof
  lastSignature: string | null;
  leafCount: number;
  checkpointIndex: number;
  isSolanaConfigured: boolean;

  // Founder Genome (USP 3)
  modelId: string | null;
  genomes: Record<string, FounderGenome>;
  comparison: ComparisonExport | null;

  // Actions
  setServerOnline: (online: boolean) => void;
  reset: (difficulty: number, seed: number, modelId?: string) => Promise<void>;
  advanceDay: () => Promise<void>;
  fetchState: () => Promise<void>;
  fetchReward: () => Promise<void>;
  commitProof: () => Promise<void>;
  fetchProofStatus: () => Promise<void>;
  
  // Genome Actions
  exportGenome: (modelId: string) => Promise<GenomeExport>;
  compareGenomes: (modelIds: string[]) => Promise<ComparisonExport>;
  
  // Helpers
  runwayDays: () => number;
}

export const useGenesisStore = create<GenesisStore>((set, get) => ({
  // Initial State
  episodeId: null,
  difficulty: 4,
  seed: 42,
  day: 0,
  maxDays: 540,
  isRunning: false,
  serverOnline: false,

  cash: 0,
  mrr: 0,
  valuation: 0,
  burnRateDaily: 0,
  equitySold: 0,
  seriesAClosed: false,

  productMaturity: 0,
  techDebt: 0,
  featuresShipped: 0,
  uptime: 0.99,
  pendingFeatures: [],

  employees: [],
  candidatePool: [],
  pendingHires: [],
  cofounderMorale: {},
  cofounderAlignment: 0.8,

  customers: [],
  investors: [],
  competitors: [],

  currentReward: null,
  rewardHistory: [],
  eventLog: [],
  personalCrises: [],
  companyBrain: {},

  pivotCount: 0,
  pivotInProgress: false,
  pivotDirection: null,

  lastSignature: null,
  leafCount: 0,
  checkpointIndex: 0,
  isSolanaConfigured: false,

  modelId: null,
  genomes: {},
  comparison: null,

  // Actions
  setServerOnline: (online) => set({ serverOnline: online }),

  reset: async (difficulty, seed, modelId = "genesis-alpha") => {
    const episodeId = `ep-${Math.random().toString(36).substring(2, 9)}`;
    try {
      const result = await genesisClient.callTool("reset", { 
        episode_id: episodeId, 
        difficulty, 
        seed,
        model_id: modelId
      });
      
      set({
        episodeId,
        difficulty,
        seed,
        modelId,
        day: result.day,
        maxDays: result.max_days,
        cash: result.cash,
        mrr: result.mrr,
        isRunning: true,
        eventLog: [{ day: 0, text: result.message, type: "special" }]
      });

      await get().fetchState();
      await get().fetchReward();
      await get().fetchProofStatus();
    } catch (error) {
      console.error("Reset failed:", error);
    }
  },

  advanceDay: async () => {
    const { episodeId, eventLog } = get();
    if (!episodeId) return;

    try {
      // Advance by calling briefing for CEO (this ticks the world in the backend)
      const result = await genesisClient.callTool("get_daily_briefing", { 
        episode_id: episodeId, 
        agent_role: "ceo" 
      });

      const newEvents: GameEvent[] = (result.world_events || []).map((text: string) => ({
        day: result.day,
        text,
        type: text.includes("🚀") || text.includes("📈") || text.includes("🎉") ? "positive" :
              text.includes("🔥") || text.includes("📉") || text.includes("Resigned") ? "negative" :
              text.includes("🆘") || text.includes("⚔️") ? "warning" : "neutral"
      }));

      set({
        day: result.day,
        eventLog: [...newEvents, ...eventLog].slice(0, 200), // Keep last 200
        isRunning: !result.is_done
      });

      await get().fetchState();
      await get().fetchReward();
      await get().fetchProofStatus();
    } catch (error) {
      console.error("Advance day failed:", error);
    }
  },

  fetchState: async () => {
    const { episodeId } = get();
    if (!episodeId) return;

    try {
      // Since states are partially observable, we merge views from multiple roles
      // For the UI, we ideally want the "God view" but the backend tools are role-filtered.
      // We'll call for CEO and CFO which combined cover most financial/strategic info.
      const ceoView = await genesisClient.callTool("get_company_state", { episode_id: episodeId, agent_role: "ceo" });
      const cfoView = await genesisClient.callTool("get_company_state", { episode_id: episodeId, agent_role: "cfo" });
      const ctoView = await genesisClient.callTool("get_company_state", { episode_id: episodeId, agent_role: "cto" });
      const peopleView = await genesisClient.callTool("get_company_state", { episode_id: episodeId, agent_role: "people" });

      set({
        cash: cfoView.cash ?? get().cash,
        mrr: cfoView.mrr ?? get().mrr,
        valuation: cfoView.valuation ?? ceoView.valuation ?? get().valuation,
        burnRateDaily: cfoView.burn_rate_daily ?? get().burn_rate_daily,
        equitySold: cfoView.equity_sold ?? get().equity_sold,
        seriesAClosed: ceoView.series_a_closed ?? get().series_a_closed,
        
        productMaturity: ctoView.product_maturity ?? get().product_maturity,
        techDebt: ctoView.tech_debt ?? get().tech_debt,
        uptime: ctoView.uptime ?? get().uptime,
        pendingFeatures: ctoView.pending_features ?? get().pendingFeatures,
        featuresShipped: ctoView.features_shipped ?? get().featuresShipped,

        employees: peopleView.employees ?? ctoView.employees ?? get().employees,
        candidatePool: peopleView.candidate_pool ?? get().candidatePool,
        cofunderMorale: peopleView.cofounder_morale ?? ceoView.cofounder_morale ?? get().cofounderMorale,
        cofunderAlignment: peopleView.cofounder_alignment ?? get().cofounderAlignment,

        customers: ceoView.customers ?? get().customers,
        investors: ceoView.investors ?? get().investors,
        competitors: ceoView.competitors ?? get().competitors,

        companyBrain: ceoView.company_brain ?? get().companyBrain,
        personalCrises: ceoView.personal_crises ?? get().personalCrises,

        pivotCount: ceoView.pivot_count ?? get().pivotCount,
        pivotInProgress: ceoView.pivot_in_progress ?? get().pivotInProgress,
        pivotDirection: ceoView.pivot_direction ?? get().pivotDirection,
      });
    } catch (error) {
      console.error("Fetch state failed:", error);
    }
  },

  fetchReward: async () => {
    const { episodeId, rewardHistory } = get();
    if (!episodeId) return;

    try {
      const result = await genesisClient.callTool("get_reward", { episode_id: episodeId });
      set({
        currentReward: result.breakdown,
        rewardHistory: [...rewardHistory, result.reward]
      });
    } catch (error) {
      console.error("Fetch reward failed:", error);
    }
  },

  commitProof: async () => {
    const { episodeId } = get();
    if (!episodeId) return;

    try {
      const result = await genesisClient.callTool("commit_simulation_proof", { episode_id: episodeId });
      if (result.success) {
        await get().fetchProofStatus();
      } else {
        console.error("Commit proof failed:", result.error);
      }
    } catch (error) {
      console.error("Commit proof error:", error);
    }
  },

  fetchProofStatus: async () => {
    const { episodeId } = get();
    if (!episodeId) return;

    try {
      const result = await genesisClient.callTool("get_simulation_proof_status", { episode_id: episodeId });
      set({
        lastSignature: result.last_signature,
        leafCount: result.leaf_count,
        checkpointIndex: result.last_checkpoint_index,
        isSolanaConfigured: result.is_solana_configured
      });
    } catch (error) {
      console.error("Fetch proof status failed:", error);
    }
  },

  exportGenome: async (modelId: string) => {
    try {
      const result = await genesisClient.callTool("export_founder_genome", { model_id: modelId });
      set((state) => ({
        genomes: { ...state.genomes, [modelId]: result.genome }
      }));
      return result;
    } catch (error) {
      console.error("Export genome failed:", error);
      throw error;
    }
  },

  compareGenomes: async (modelIds: string[]) => {
    try {
      const result = await genesisClient.callTool("compare_founder_genomes", { model_ids: modelIds });
      set({ comparison: result });
      return result;
    } catch (error) {
      console.error("Compare genomes failed:", error);
      throw error;
    }
  },

  runwayDays: () => {
    const { cash, mrr, burnRateDaily } = get();
    const dailyRevenue = mrr / 30.0;
    const netBurn = burnRateDaily - dailyRevenue;
    if (netBurn <= 0) return Infinity;
    return Math.floor(cash / netBurn);
  }
}));
