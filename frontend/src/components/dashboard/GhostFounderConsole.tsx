"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useGenesisStore } from "@/lib/store";
import type { AgentRoleId } from "@/types/genesis";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  X,
  User,
  Send,
  Hammer,
  UserPlus,
  Handshake,
  Compass,
  GitBranch,
  ShieldAlert,
  ScrollText,
  Hand,
  Mail,
} from "lucide-react";

const ROLE_LABEL: Record<AgentRoleId, string> = {
  ceo: "CEO",
  cto: "CTO",
  sales: "Sales",
  people: "People",
  cfo: "CFO",
};

const ROLE_TAGLINE: Record<AgentRoleId, string> = {
  ceo: "Vision, fundraising, pivots, market analysis.",
  cto: "Product roadmap, engineering, tech debt.",
  sales: "Customers, revenue, GTM.",
  people: "Hiring, morale, team health.",
  cfo: "Cash, runway, term sheets.",
};

const PEER_ROLES: AgentRoleId[] = ["ceo", "cto", "sales", "people", "cfo"];

export const GhostFounderConsole: React.FC = () => {
  const {
    ghostActiveRole,
    closeGhostConsole,
    roleControllers,
    takeControl,
    releaseControl,
    ghostBriefings,
    fetchGhostBriefing,
    humanActionLog,
    personalCrises,
    investors,
    customers,
    candidatePool,
    pendingFeatures,
    cofounderMorale,
    day,
    ghostMakeDecision,
    ghostSendMessage,
    ghostHandleCrisis,
    ghostBuildFeature,
    ghostHire,
    ghostNegotiate,
    ghostAnalyzeMarket,
    ghostPivot,
  } = useGenesisStore();

  const role = ghostActiveRole;

  useEffect(() => {
    if (role) fetchGhostBriefing(role);
  }, [role, fetchGhostBriefing]);

  if (!role) return null;

  const isHuman = roleControllers[role] === "human";
  const briefing = ghostBriefings[role];
  const myCrises = personalCrises.filter(
    (c) => c.target_role === role && !c.resolved && !c.ignored
  );

  return (
    <AnimatePresence>
      <motion.div
        key="ghost-overlay"
        className="fixed inset-0 z-50 bg-bg-void/80 backdrop-blur-sm flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={closeGhostConsole}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          transition={{ duration: 0.18 }}
          onClick={(e) => e.stopPropagation()}
          className={cn(
            "relative w-[min(1180px,96vw)] h-[min(820px,92vh)] rounded-2xl border overflow-hidden shadow-2xl",
            "bg-bg-surface/95 backdrop-blur-xl",
            isHuman ? "border-signal-purple/40" : "border-border-dim"
          )}
        >
          {/* Header */}
          <div
            className={cn(
              "flex items-center justify-between px-6 py-4 border-b",
              isHuman
                ? "border-signal-purple/30 bg-signal-purple/5"
                : "border-border-dim bg-bg-void/40"
            )}
          >
            <div className="flex items-center gap-4">
              <div
                className={cn(
                  "w-11 h-11 rounded-xl border flex items-center justify-center",
                  isHuman
                    ? "bg-signal-purple/15 border-signal-purple/40 text-signal-purple"
                    : "bg-accent/10 border-accent/30 text-accent"
                )}
              >
                {isHuman ? <User size={20} /> : <Hand size={20} />}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-black uppercase tracking-tight font-mono text-text-primary">
                    Ghost Founder · {ROLE_LABEL[role]}
                  </h2>
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-widest border font-mono",
                      isHuman
                        ? "bg-signal-purple/15 border-signal-purple/40 text-signal-purple"
                        : "bg-bg-void border-border-dim text-text-muted"
                    )}
                  >
                    {isHuman ? "Human Controlled" : "AI Controlled"}
                  </span>
                </div>
                <p className="text-[11px] text-text-muted">
                  Day {day} · {ROLE_TAGLINE[role]}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {isHuman ? (
                <button
                  onClick={() => releaseControl(role)}
                  className="px-3 py-1.5 rounded border border-border-dim text-[10px] font-bold uppercase tracking-widest text-text-secondary hover:text-accent hover:border-accent/50 transition-colors"
                >
                  Release to AI
                </button>
              ) : (
                <button
                  onClick={() => takeControl(role)}
                  className="px-3 py-1.5 rounded bg-signal-purple/15 border border-signal-purple/40 text-signal-purple text-[10px] font-black uppercase tracking-widest hover:bg-signal-purple/25 transition-colors flex items-center gap-1.5"
                >
                  <Hand size={11} />
                  Take Control
                </button>
              )}
              <button
                onClick={closeGhostConsole}
                className="p-1.5 rounded border border-border-dim text-text-muted hover:text-text-primary hover:border-accent/40 transition-colors"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="grid grid-cols-12 gap-0 h-[calc(100%-72px)]">
            {/* Left — Briefing */}
            <div className="col-span-4 border-r border-border-dim p-5 overflow-y-auto custom-scrollbar">
              <SectionHeader icon={<ScrollText size={13} />} label="Briefing" />
              <BriefingPane role={role} briefing={briefing} morale={cofounderMorale[role] ?? 0.8} />

              {myCrises.length > 0 && (
                <div className="mt-5">
                  <SectionHeader icon={<ShieldAlert size={13} />} label="Active Crises" tone="red" />
                  <div className="space-y-2">
                    {myCrises.map((c) => (
                      <CrisisCard
                        key={c.id}
                        description={c.description}
                        severity={c.severity}
                        disabled={!isHuman}
                        onResolve={(response) => ghostHandleCrisis(role, c.id, response)}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Middle — Decision Console */}
            <div className="col-span-5 border-r border-border-dim p-5 overflow-y-auto custom-scrollbar">
              <SectionHeader icon={<Hand size={13} />} label="Decision Console" />
              {!isHuman && (
                <div className="mb-4 p-3 rounded border border-border-dim bg-bg-void/40 text-[11px] text-text-muted">
                  This role is currently AI-driven. Click{" "}
                  <span className="text-signal-purple font-bold">Take Control</span> in the header
                  to override and act yourself.
                </div>
              )}
              <DecisionConsole
                role={role}
                disabled={!isHuman}
                onMakeDecision={(t, d, r) => ghostMakeDecision(role, t, d, r)}
                onSendMessage={(to, subj, body) => ghostSendMessage(role, to, subj, body)}
                onBuildFeature={ghostBuildFeature}
                onHire={ghostHire}
                onNegotiate={ghostNegotiate}
                onAnalyzeMarket={ghostAnalyzeMarket}
                onPivot={ghostPivot}
                investors={investors}
                customers={customers}
                candidatePool={candidatePool}
                pendingFeatures={pendingFeatures}
              />
            </div>

            {/* Right — AI awareness panel */}
            <div className="col-span-3 p-5 overflow-y-auto custom-scrollbar bg-bg-void/30">
              <SectionHeader icon={<GitBranch size={13} />} label="AI Awareness" />
              <div className="text-[11px] text-text-muted leading-relaxed mb-4">
                The remaining AI co-founders see this log at every briefing and adapt
                their plans around it.
              </div>

              <div className="space-y-2">
                {humanActionLog.length === 0 ? (
                  <div className="text-[10px] text-text-muted/60 italic font-mono uppercase tracking-widest">
                    No human actions yet
                  </div>
                ) : (
                  [...humanActionLog]
                    .reverse()
                    .slice(0, 18)
                    .map((entry, i) => (
                      <div
                        key={i}
                        className="p-2 rounded border border-border-dim bg-bg-surface/60 text-[10px]"
                      >
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-signal-purple font-mono font-bold uppercase tracking-widest">
                            {entry.role}
                          </span>
                          <span className="text-text-muted font-mono">D{entry.day}</span>
                        </div>
                        <div className="text-text-primary font-medium">{entry.action}</div>
                        {entry.details ? (
                          <div className="text-text-muted leading-snug mt-0.5 line-clamp-2">
                            {typeof entry.details === "string"
                              ? entry.details
                              : JSON.stringify(entry.details)}
                          </div>
                        ) : null}
                      </div>
                    ))
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

// ── Sub-components ──────────────────────────────────────────────────────────

const SectionHeader: React.FC<{
  icon: React.ReactNode;
  label: string;
  tone?: "default" | "red";
}> = ({ icon, label, tone = "default" }) => (
  <div
    className={cn(
      "flex items-center gap-2 mb-3 text-[10px] font-black uppercase tracking-widest font-mono",
      tone === "red" ? "text-signal-red" : "text-accent"
    )}
  >
    {icon}
    {label}
  </div>
);

const BriefingPane: React.FC<{ role: AgentRoleId; briefing: any; morale: number }> = ({
  role,
  briefing,
  morale,
}) => {
  const stats = useMemo(() => {
    if (!briefing) return [];
    const out: Array<{ label: string; value: string }> = [];
    const f = briefing.financials;
    if (f) {
      if (f.cash != null) out.push({ label: "Cash", value: `$${Math.round(f.cash).toLocaleString()}` });
      if (f.mrr != null) out.push({ label: "MRR", value: `$${Math.round(f.mrr).toLocaleString()}` });
      if (f.runway_days != null)
        out.push({ label: "Runway", value: `${Math.round(f.runway_days)} d` });
      if (f.valuation != null)
        out.push({ label: "Valuation", value: `$${Math.round(f.valuation).toLocaleString()}` });
    }
    const p = briefing.product;
    if (p) {
      if (p.product_maturity != null)
        out.push({ label: "Product", value: `${(p.product_maturity * 100).toFixed(0)}%` });
      if (p.tech_debt != null)
        out.push({ label: "Tech Debt", value: `${(p.tech_debt * 100).toFixed(0)}%` });
      if (p.uptime != null) out.push({ label: "Uptime", value: `${(p.uptime * 100).toFixed(2)}%` });
    }
    const t = briefing.team;
    if (t?.employees) out.push({ label: "Team", value: `${t.employees.length}` });
    return out;
  }, [briefing]);

  return (
    <div>
      <div className="grid grid-cols-2 gap-2 mb-4">
        <Stat label="Role" value={ROLE_LABEL[role]} accent />
        <Stat label="Morale" value={`${(morale * 100).toFixed(0)}%`} />
        {stats.map((s) => (
          <Stat key={s.label} label={s.label} value={s.value} />
        ))}
      </div>

      {briefing?.messages && briefing.messages.length > 0 && (
        <div>
          <div className="text-[10px] font-black uppercase tracking-widest text-text-muted font-mono mb-2 flex items-center gap-1.5">
            <Mail size={11} /> Inbox
          </div>
          <div className="space-y-2">
            {briefing.messages.slice(-5).map((m: any, i: number) => (
              <div
                key={i}
                className="p-2 rounded border border-border-dim bg-bg-void/40 text-[11px]"
              >
                <div className="flex justify-between text-[9px] font-mono uppercase tracking-widest text-text-muted mb-0.5">
                  <span className="text-accent">
                    {m.from_role} → {m.to_role}
                  </span>
                  <span>D{m.day}</span>
                </div>
                <div className="text-text-primary font-bold">{m.subject}</div>
                <div className="text-text-secondary leading-snug line-clamp-3">{m.content}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const Stat: React.FC<{ label: string; value: string; accent?: boolean }> = ({
  label,
  value,
  accent,
}) => (
  <div
    className={cn(
      "p-2 rounded border bg-bg-void/40",
      accent ? "border-accent/40" : "border-border-dim"
    )}
  >
    <div className="text-[9px] uppercase tracking-widest text-text-muted font-mono">{label}</div>
    <div className={cn("text-sm font-mono font-bold", accent ? "text-accent" : "text-text-primary")}>
      {value}
    </div>
  </div>
);

const CrisisCard: React.FC<{
  description: string;
  severity: number;
  disabled: boolean;
  onResolve: (response: string) => void;
}> = ({ description, severity, disabled, onResolve }) => {
  const [response, setResponse] = useState("");
  return (
    <div className="p-3 rounded border border-signal-red/30 bg-signal-red/5">
      <div className="flex items-start gap-2 mb-2">
        <ShieldAlert size={13} className="text-signal-red mt-0.5" />
        <div className="text-[11px] text-text-primary leading-snug font-medium">{description}</div>
      </div>
      <div className="text-[9px] uppercase tracking-widest text-signal-red font-mono mb-2">
        Severity {(severity * 100).toFixed(0)}%
      </div>
      <textarea
        value={response}
        onChange={(e) => setResponse(e.target.value)}
        disabled={disabled}
        placeholder="How do you respond?"
        rows={2}
        className="w-full bg-bg-void/60 border border-border-dim rounded px-2 py-1.5 text-[11px] text-text-primary placeholder:text-text-muted focus:border-signal-red/50 focus:outline-none disabled:opacity-50 resize-none"
      />
      <button
        onClick={() => {
          if (!response.trim()) return;
          onResolve(response.trim());
          setResponse("");
        }}
        disabled={disabled || !response.trim()}
        className="mt-2 w-full py-1.5 rounded bg-signal-red/15 border border-signal-red/40 text-signal-red text-[10px] font-black uppercase tracking-widest hover:bg-signal-red/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Submit Response
      </button>
    </div>
  );
};

// ── Decision Console (role-aware) ───────────────────────────────────────────

const DecisionConsole: React.FC<{
  role: AgentRoleId;
  disabled: boolean;
  onMakeDecision: (type: string, decision: string, reasoning: string) => void;
  onSendMessage: (to: AgentRoleId, subject: string, body: string) => void;
  onBuildFeature: (name: string, complexity: string, engineers: number) => void;
  onHire: (candidateId: string, role: string, salary: number) => void;
  onNegotiate: (investorId: string, valuation: number, equity: number) => void;
  onAnalyzeMarket: (segment: string) => void;
  onPivot: (newDirection: string, rationale: string, vote: string) => void;
  investors: any[];
  customers: any[];
  candidatePool: any[];
  pendingFeatures: any[];
}> = ({
  role,
  disabled,
  onMakeDecision,
  onSendMessage,
  onBuildFeature,
  onHire,
  onNegotiate,
  onAnalyzeMarket,
  onPivot,
  investors,
  candidatePool,
}) => {
  return (
    <div className="space-y-4">
      <DecisionLogger disabled={disabled} onSubmit={onMakeDecision} />

      <SendMessageBlock role={role} disabled={disabled} onSend={onSendMessage} />

      {role === "ceo" && (
        <>
          <AnalyzeMarketBlock disabled={disabled} onSubmit={onAnalyzeMarket} />
          <PivotBlock disabled={disabled} onSubmit={onPivot} />
        </>
      )}

      {role === "cto" && <BuildFeatureBlock disabled={disabled} onSubmit={onBuildFeature} />}

      {role === "people" && (
        <HireBlock disabled={disabled} candidates={candidatePool} onSubmit={onHire} />
      )}

      {role === "cfo" && (
        <NegotiateBlock disabled={disabled} investors={investors} onSubmit={onNegotiate} />
      )}

      {role === "sales" && (
        <div className="p-3 rounded border border-border-dim bg-bg-void/40 text-[11px] text-text-muted">
          Sales-specific tools (customer email / CRM) live on the Market page. Use the
          decision logger above to record GTM moves; remaining AI co-founders will
          adapt to your strategy.
        </div>
      )}
    </div>
  );
};

const Block: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}> = ({ title, icon, children }) => (
  <div className="p-3 rounded border border-border-dim bg-bg-void/40">
    <div className="flex items-center gap-2 mb-3 text-[10px] font-black uppercase tracking-widest text-text-secondary font-mono">
      {icon}
      {title}
    </div>
    {children}
  </div>
);

const Field: React.FC<{
  label: string;
  children: React.ReactNode;
}> = ({ label, children }) => (
  <label className="block mb-2">
    <div className="text-[9px] uppercase tracking-widest text-text-muted font-mono mb-1">
      {label}
    </div>
    {children}
  </label>
);

const inputCls =
  "w-full bg-bg-void/70 border border-border-dim rounded px-2 py-1.5 text-[11px] text-text-primary placeholder:text-text-muted focus:border-accent/50 focus:outline-none disabled:opacity-50";

const submitCls =
  "w-full mt-1 py-1.5 rounded bg-signal-purple/15 border border-signal-purple/40 text-signal-purple text-[10px] font-black uppercase tracking-widest hover:bg-signal-purple/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed";

const DecisionLogger: React.FC<{
  disabled: boolean;
  onSubmit: (type: string, decision: string, reasoning: string) => void;
}> = ({ disabled, onSubmit }) => {
  const [type, setType] = useState("strategic");
  const [decision, setDecision] = useState("");
  const [reasoning, setReasoning] = useState("");
  return (
    <Block title="Log Decision" icon={<ScrollText size={12} />}>
      <Field label="Type">
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          disabled={disabled}
          className={inputCls}
        >
          <option value="strategic">strategic</option>
          <option value="tactical">tactical</option>
        </select>
      </Field>
      <Field label="Decision">
        <input
          type="text"
          value={decision}
          onChange={(e) => setDecision(e.target.value)}
          disabled={disabled}
          placeholder="e.g. Pivot to enterprise PLG"
          className={inputCls}
        />
      </Field>
      <Field label="Reasoning">
        <textarea
          value={reasoning}
          onChange={(e) => setReasoning(e.target.value)}
          disabled={disabled}
          placeholder="Why this is the right move…"
          rows={2}
          className={cn(inputCls, "resize-none")}
        />
      </Field>
      <button
        disabled={disabled || !decision.trim() || !reasoning.trim()}
        onClick={() => {
          onSubmit(type, decision.trim(), reasoning.trim());
          setDecision("");
          setReasoning("");
        }}
        className={submitCls}
      >
        Commit Decision
      </button>
    </Block>
  );
};

const SendMessageBlock: React.FC<{
  role: AgentRoleId;
  disabled: boolean;
  onSend: (to: AgentRoleId, subject: string, body: string) => void;
}> = ({ role, disabled, onSend }) => {
  const peers = PEER_ROLES.filter((r) => r !== role);
  const [to, setTo] = useState<AgentRoleId>(peers[0]);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  return (
    <Block title="Message a Co-founder" icon={<Send size={12} />}>
      <Field label="To">
        <select
          value={to}
          onChange={(e) => setTo(e.target.value as AgentRoleId)}
          disabled={disabled}
          className={inputCls}
        >
          {peers.map((p) => (
            <option key={p} value={p}>
              {ROLE_LABEL[p]}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Subject">
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          disabled={disabled}
          className={inputCls}
        />
      </Field>
      <Field label="Body">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          disabled={disabled}
          rows={3}
          className={cn(inputCls, "resize-none")}
        />
      </Field>
      <button
        disabled={disabled || !subject.trim() || !body.trim()}
        onClick={() => {
          onSend(to, subject.trim(), body.trim());
          setSubject("");
          setBody("");
        }}
        className={submitCls}
      >
        Send Message
      </button>
    </Block>
  );
};

const AnalyzeMarketBlock: React.FC<{
  disabled: boolean;
  onSubmit: (segment: string) => void;
}> = ({ disabled, onSubmit }) => {
  const [segment, setSegment] = useState("");
  return (
    <Block title="Analyze Market" icon={<Compass size={12} />}>
      <Field label="Segment">
        <input
          type="text"
          value={segment}
          onChange={(e) => setSegment(e.target.value)}
          disabled={disabled}
          placeholder="e.g. mid-market fintech"
          className={inputCls}
        />
      </Field>
      <button
        disabled={disabled || !segment.trim()}
        onClick={() => {
          onSubmit(segment.trim());
          setSegment("");
        }}
        className={submitCls}
      >
        Run Analysis
      </button>
    </Block>
  );
};

const PivotBlock: React.FC<{
  disabled: boolean;
  onSubmit: (direction: string, rationale: string, vote: string) => void;
}> = ({ disabled, onSubmit }) => {
  const [direction, setDirection] = useState("");
  const [rationale, setRationale] = useState("");
  const [vote, setVote] = useState("approve");
  return (
    <Block title="Pivot Company" icon={<GitBranch size={12} />}>
      <Field label="New Direction">
        <input
          type="text"
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          disabled={disabled}
          className={inputCls}
        />
      </Field>
      <Field label="Rationale">
        <textarea
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          disabled={disabled}
          rows={2}
          className={cn(inputCls, "resize-none")}
        />
      </Field>
      <Field label="Vote">
        <select
          value={vote}
          onChange={(e) => setVote(e.target.value)}
          disabled={disabled}
          className={inputCls}
        >
          <option value="approve">approve</option>
          <option value="reject">reject</option>
          <option value="override">override (CEO only)</option>
        </select>
      </Field>
      <button
        disabled={disabled || !direction.trim() || !rationale.trim()}
        onClick={() => {
          onSubmit(direction.trim(), rationale.trim(), vote);
          setDirection("");
          setRationale("");
        }}
        className={submitCls}
      >
        Submit Pivot
      </button>
    </Block>
  );
};

const BuildFeatureBlock: React.FC<{
  disabled: boolean;
  onSubmit: (name: string, complexity: string, engineers: number) => void;
}> = ({ disabled, onSubmit }) => {
  const [name, setName] = useState("");
  const [complexity, setComplexity] = useState("medium");
  const [engineers, setEngineers] = useState(2);
  return (
    <Block title="Build Feature" icon={<Hammer size={12} />}>
      <Field label="Name">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={disabled}
          className={inputCls}
        />
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Complexity">
          <select
            value={complexity}
            onChange={(e) => setComplexity(e.target.value)}
            disabled={disabled}
            className={inputCls}
          >
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </Field>
        <Field label="Engineers">
          <input
            type="number"
            min={1}
            max={20}
            value={engineers}
            onChange={(e) => setEngineers(parseInt(e.target.value || "1", 10))}
            disabled={disabled}
            className={inputCls}
          />
        </Field>
      </div>
      <button
        disabled={disabled || !name.trim()}
        onClick={() => {
          onSubmit(name.trim(), complexity, engineers);
          setName("");
        }}
        className={submitCls}
      >
        Kick Off Build
      </button>
    </Block>
  );
};

const HireBlock: React.FC<{
  disabled: boolean;
  candidates: any[];
  onSubmit: (candidateId: string, role: string, salary: number) => void;
}> = ({ disabled, candidates, onSubmit }) => {
  const [candidateId, setCandidateId] = useState<string>(candidates[0]?.id ?? "");
  const [role, setRole] = useState("Engineer");
  const [salary, setSalary] = useState(120000);
  useEffect(() => {
    if (!candidateId && candidates[0]?.id) setCandidateId(candidates[0].id);
  }, [candidates, candidateId]);
  return (
    <Block title="Hire Candidate" icon={<UserPlus size={12} />}>
      <Field label="Candidate">
        <select
          value={candidateId}
          onChange={(e) => setCandidateId(e.target.value)}
          disabled={disabled || candidates.length === 0}
          className={inputCls}
        >
          {candidates.length === 0 && <option value="">— No candidates in pool —</option>}
          {candidates.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} · skill {(c.skill_level * 100).toFixed(0)}%
            </option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Role">
          <input
            type="text"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            disabled={disabled}
            className={inputCls}
          />
        </Field>
        <Field label="Salary ($)">
          <input
            type="number"
            min={50000}
            step={5000}
            value={salary}
            onChange={(e) => setSalary(parseInt(e.target.value || "0", 10))}
            disabled={disabled}
            className={inputCls}
          />
        </Field>
      </div>
      <button
        disabled={disabled || !candidateId || !role.trim()}
        onClick={() => onSubmit(candidateId, role.trim(), salary)}
        className={submitCls}
      >
        Send Offer
      </button>
    </Block>
  );
};

const NegotiateBlock: React.FC<{
  disabled: boolean;
  investors: any[];
  onSubmit: (investorId: string, valuation: number, equity: number) => void;
}> = ({ disabled, investors, onSubmit }) => {
  const [investorId, setInvestorId] = useState(investors[0]?.id ?? "");
  const [valuation, setValuation] = useState(10_000_000);
  const [equityPct, setEquityPct] = useState(15);
  useEffect(() => {
    if (!investorId && investors[0]?.id) setInvestorId(investors[0].id);
  }, [investors, investorId]);
  return (
    <Block title="Negotiate with Investor" icon={<Handshake size={12} />}>
      <Field label="Investor">
        <select
          value={investorId}
          onChange={(e) => setInvestorId(e.target.value)}
          disabled={disabled || investors.length === 0}
          className={inputCls}
        >
          {investors.length === 0 && <option value="">— No investors in pipeline —</option>}
          {investors.map((inv) => (
            <option key={inv.id} value={inv.id}>
              {inv.name} · sentiment {(inv.sentiment * 100).toFixed(0)}%
            </option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Valuation ($)">
          <input
            type="number"
            min={1_000_000}
            step={500_000}
            value={valuation}
            onChange={(e) => setValuation(parseInt(e.target.value || "0", 10))}
            disabled={disabled}
            className={inputCls}
          />
        </Field>
        <Field label="Equity (%)">
          <input
            type="number"
            min={1}
            max={50}
            step={0.5}
            value={equityPct}
            onChange={(e) => setEquityPct(parseFloat(e.target.value || "0"))}
            disabled={disabled}
            className={inputCls}
          />
        </Field>
      </div>
      <button
        disabled={disabled || !investorId}
        onClick={() => onSubmit(investorId, valuation, equityPct / 100)}
        className={submitCls}
      >
        Send Term Sheet
      </button>
    </Block>
  );
};
