"use client";

import React, { useEffect, useRef, useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { useDemoStream, DemoEvent } from "@/lib/use-demo-stream";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Terminal, 
  Cpu, 
  Activity, 
  TrendingUp, 
  Users, 
  ShieldCheck, 
  BrainCircuit, 
  Radio,
  Clock,
  CheckCircle2,
  AlertCircle,
  Info,
  Circle,
  ChevronRight,
  Database
} from "lucide-react";
import { cn } from "@/lib/utils";

const PHASES = [
  "Session Setup",
  "Product Engineering",
  "Sales & Market",
  "Finance & Fundraising",
  "People & Culture",
  "Memory & Messaging",
  "Personal Crises",
  "Strategy & Pivots",
  "Time Advancement",
  "Resurrection Engine",
  "Ghost Founder",
  "Founder Genome",
  "Blockchain Proofs",
  "Final Reward"
];

export default function LiveDemo() {
  const { events, currentPhase, phaseTitle, isConnected } = useDemoStream();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const stats = {
    features: events.filter(e => e.step === "build_feature" && e.status === "ok").length,
    hires: events.filter(e => e.step === "hire_candidate" && e.status === "ok").length,
    crises: events.filter(e => e.phase_title === "Personal Crises" && e.status === "ok").length,
    proofs: events.filter(e => e.step === "commit_simulation_proof" && e.status === "ok").length,
  };

  return (
    <MainLayout requireEpisode={false}>
      <div className="flex flex-col h-full gap-6 overflow-hidden">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono flex items-center gap-3">
              <Radio size={24} className={cn("text-accent", isConnected && "animate-pulse")} />
              Live Demo Surveillance
            </h1>
            <p className="text-text-secondary text-sm">Real-time observer for the GENESIS automated rollout protocol.</p>
          </div>
          <div className="flex gap-4">
             <div className={cn(
               "px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border flex items-center gap-2",
               isConnected ? "bg-signal-green/10 border-signal-green/30 text-signal-green" : "bg-signal-red/10 border-signal-red/30 text-signal-red"
             )}>
               <div className={cn("w-1.5 h-1.5 rounded-full", isConnected ? "bg-signal-green animate-pulse" : "bg-signal-red")} />
               {isConnected ? "Connection Live" : "Connection Lost"}
             </div>
          </div>
        </div>

        {/* Phase Progress */}
        <div className="glass-panel p-4 rounded-xl border-accent/10">
          <div className="flex justify-between items-center mb-4 px-2">
            <span className="text-[10px] font-black text-text-muted uppercase tracking-widest">Protocol Sequence</span>
            <span className="text-[10px] font-mono text-accent">
              PHASE {currentPhase || 0}/14: {phaseTitle || "WAITING"}
            </span>
          </div>
          <div className="flex items-center gap-2 px-2">
            {PHASES.map((p, i) => {
              const phaseNum = i + 1;
              const isComplete = currentPhase > phaseNum || (currentPhase === 14 && events.some(e => e.step === "demo_complete"));
              const isCurrent = currentPhase === phaseNum;
              return (
                <React.Fragment key={p}>
                  <div className="relative group">
                    <div className={cn(
                      "w-8 h-8 rounded-full border flex items-center justify-center text-[10px] font-mono transition-all duration-500",
                      isComplete ? "bg-accent border-accent text-bg-void shadow-[0_0_10px_rgba(45,212,191,0.3)]" :
                      isCurrent ? "bg-accent/20 border-accent text-accent animate-pulse-glow" :
                      "bg-bg-void border-border-dim text-text-muted"
                    )}>
                      {isComplete ? <CheckCircle2 size={14} /> : phaseNum}
                    </div>
                    <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap text-[8px] font-black uppercase tracking-tighter opacity-0 group-hover:opacity-100 transition-opacity text-text-muted">
                      {p}
                    </div>
                  </div>
                  {i < PHASES.length - 1 && (
                    <div className={cn(
                      "flex-1 h-[1px] transition-all duration-1000",
                      isComplete ? "bg-accent" : "bg-border-dim"
                    )} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
          {/* Main Feed */}
          <div className="lg:col-span-8 flex flex-col gap-4 min-h-0">
            <div className="flex-1 glass-panel rounded-xl overflow-hidden flex flex-col">
              <div className="p-4 border-b border-border-dim bg-bg-surface/60 flex items-center justify-between">
                <div className="flex items-center gap-2 text-text-primary">
                  <Terminal size={16} className="text-accent" />
                  <span className="text-xs font-black uppercase tracking-widest">Event Stream</span>
                </div>
                <button 
                  onClick={() => setAutoScroll(!autoScroll)}
                  className={cn(
                    "text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded transition-all",
                    autoScroll ? "bg-accent/20 text-accent" : "bg-bg-void text-text-muted border border-border-dim"
                  )}
                >
                  {autoScroll ? "Auto-Scroll ON" : "Auto-Scroll OFF"}
                </button>
              </div>

              <div 
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar"
                onWheel={() => setAutoScroll(false)}
              >
                <AnimatePresence initial={false}>
                  {events.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center gap-4 text-text-muted">
                      <Clock size={40} className="animate-spin-slow opacity-20" />
                      <p className="font-mono text-xs uppercase tracking-[0.2em]">Awaiting initialization...</p>
                    </div>
                  ) : (
                    events.map((event, i) => (
                      <motion.div
                        key={event.id}
                        initial={{ opacity: 0, y: 20, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        className={cn(
                          "p-4 rounded-lg border bg-bg-surface/40 backdrop-blur-sm relative overflow-hidden group",
                          event.status === "ok" ? "border-l-4 border-l-signal-green border-border-dim" :
                          event.status === "warn" ? "border-l-4 border-l-signal-amber border-border-dim" :
                          event.status === "error" ? "border-l-4 border-l-signal-red border-border-dim" :
                          "border-l-4 border-l-signal-blue border-border-dim"
                        )}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] font-mono text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20 uppercase">
                              Phase {event.phase}
                            </span>
                            <span className="text-xs font-black text-text-primary uppercase tracking-tight">
                              {event.step}
                            </span>
                          </div>
                          <span className="text-[9px] font-mono text-text-muted">
                            {new Date(event.ts).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-sm text-text-secondary mb-3 leading-relaxed">
                          {event.detail}
                        </p>
                        {event.data && Object.keys(event.data).length > 0 && (
                          <div className="mt-3 bg-bg-void/60 rounded p-3 border border-border-dim/50">
                            <pre className="text-[10px] font-mono text-text-muted overflow-x-auto custom-scrollbar">
                              {JSON.stringify(event.data, null, 2)}
                            </pre>
                          </div>
                        )}
                      </motion.div>
                    ))
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>

          {/* Stats Sidebar */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            <div className="glass-panel p-6 rounded-xl space-y-8">
              <div>
                <h3 className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                  <Activity size={14} className="text-accent" />
                  Live Metrics
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: "Features", value: stats.features, icon: Cpu, color: "text-signal-blue" },
                    { label: "New Hires", value: stats.hires, icon: Users, color: "text-signal-purple" },
                    { label: "Crises Resolved", value: stats.crises, icon: AlertCircle, color: "text-signal-amber" },
                    { label: "Chain Proofs", value: stats.proofs, icon: ShieldCheck, color: "text-signal-green" },
                  ].map((s) => (
                    <div key={s.label} className="bg-bg-void/40 border border-border-dim p-4 rounded-xl">
                      <div className="flex items-center gap-2 mb-2">
                        <s.icon size={12} className={s.color} />
                        <span className="text-[8px] font-black text-text-muted uppercase tracking-widest">{s.label}</span>
                      </div>
                      <div className="text-xl font-mono font-black text-text-primary">{s.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-6 border-t border-border-dim">
                <h3 className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em] mb-4">Current Operation</h3>
                <div className="bg-accent/5 border border-accent/20 p-4 rounded-xl relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-2 opacity-10">
                    <Database size={40} className="text-accent" />
                  </div>
                  <div className="text-[9px] font-black text-accent uppercase mb-1">Active Scenario</div>
                  <div className="text-xs font-mono text-text-primary mb-3">
                    {events.find(e => e.step === "load_postmortem_scenario")?.data?.scenario_id?.toUpperCase() || "STANDARD ROLLOUT"}
                  </div>
                  <div className="text-[9px] font-black text-accent uppercase mb-1">Controller</div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-text-secondary uppercase">
                      {events.some(e => e.phase_title === "Ghost Founder") ? "Hybrid (Ghost + AI)" : "Autonomous Engine"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-6 border-t border-border-dim">
                <div className="p-4 rounded-xl bg-bg-void border border-border-dim flex flex-col items-center text-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center">
                    <BrainCircuit size={20} className="text-accent" />
                  </div>
                  <div>
                    <div className="text-[10px] font-black text-text-primary uppercase tracking-widest mb-1">Founder Genome</div>
                    <p className="text-[9px] text-text-muted font-mono leading-relaxed">
                      Capability fingerprinting active. Behavioral divergence tracking in progress.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Info */}
            <div className="glass-panel p-4 rounded-xl border-signal-blue/20 bg-signal-blue/5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-signal-blue/20">
                  <Info size={16} className="text-signal-blue" />
                </div>
                <div>
                  <div className="text-[9px] font-black text-signal-blue uppercase">Judge Note</div>
                  <p className="text-[10px] text-text-secondary leading-tight">
                    This page visualizes real-time tool interactions between AI agents and the environment.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
