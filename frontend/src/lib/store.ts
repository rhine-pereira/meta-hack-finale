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
  ComparisonExport,
  AgentRoleId,
  RoleController,
  HumanActionEntry
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
  genomeExports: Record<string, GenomeExport>;
  comparison: ComparisonExport | null;
  availableModels: string[];
  
  // Ghost Founder (USP 2 — Human-in-the-Loop Takeover)
  roleControllers: Record<AgentRoleId, RoleController>;
  ghostActiveRole: AgentRoleId | null;       // role whose console is open
  humanActionLog: HumanActionEntry[];
  ghostBriefings: Partial<Record<AgentRoleId, any>>;

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
  listFounderGenomes: () => Promise<string[]>;
  
  // New Domain Actions
  buildFeature: (name: string, complexity: string, engineers: number) => Promise<void>;
  analyzeMarket: (segment: string) => Promise<any>;
  hireCandidate: (candidateId: string, role: string, salary: number) => Promise<void>;
  negotiateWithInvestor: (investorId: string, valuation: number, equity: number) => Promise<void>;
  handleCrisis: (crisisId: string, response: string) => Promise<void>;
  injectMemory: (key: string, value: string) => Promise<void>;
  runLoadTest: () => Promise<void>;
  deployToProduction: () => Promise<void>;
  sendCustomerEmail: (email: string, subject: string, content: string) => Promise<void>;
  postJobListing: (role: string, requirements: string, salaryRange: string) => Promise<void>;
  holdOneOnOne: (employeeId: string) => Promise<void>;
  fireEmployee: (employeeId: string) => Promise<void>;
  createFinancialModel: (params: any) => Promise<void>;
  
  // Ghost Founder Actions
  takeControl: (role: AgentRoleId) => Promise<void>;
  releaseControl: (role: AgentRoleId) => Promise<void>;
  openGhostConsole: (role: AgentRoleId) => void;
  closeGhostConsole: () => void;
  fetchGhostBriefing: (role: AgentRoleId) => Promise<any>;
  refreshControllers: () => Promise<void>;
  ghostMakeDecision: (role: AgentRoleId, decisionType: string, decision: string, reasoning: string) => Promise<void>;
  ghostSendMessage: (fromRole: AgentRoleId, toRole: AgentRoleId, subject: string, content: string) => Promise<void>;
  ghostHandleCrisis: (role: AgentRoleId, crisisId: string, response: string) => Promise<void>;
  ghostBuildFeature: (name: string, complexity: string, engineers: number) => Promise<void>;
  ghostHire: (candidateId: string, role: string, salary: number) => Promise<void>;
  ghostNegotiate: (investorId: string, valuation: number, equity: number) => Promise<void>;
  ghostAnalyzeMarket: (segment: string) => Promise<void>;
  ghostPivot: (newDirection: string, rationale: string, vote: string) => Promise<void>;

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
  genomeExports: {},
  comparison: null,
  availableModels: [],

  roleControllers: { ceo: "ai", cto: "ai", sales: "ai", people: "ai", cfo: "ai" },
  ghostActiveRole: null,
  humanActionLog: [],
  ghostBriefings: {},

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
      set({
        roleControllers: { ceo: "ai", cto: "ai", sales: "ai", people: "ai", cfo: "ai" },
        ghostActiveRole: null,
        humanActionLog: [],
        ghostBriefings: {},
      });
      await get().refreshControllers();
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
      await get().refreshControllers();
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
        cash: cfoView.financials?.cash ?? get().cash,
        mrr: cfoView.financials?.mrr ?? get().mrr,
        valuation: cfoView.financials?.valuation ?? ceoView.financials?.valuation ?? get().valuation,
        burnRateDaily: cfoView.financials?.burn_rate_daily ?? get().burnRateDaily,
        equitySold: cfoView.financials?.equity_sold ?? get().equitySold,
        seriesAClosed: ceoView.series_a_closed ?? get().seriesAClosed,
        
        productMaturity: ctoView.product?.product_maturity ?? get().productMaturity,
        techDebt: ctoView.product?.tech_debt ?? get().techDebt,
        uptime: ctoView.product?.uptime ?? get().uptime,
        pendingFeatures: ctoView.product?.pending_features ?? get().pendingFeatures,
        featuresShipped: ctoView.product?.features_shipped ?? get().featuresShipped,

        employees: peopleView.team?.employees ?? ctoView.team?.employees ?? get().employees,
        candidatePool: peopleView.team?.candidate_pool ?? get().candidatePool,
        cofounderMorale: peopleView.team?.cofounder_morale ?? ceoView.team?.cofounder_morale ?? get().cofounderMorale,
        cofounderAlignment: peopleView.cofounder_alignment ?? get().cofounderAlignment,

        customers: ceoView.customers?.customers ?? get().customers,
        investors: ceoView.investors?.investors ?? get().investors,
        competitors: ceoView.competitors?.competitors ?? get().competitors,

        companyBrain: ceoView.company_brain ?? get().companyBrain,
        personalCrises: ceoView.active_personal_crises ?? get().personalCrises,

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
        genomes: { ...state.genomes, [modelId]: result.genome },
        genomeExports: { ...state.genomeExports, [modelId]: result }
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

  listFounderGenomes: async () => {
    try {
      const result = await genesisClient.callTool("list_founder_genomes", {});
      set({ availableModels: result.models || [] });
      return result.models || [];
    } catch (error) {
      console.error("List genomes failed:", error);
      return [];
    }
  },

  buildFeature: async (name, complexity, engineers) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("build_feature", { 
        episode_id: episodeId, 
        agent_role: "cto",
        name,
        complexity,
        engineers
      });
      await get().fetchState();
    } catch (error) {
      console.error("Build feature failed:", error);
    }
  },

  analyzeMarket: async (segment) => {
    const { episodeId } = get();
    if (!episodeId) return null;
    try {
      const result = await genesisClient.callTool("analyze_market", { 
        episode_id: episodeId, 
        agent_role: "ceo",
        segment
      });
      await get().fetchState();
      return result;
    } catch (error) {
      console.error("Analyze market failed:", error);
      return null;
    }
  },

  hireCandidate: async (candidateId, role, salary) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("hire_candidate", { 
        episode_id: episodeId, 
        agent_role: "people",
        candidate_id: candidateId,
        role,
        salary
      });
      await get().fetchState();
    } catch (error) {
      console.error("Hire candidate failed:", error);
    }
  },

  negotiateWithInvestor: async (investorId, valuation, equity) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("negotiate_with_investor", { 
        episode_id: episodeId, 
        agent_role: "cfo",
        investor_id: investorId,
        valuation,
        equity
      });
      await get().fetchState();
    } catch (error) {
      console.error("Negotiate failed:", error);
    }
  },

  handleCrisis: async (crisisId, response) => {
    const { episodeId, personalCrises } = get();
    if (!episodeId) return;
    
    // Find the crisis to get its target role
    const crisis = personalCrises.find(c => c.id === crisisId);
    if (!crisis) return;

    try {
      await genesisClient.callTool("handle_personal_crisis", { 
        episode_id: episodeId, 
        agent_role: crisis.target_role.toLowerCase(),
        crisis_id: crisisId,
        response
      });
      await get().fetchState();
    } catch (error) {
      console.error("Handle crisis failed:", error);
    }
  },

  injectMemory: async (key, value) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("write_company_brain", { 
        episode_id: episodeId, 
        agent_role: "ceo",
        key,
        value
      });
      await get().fetchState();
    } catch (error) {
      console.error("Inject memory failed:", error);
    }
  },

  runLoadTest: async () => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("run_load_test", { 
        episode_id: episodeId, 
        agent_role: "cto" 
      });
      await get().fetchState();
    } catch (error) {
      console.error("Run load test failed:", error);
    }
  },

  deployToProduction: async () => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("deploy_to_production", { 
        episode_id: episodeId, 
        agent_role: "cto" 
      });
      await get().fetchState();
    } catch (error) {
      console.error("Deploy failed:", error);
    }
  },

  sendCustomerEmail: async (email, subject, content) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("send_customer_email", { 
        episode_id: episodeId, 
        agent_role: "sales",
        customer_email: email,
        subject,
        content
      });
      await get().fetchState();
    } catch (error) {
      console.error("Send email failed:", error);
    }
  },

  postJobListing: async (role, requirements, salaryRange) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("post_job_listing", { 
        episode_id: episodeId, 
        agent_role: "people",
        role,
        requirements,
        salary_range: salaryRange
      });
      await get().fetchState();
    } catch (error) {
      console.error("Post job failed:", error);
    }
  },

  holdOneOnOne: async (employeeId) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("hold_one_on_one", { 
        episode_id: episodeId, 
        agent_role: "people",
        employee_id: employeeId
      });
      await get().fetchState();
    } catch (error) {
      console.error("Hold one-on-one failed:", error);
    }
  },

  fireEmployee: async (employeeId) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("fire_employee", { 
        episode_id: episodeId, 
        agent_role: "people",
        employee_id: employeeId
      });
      await get().fetchState();
    } catch (error) {
      console.error("Fire employee failed:", error);
    }
  },

  createFinancialModel: async (params) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("create_financial_model", { 
        episode_id: episodeId, 
        agent_role: "cfo",
        ...params
      });
      await get().fetchState();
    } catch (error) {
      console.error("Create financial model failed:", error);
    }
  },

  takeControl: async (role) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      const result = await genesisClient.callTool("set_role_controller", {
        episode_id: episodeId,
        role,
        controller: "human",
      });
      if (result?.role_controllers) {
        set({ roleControllers: result.role_controllers, ghostActiveRole: role });
      }
      await get().fetchGhostBriefing(role);
      await get().refreshControllers();
    } catch (error) {
      console.error("Take control failed:", error);
    }
  },

  releaseControl: async (role) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      const result = await genesisClient.callTool("set_role_controller", {
        episode_id: episodeId,
        role,
        controller: "ai",
      });
      if (result?.role_controllers) {
        set({ roleControllers: result.role_controllers });
      }
      const { ghostActiveRole } = get();
      if (ghostActiveRole === role) set({ ghostActiveRole: null });
      await get().refreshControllers();
    } catch (error) {
      console.error("Release control failed:", error);
    }
  },

  openGhostConsole: (role) => {
    set({ ghostActiveRole: role });
    get().fetchGhostBriefing(role).catch(() => {});
  },

  closeGhostConsole: () => set({ ghostActiveRole: null }),

  fetchGhostBriefing: async (role) => {
    const { episodeId } = get();
    if (!episodeId) return null;
    try {
      const view = await genesisClient.callTool("get_company_state", {
        episode_id: episodeId,
        agent_role: role,
      });
      set((state) => ({ ghostBriefings: { ...state.ghostBriefings, [role]: view } }));
      return view;
    } catch (error) {
      console.error("Fetch ghost briefing failed:", error);
      return null;
    }
  },

  refreshControllers: async () => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      const result = await genesisClient.callTool("get_role_controllers", {
        episode_id: episodeId,
      });
      set({
        roleControllers: result.role_controllers ?? get().roleControllers,
        humanActionLog: result.human_action_log ?? get().humanActionLog,
      });
    } catch (error) {
      console.error("Refresh controllers failed:", error);
    }
  },

  ghostMakeDecision: async (role, decisionType, decision, reasoning) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("make_decision", {
        episode_id: episodeId,
        agent_role: role,
        decision_type: decisionType,
        decision,
        reasoning,
      });
      await genesisClient.callTool("log_human_action", {
        episode_id: episodeId,
        role,
        action: "make_decision",
        details: `${decisionType}: ${decision}`,
      });
      await get().fetchState();
      await get().fetchGhostBriefing(role);
      await get().refreshControllers();
    } catch (error) {
      console.error("Ghost make decision failed:", error);
    }
  },

  ghostSendMessage: async (fromRole, toRole, subject, content) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("send_message", {
        episode_id: episodeId,
        from_role: fromRole,
        to_role: toRole,
        subject,
        content,
      });
      await genesisClient.callTool("log_human_action", {
        episode_id: episodeId,
        role: fromRole,
        action: "send_message",
        details: `to ${toRole}: ${subject}`,
      });
      await get().refreshControllers();
    } catch (error) {
      console.error("Ghost send message failed:", error);
    }
  },

  ghostHandleCrisis: async (role, crisisId, response) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("handle_personal_crisis", {
        episode_id: episodeId,
        agent_role: role,
        crisis_id: crisisId,
        response,
      });
      await genesisClient.callTool("log_human_action", {
        episode_id: episodeId,
        role,
        action: "handle_crisis",
        details: `${crisisId}: ${response.substring(0, 80)}`,
      });
      await get().fetchState();
      await get().fetchGhostBriefing(role);
      await get().refreshControllers();
    } catch (error) {
      console.error("Ghost handle crisis failed:", error);
    }
  },

  ghostBuildFeature: async (name, complexity, engineers) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("build_feature", {
        episode_id: episodeId,
        agent_role: "cto",
        name,
        complexity,
        engineers,
      });
      await genesisClient.callTool("log_human_action", {
        episode_id: episodeId,
        role: "cto",
        action: "build_feature",
        details: `${name} [${complexity}, ${engineers} eng]`,
      });
      await get().fetchState();
      await get().fetchGhostBriefing("cto");
      await get().refreshControllers();
    } catch (error) {
      console.error("Ghost build feature failed:", error);
    }
  },

  ghostHire: async (candidateId, role, salary) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("hire_candidate", {
        episode_id: episodeId,
        agent_role: "people",
        candidate_id: candidateId,
        role,
        salary,
      });
      await genesisClient.callTool("log_human_action", {
        episode_id: episodeId,
        role: "people",
        action: "hire_candidate",
        details: `${role} @ $${salary}`,
      });
      await get().fetchState();
      await get().fetchGhostBriefing("people");
      await get().refreshControllers();
    } catch (error) {
      console.error("Ghost hire failed:", error);
    }
  },

  ghostNegotiate: async (investorId, valuation, equity) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("negotiate_with_investor", {
        episode_id: episodeId,
        agent_role: "cfo",
        investor_id: investorId,
        valuation,
        equity,
      });
      await genesisClient.callTool("log_human_action", {
        episode_id: episodeId,
        role: "cfo",
        action: "negotiate_with_investor",
        details: `${investorId} val=$${valuation} eq=${(equity * 100).toFixed(1)}%`,
      });
      await get().fetchState();
      await get().fetchGhostBriefing("cfo");
      await get().refreshControllers();
    } catch (error) {
      console.error("Ghost negotiate failed:", error);
    }
  },

  ghostAnalyzeMarket: async (segment) => {
    const { episodeId } = get();
    if (!episodeId) return;
    try {
      await genesisClient.callTool("analyze_market", {
        episode_id: episodeId,
        agent_role: "ceo",
        segment,
      });
      await genesisClient.callTool("log_human_action", {
        episode_id: episodeId,
        role: "ceo",
        action: "analyze_market",
        details: segment,
      });
      await get().refreshControllers();
    } catch (error) {
      console.error("Ghost analyze market failed:", error);
    }
  },

  ghostPivot: async (newDirection, rationale, vote) => {
    const { episodeId, ghostActiveRole } = get();
    if (!episodeId) return;
    const role = ghostActiveRole ?? "ceo";
    try {
      await genesisClient.callTool("pivot_company", {
        episode_id: episodeId,
        agent_role: role,
        new_direction: newDirection,
        rationale,
        vote,
      });
      await genesisClient.callTool("log_human_action", {
        episode_id: episodeId,
        role,
        action: "pivot_company",
        details: `${vote}: ${newDirection}`,
      });
      await get().fetchState();
      await get().refreshControllers();
    } catch (error) {
      console.error("Ghost pivot failed:", error);
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
