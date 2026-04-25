"use client";

import React, { useState, useCallback } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { useGenesisStore } from "@/lib/store";
import { genesisClient } from "@/lib/genesis-client";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  Skull,
  Zap,
  ChevronRight,
  ChevronDown,
  RotateCcw,
  FileText,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  DollarSign,
  Activity,
  Play,
  Download,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────

interface ScenarioSummary {
  id: string;
  company_name: string;
  tagline: string;
  year_founded: number;
  year_failed: number;
  total_funding_raised: number;
  category: string;
  num_fork_points: number;
  failure_summary: string;
}

interface ForkComparison {
  fork_title: string;
  day: number;
  category: string;
  target_role: string;
  context_summary: string;
  what_founders_did: string;
  known_outcome: string;
  ai_response: string;
  ai_score: number | null;
  divergence_label: string;
  value_at_stake_usd: number;
  estimated_recovery_usd: number;
  outcome_narrative: string;
}

interface ResurrectionReport {
  company_name: string;
  tagline: string;
  year_founded: number;
  year_failed: number;
  total_funding_raised: number;
  failure_summary: string;
  resurrection_hypothesis: string;
  simulation_day: number;
  forks_reached: number;
  forks_total: number;
  failures_avoided: number;
  avg_ai_decision_score: number;
  total_value_at_stake_usd: number;
  total_estimated_recovery_usd: number;
  overall_verdict: string;
  fork_comparisons: ForkComparison[];
  final_simulation_metrics: {
    cash_remaining: number;
    mrr: number;
    arr: number;
    team_size: number;
    product_maturity: number;
    series_a_closed: boolean;
    pivot_count: number;
    cumulative_reward: number;
  };
}

// ── Constants ────────────────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  consumer: "text-signal-amber border-signal-amber/30 bg-signal-amber/10",
  hardware: "text-signal-blue border-signal-blue/30 bg-signal-blue/10",
  b2b: "text-accent border-accent/30 bg-accent/10",
  fraud: "text-signal-red border-signal-red/30 bg-signal-red/10",
};

const ROLE_COLORS: Record<string, string> = {
  ceo: "text-role-ceo",
  cto: "text-role-cto",
  cfo: "text-role-cfo",
  sales: "text-role-sales",
  people: "text-role-people",
};

// ── Helper Components ────────────────────────────────────────────────────────

const ScoreBar = ({ score, className }: { score: number; className?: string }) => (
  <div className={cn("h-1.5 w-full bg-bg-void rounded-full overflow-hidden border border-border-dim", className)}>
    <motion.div
      initial={{ width: 0 }}
      animate={{ width: `${score * 100}%` }}
      transition={{ duration: 1, ease: "easeOut" }}
      className={cn(
        "h-full rounded-full",
        score >= 0.70 ? "bg-signal-green" :
        score >= 0.50 ? "bg-signal-amber" :
        "bg-signal-red"
      )}
    />
  </div>
);

const DivergenceIcon = ({ label }: { label: string }) => {
  if (label.startsWith("STRONGLY DIVERGED")) return <TrendingUp size={16} className="text-signal-green" />;
  if (label.startsWith("DIVERGED")) return <TrendingUp size={16} className="text-signal-amber" />;
  if (label.startsWith("SIMILAR")) return <Minus size={16} className="text-text-muted" />;
  if (label.startsWith("REPLICATED")) return <TrendingDown size={16} className="text-signal-red" />;
  return <Clock size={16} className="text-text-muted" />;
};

const formatUSD = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` :
  n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` :
  n >= 1e3 ? `$${(n / 1e3).toFixed(0)}K` :
  `$${n.toFixed(0)}`;

// ── Scenario Card ─────────────────────────────────────────────────────────────

const ScenarioCard = ({
  scenario,
  onLoad,
  isLoading,
}: {
  scenario: ScenarioSummary;
  onLoad: (id: string) => void;
  isLoading: boolean;
}) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    className="glass-panel rounded-xl p-6 flex flex-col gap-4 border border-border-dim hover:border-accent/30 transition-all group cursor-pointer"
    onClick={() => onLoad(scenario.id)}
  >
    <div className="flex justify-between items-start">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-signal-red/10 border border-signal-red/20 flex items-center justify-center flex-shrink-0">
          <Skull size={18} className="text-signal-red" />
        </div>
        <div>
          <h3 className="text-sm font-black text-text-primary uppercase tracking-tight">{scenario.company_name}</h3>
          <div className="text-[10px] text-text-muted font-mono">{scenario.year_founded}–{scenario.year_failed}</div>
        </div>
      </div>
      <div className={cn("px-2 py-0.5 rounded border text-[9px] font-black uppercase", CATEGORY_COLORS[scenario.category] ?? "text-text-muted")}>
        {scenario.category}
      </div>
    </div>

    <p className="text-[11px] text-text-secondary leading-relaxed flex-1">{scenario.tagline}</p>

    <div className="flex items-center justify-between border-t border-border-dim pt-3">
      <div className="flex gap-4">
        <div>
          <div className="text-[9px] text-text-muted uppercase font-black">Raised</div>
          <div className="text-[11px] font-mono text-text-primary">{formatUSD(scenario.total_funding_raised)}</div>
        </div>
        <div>
          <div className="text-[9px] text-text-muted uppercase font-black">Forks</div>
          <div className="text-[11px] font-mono text-text-primary">{scenario.num_fork_points}</div>
        </div>
      </div>
      <button
        disabled={isLoading}
        className="flex items-center gap-1.5 px-4 py-2 bg-accent/10 border border-accent/30 text-accent font-black text-[10px] uppercase tracking-widest rounded hover:bg-accent/20 transition-all group-hover:shadow-[0_0_12px_rgba(45,212,191,0.2)] disabled:opacity-50"
      >
        {isLoading ? <Activity size={12} className="animate-spin" /> : <Play size={12} />}
        {isLoading ? "Loading..." : "Load Scenario"}
      </button>
    </div>
  </motion.div>
);

// ── Fork Comparison Row ───────────────────────────────────────────────────────

const ForkRow = ({ fork, index }: { fork: ForkComparison; index: number }) => {
  const [expanded, setExpanded] = useState(false);
  const notReached = fork.divergence_label === "NOT REACHED";
  const noScore = fork.ai_score === null;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.07 }}
      className={cn(
        "glass-panel rounded-xl border overflow-hidden transition-all",
        notReached ? "border-border-dim opacity-50" :
        (fork.ai_score ?? 0) >= 0.70 ? "border-signal-green/20" :
        (fork.ai_score ?? 0) >= 0.50 ? "border-signal-amber/20" :
        "border-signal-red/20"
      )}
    >
      {/* Header row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-5 flex items-center gap-4 hover:bg-bg-hover/30 transition-colors"
      >
        <div className="w-8 h-8 rounded bg-bg-void border border-border-dim flex items-center justify-center flex-shrink-0 font-mono text-[11px] text-text-muted">
          D{fork.day}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={cn("text-[9px] font-black uppercase px-1.5 py-0.5 rounded border", CATEGORY_COLORS[fork.category] ?? "text-text-muted border-border-dim")}>
              {fork.category}
            </span>
            <span className={cn("text-[9px] font-black uppercase", ROLE_COLORS[fork.target_role] ?? "text-text-muted")}>
              {fork.target_role.toUpperCase()}
            </span>
          </div>
          <div className="text-[12px] font-black text-text-primary uppercase tracking-tight truncate">{fork.fork_title}</div>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          {!noScore && (
            <div className="text-right">
              <div className="text-[9px] text-text-muted uppercase font-black mb-1">AI Score</div>
              <div className={cn(
                "text-sm font-mono font-black",
                (fork.ai_score ?? 0) >= 0.70 ? "text-signal-green" :
                (fork.ai_score ?? 0) >= 0.50 ? "text-signal-amber" :
                "text-signal-red"
              )}>
                {((fork.ai_score ?? 0) * 100).toFixed(0)}%
              </div>
            </div>
          )}

          <div className="flex items-center gap-1">
            <DivergenceIcon label={fork.divergence_label} />
          </div>

          {expanded ? <ChevronDown size={14} className="text-text-muted" /> : <ChevronRight size={14} className="text-text-muted" />}
        </div>
      </button>

      {/* Expanded detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t border-border-dim pt-4 grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Left: founders vs AI */}
              <div className="space-y-4">
                <div>
                  <div className="text-[9px] text-text-muted uppercase font-black mb-2 flex items-center gap-1.5">
                    <XCircle size={10} className="text-signal-red" />
                    What The Real Founders Did
                  </div>
                  <div className="p-3 rounded bg-signal-red/5 border border-signal-red/15 text-[11px] text-text-secondary leading-relaxed">
                    {fork.what_founders_did}
                  </div>
                </div>
                <div>
                  <div className="text-[9px] text-text-muted uppercase font-black mb-2 flex items-center gap-1.5">
                    <CheckCircle2 size={10} className="text-signal-green" />
                    What The AI Agents Did
                  </div>
                  <div className={cn(
                    "p-3 rounded border text-[11px] leading-relaxed",
                    notReached ? "text-text-muted border-border-dim bg-bg-void italic" :
                    (fork.ai_score ?? 0) >= 0.55 ? "text-text-secondary border-signal-green/15 bg-signal-green/5" :
                    "text-text-secondary border-signal-amber/15 bg-signal-amber/5"
                  )}>
                    {fork.ai_response}
                  </div>
                </div>
              </div>

              {/* Right: outcomes + metrics */}
              <div className="space-y-4">
                <div>
                  <div className="text-[9px] text-text-muted uppercase font-black mb-2">Historical Outcome</div>
                  <div className="p-3 rounded bg-bg-void border border-border-dim text-[11px] text-text-secondary leading-relaxed">
                    {fork.known_outcome}
                  </div>
                </div>

                {!noScore && (
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-[9px] font-black text-text-muted uppercase mb-1">
                        <span>AI Decision Score</span>
                        <span className={cn(
                          (fork.ai_score ?? 0) >= 0.70 ? "text-signal-green" :
                          (fork.ai_score ?? 0) >= 0.50 ? "text-signal-amber" :
                          "text-signal-red"
                        )}>{fork.divergence_label}</span>
                      </div>
                      <ScoreBar score={fork.ai_score ?? 0} />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-2 rounded bg-bg-void border border-border-dim">
                        <div className="text-[9px] text-text-muted uppercase font-black mb-1">Value at Stake</div>
                        <div className="text-[12px] font-mono text-signal-red">{formatUSD(fork.value_at_stake_usd)}</div>
                      </div>
                      <div className={cn(
                        "p-2 rounded border",
                        fork.estimated_recovery_usd > 0 ? "bg-signal-green/5 border-signal-green/20" : "bg-bg-void border-border-dim"
                      )}>
                        <div className="text-[9px] text-text-muted uppercase font-black mb-1">Est. Recovered</div>
                        <div className={cn(
                          "text-[12px] font-mono",
                          fork.estimated_recovery_usd > 0 ? "text-signal-green" : "text-text-muted"
                        )}>{formatUSD(fork.estimated_recovery_usd)}</div>
                      </div>
                    </div>

                    <div className="p-3 rounded bg-accent/5 border border-accent/15 text-[10px] text-text-secondary leading-relaxed">
                      {fork.outcome_narrative}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// ── Resurrection Report Panel ─────────────────────────────────────────────────

const ResurrectionReportPanel = ({ report }: { report: ResurrectionReport }) => {
  const verdictColor =
    report.overall_verdict.startsWith("RESURRECTION SUCCESSFUL") ? "text-signal-green border-signal-green/20 bg-signal-green/5" :
    report.overall_verdict.startsWith("PARTIAL") ? "text-signal-amber border-signal-amber/20 bg-signal-amber/5" :
    report.overall_verdict.startsWith("NARROW") ? "text-signal-amber border-signal-amber/20 bg-signal-amber/5" :
    "text-signal-red border-signal-red/20 bg-signal-red/5";

  const recoveryPct = report.total_value_at_stake_usd > 0
    ? Math.round((report.total_estimated_recovery_usd / report.total_value_at_stake_usd) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Verdict banner */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn("p-5 rounded-xl border", verdictColor)}
      >
        <div className="flex items-start gap-3">
          <Zap size={20} className="flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-[10px] font-black uppercase tracking-widest mb-1 opacity-70">Overall Verdict</div>
            <div className="text-sm font-bold leading-snug">{report.overall_verdict}</div>
          </div>
        </div>
      </motion.div>

      {/* Summary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: "Failures Avoided",
            value: `${report.failures_avoided}/${report.forks_total}`,
            color: report.failures_avoided >= report.forks_total / 2 ? "text-signal-green" : "text-signal-amber",
          },
          {
            label: "Avg Decision Score",
            value: `${(report.avg_ai_decision_score * 100).toFixed(0)}%`,
            color: report.avg_ai_decision_score >= 0.65 ? "text-signal-green" : report.avg_ai_decision_score >= 0.45 ? "text-signal-amber" : "text-signal-red",
          },
          {
            label: "Value at Stake",
            value: formatUSD(report.total_value_at_stake_usd),
            color: "text-signal-red",
          },
          {
            label: "Est. Recovered",
            value: `${formatUSD(report.total_estimated_recovery_usd)} (${recoveryPct}%)`,
            color: recoveryPct >= 40 ? "text-signal-green" : "text-signal-amber",
          },
        ].map((m, i) => (
          <div key={i} className="glass-panel p-4 rounded-xl">
            <div className="text-[9px] text-text-muted uppercase font-black mb-2">{m.label}</div>
            <div className={cn("text-base font-mono font-black", m.color)}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* Fork-by-fork comparison */}
      <div>
        <h2 className="text-sm font-black text-text-primary uppercase tracking-tight mb-4 flex items-center gap-2">
          <FileText size={16} className="text-accent" />
          Fork-by-Fork Analysis
        </h2>
        <div className="space-y-3">
          {report.fork_comparisons.map((fork, i) => (
            <ForkRow key={`${fork.day}-${i}`} fork={fork} index={i} />
          ))}
        </div>
      </div>

      {/* Resurrection hypothesis */}
      <div className="glass-panel p-5 rounded-xl border border-accent/15 bg-accent/5">
        <div className="text-[9px] text-accent uppercase font-black mb-2 tracking-widest">Resurrection Hypothesis</div>
        <p className="text-[12px] text-text-secondary leading-relaxed">{report.resurrection_hypothesis}</p>
      </div>

      {/* Final simulation metrics */}
      <div className="glass-panel p-5 rounded-xl">
        <div className="text-[10px] text-text-muted uppercase font-black mb-4 tracking-widest">Final Simulation State</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Cash Remaining", value: formatUSD(report.final_simulation_metrics.cash_remaining), icon: DollarSign },
            { label: "ARR", value: formatUSD(report.final_simulation_metrics.arr), icon: TrendingUp },
            { label: "Team Size", value: String(report.final_simulation_metrics.team_size), icon: Activity },
            { label: "Series A", value: report.final_simulation_metrics.series_a_closed ? "CLOSED ✓" : "Open", icon: CheckCircle2 },
          ].map((m, i) => (
            <div key={i} className="p-3 rounded bg-bg-void border border-border-dim">
              <div className="flex items-center gap-1.5 text-[9px] text-text-muted uppercase font-black mb-1">
                <m.icon size={10} />
                {m.label}
              </div>
              <div className="text-[12px] font-mono text-text-primary">{m.value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function PostmortemPage() {
  const { episodeId, reset, difficulty, seed } = useGenesisStore();

  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [loadingScenarios, setLoadingScenarios] = useState(false);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [loadedScenario, setLoadedScenario] = useState<string | null>(null);
  const [report, setReport] = useState<ResurrectionReport | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [activeTab, setActiveTab] = useState<"select" | "loaded" | "report">("select");
  const [error, setError] = useState<string | null>(null);

  const fetchScenarios = useCallback(async () => {
    setLoadingScenarios(true);
    setError(null);
    try {
      const result = await genesisClient.callTool("list_postmortem_scenarios", {});
      setScenarios(result.scenarios || []);
    } catch (e: any) {
      setError(e?.message || "Failed to fetch scenarios");
    } finally {
      setLoadingScenarios(false);
    }
  }, []);

  const handleLoadScenario = useCallback(async (scenarioId: string) => {
    if (!episodeId) {
      // Spin up a session first
      await reset(difficulty, seed);
    }
    const eid = episodeId ?? `ep-${Math.random().toString(36).substring(2, 9)}`;
    setLoadingId(scenarioId);
    setError(null);
    try {
      await genesisClient.callTool("load_postmortem_scenario", {
        episode_id: eid,
        scenario_id: scenarioId,
      });
      setLoadedScenario(scenarioId);
      setActiveTab("loaded");
    } catch (e: any) {
      setError(e?.message || "Failed to load scenario");
    } finally {
      setLoadingId(null);
    }
  }, [episodeId, reset, difficulty, seed]);

  const handleGenerateReport = useCallback(async () => {
    if (!episodeId) return;
    setLoadingReport(true);
    setError(null);
    try {
      const result = await genesisClient.callTool("get_resurrection_report", {
        episode_id: episodeId,
      });
      if (result.error) {
        setError(result.error);
      } else {
        setReport(result);
        setActiveTab("report");
      }
    } catch (e: any) {
      setError(e?.message || "Failed to generate report");
    } finally {
      setLoadingReport(false);
    }
  }, [episodeId]);

  // Auto-load scenarios on first render
  React.useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  const selectedScenario = scenarios.find((s) => s.id === loadedScenario);

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex justify-between items-end">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-8 h-8 rounded-lg bg-signal-red/10 border border-signal-red/20 flex items-center justify-center">
                <Skull size={16} className="text-signal-red" />
              </div>
              <h1 className="text-2xl font-black text-text-primary uppercase tracking-tight font-mono">
                Dead Startup <span className="text-accent">Resurrection Engine</span>
              </h1>
            </div>
            <p className="text-text-secondary text-sm ml-11">
              Replay real startup failures. AI agents face the same fatal forks as the real founders — and try to rewrite history.
            </p>
          </div>
          {loadedScenario && (
            <div className="flex gap-2">
              <button
                onClick={handleGenerateReport}
                disabled={loadingReport}
                className="flex items-center gap-2 px-4 py-2 bg-accent text-bg-void font-black text-[10px] uppercase tracking-widest rounded hover:shadow-[0_0_16px_rgba(45,212,191,0.3)] transition-all disabled:opacity-50"
              >
                {loadingReport ? <Activity size={14} className="animate-spin" /> : <FileText size={14} />}
                Generate Report
              </button>
            </div>
          )}
        </div>

        {/* Error banner */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 p-4 rounded-xl bg-signal-red/10 border border-signal-red/30 text-signal-red text-sm"
          >
            <AlertTriangle size={16} />
            {error}
          </motion.div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border-dim pb-0">
          {([
            { id: "select", label: "Scenario Library", icon: Skull },
            { id: "loaded", label: loadedScenario ? `Loaded: ${selectedScenario?.company_name ?? loadedScenario}` : "Active Scenario", icon: Play },
            { id: "report", label: "Resurrection Report", icon: FileText },
          ] as const).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              disabled={id === "loaded" && !loadedScenario || id === "report" && !report}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 text-[11px] font-black uppercase tracking-widest border-b-2 transition-all -mb-px disabled:opacity-30 disabled:cursor-default",
                activeTab === id
                  ? "border-accent text-accent"
                  : "border-transparent text-text-muted hover:text-text-secondary hover:border-border-active"
              )}
            >
              <Icon size={12} />
              {label}
            </button>
          ))}
        </div>

        {/* Tab: Scenario Library */}
        {activeTab === "select" && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <p className="text-[11px] text-text-muted font-mono">
                {scenarios.length} failure scenarios available. Each encodes real decision forks as simulation events.
              </p>
              <button
                onClick={fetchScenarios}
                disabled={loadingScenarios}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border-dim text-text-muted text-[10px] uppercase hover:border-accent/30 hover:text-accent transition-all"
              >
                <RotateCcw size={10} className={loadingScenarios ? "animate-spin" : ""} />
                Refresh
              </button>
            </div>

            {loadingScenarios ? (
              <div className="py-20 text-center text-text-muted text-[11px] uppercase tracking-widest animate-pulse">
                Loading scenario library...
              </div>
            ) : scenarios.length === 0 ? (
              <div className="py-20 glass-panel rounded-xl text-center text-text-muted text-xs uppercase tracking-widest border-dashed italic">
                No scenarios available. Ensure the GENESIS server is running.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {scenarios.map((s) => (
                  <ScenarioCard
                    key={s.id}
                    scenario={s}
                    onLoad={handleLoadScenario}
                    isLoading={loadingId === s.id}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab: Active Scenario */}
        {activeTab === "loaded" && loadedScenario && selectedScenario && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            {/* Scenario overview */}
            <div className="glass-panel p-6 rounded-xl border border-signal-red/20 bg-signal-red/5">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-signal-red/10 border border-signal-red/20 flex items-center justify-center flex-shrink-0">
                  <Skull size={22} className="text-signal-red" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-xl font-black text-text-primary uppercase tracking-tight">{selectedScenario.company_name}</h2>
                    <span className={cn("px-2 py-0.5 rounded border text-[9px] font-black uppercase", CATEGORY_COLORS[selectedScenario.category] ?? "text-text-muted")}>
                      {selectedScenario.category}
                    </span>
                  </div>
                  <p className="text-[12px] text-text-secondary mb-3">{selectedScenario.tagline}</p>
                  <div className="flex gap-4 text-[10px]">
                    <div><span className="text-text-muted">Founded:</span> <span className="text-text-primary font-mono">{selectedScenario.year_founded}</span></div>
                    <div><span className="text-text-muted">Failed:</span> <span className="text-signal-red font-mono">{selectedScenario.year_failed}</span></div>
                    <div><span className="text-text-muted">Raised:</span> <span className="text-text-primary font-mono">{formatUSD(selectedScenario.total_funding_raised)}</span></div>
                    <div><span className="text-text-muted">Fork Points:</span> <span className="text-accent font-mono">{selectedScenario.num_fork_points}</span></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Instructions */}
            <div className="glass-panel p-5 rounded-xl border border-accent/15">
              <h3 className="text-[10px] font-black text-accent uppercase tracking-widest mb-3">How to Run This Scenario</h3>
              <ol className="space-y-2 text-[11px] text-text-secondary">
                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-accent/10 border border-accent/20 text-accent text-[9px] font-black flex items-center justify-center flex-shrink-0 mt-0.5">1</span>
                  <span>Run the simulation from the Dashboard (Advance Day button). Fork points fire automatically at the scheduled days.</span>
                </li>
                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-accent/10 border border-accent/20 text-accent text-[9px] font-black flex items-center justify-center flex-shrink-0 mt-0.5">2</span>
                  <span>When a <code className="text-accent bg-accent/10 px-1 rounded text-[10px]">[HISTORICAL FORK]</code> crisis appears in an agent's briefing, the AI resolves it via <code className="text-accent bg-accent/10 px-1 rounded text-[10px]">handle_personal_crisis</code>.</span>
                </li>
                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-accent/10 border border-accent/20 text-accent text-[9px] font-black flex items-center justify-center flex-shrink-0 mt-0.5">3</span>
                  <span>For each fork, also call <code className="text-accent bg-accent/10 px-1 rounded text-[10px]">record_fork_decision</code> to log the AI's choice for the Resurrection Report.</span>
                </li>
                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-accent/10 border border-accent/20 text-accent text-[9px] font-black flex items-center justify-center flex-shrink-0 mt-0.5">4</span>
                  <span>After all forks have fired (or the simulation ends), click <strong className="text-accent">Generate Report</strong> above to see the Resurrection Report.</span>
                </li>
              </ol>
            </div>

            {/* Fork schedule */}
            <div>
              <h3 className="text-[10px] font-black text-text-muted uppercase tracking-widest mb-3">Scheduled Fork Points</h3>
              <div className="space-y-2">
                {Array.from({ length: selectedScenario.num_fork_points }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4 p-3 rounded bg-bg-void border border-border-dim text-[11px]">
                    <Clock size={12} className="text-text-muted flex-shrink-0" />
                    <span className="text-text-muted font-mono">Fork {i + 1}</span>
                    <span className="text-text-primary">See simulation briefing for details</span>
                    <span className="ml-auto text-text-muted">fires automatically</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={handleGenerateReport}
              disabled={loadingReport}
              className="w-full py-3 bg-accent/10 border border-accent/30 text-accent font-black text-[11px] uppercase tracking-widest rounded-xl hover:bg-accent/20 transition-all flex items-center justify-center gap-2"
            >
              {loadingReport ? <Activity size={14} className="animate-spin" /> : <FileText size={14} />}
              {loadingReport ? "Generating Resurrection Report..." : "Generate Resurrection Report Now"}
            </button>
          </motion.div>
        )}

        {/* Tab: Resurrection Report */}
        {activeTab === "report" && report && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {/* Report header */}
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-xl font-black text-text-primary uppercase tracking-tight">
                  {report.company_name} — Resurrection Report
                </h2>
                <p className="text-[11px] text-text-muted">Simulation Day {report.simulation_day} · {report.forks_reached}/{report.forks_total} forks reached</p>
              </div>
              <button className="flex items-center gap-2 px-4 py-2 border border-border-dim text-text-muted text-[10px] uppercase rounded hover:border-accent/30 hover:text-accent transition-all">
                <Download size={12} />
                Export JSON
              </button>
            </div>
            <ResurrectionReportPanel report={report} />
          </motion.div>
        )}
      </div>
    </MainLayout>
  );
}
