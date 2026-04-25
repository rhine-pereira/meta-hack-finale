"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { 
  ChevronRight, 
  AlertCircle, 
  Code2, 
  Users, 
  TrendingUp, 
  DollarSign, 
  BrainCircuit,
  Play
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

export const DayPlan = () => {
  const { 
    personalCrises, 
    pendingFeatures, 
    featuresShipped,
    customers,
    employees,
    runwayDays,
    companyBrain,
    advanceDay,
    isRunning
  } = useGenesisStore();

  const activeCrises = personalCrises.filter(c => !c.resolved && !c.ignored);
  
  const suggestions = [];

  if (activeCrises.length > 0) {
    suggestions.push({
      id: "crises",
      label: "Resolve Critical Crises",
      href: "/crises",
      icon: AlertCircle,
      color: "text-signal-red",
      bg: "bg-signal-red/10",
      border: "border-signal-red/30",
      priority: "CRITICAL"
    });
  }

  if (pendingFeatures.length > 0) {
    suggestions.push({
      id: "product",
      label: "Manage Feature Pipeline",
      href: "/product",
      icon: Code2,
      color: "text-accent",
      bg: "bg-accent/10",
      border: "border-accent/30",
      priority: "HIGH"
    });
  }

  if (customers.length === 0) {
    suggestions.push({
      id: "market",
      label: "Acquire First Customers",
      href: "/market",
      icon: TrendingUp,
      color: "text-signal-green",
      bg: "bg-signal-green/10",
      border: "border-signal-green/30",
      priority: "HIGH"
    });
  }

  if (employees.length < 3) {
    suggestions.push({
      id: "team",
      label: "Scale Founding Team",
      href: "/team",
      icon: Users,
      color: "text-signal-blue",
      bg: "bg-signal-blue/10",
      border: "border-signal-blue/30",
      priority: "MEDIUM"
    });
  }

  if (runwayDays() < 100) {
    suggestions.push({
      id: "financials",
      label: "Review Burn & Runway",
      href: "/financials",
      icon: DollarSign,
      color: "text-signal-amber",
      bg: "bg-signal-amber/10",
      border: "border-signal-amber/30",
      priority: "MEDIUM"
    });
  }

  if (Object.keys(companyBrain).length === 0) {
    suggestions.push({
      id: "brain",
      label: "Inject Strategic Memory",
      href: "/brain",
      icon: BrainCircuit,
      color: "text-signal-purple",
      bg: "bg-signal-purple/10",
      border: "border-signal-purple/30",
      priority: "LOW"
    });
  }

  // Limit to 4 suggestions
  const displaySuggestions = suggestions.slice(0, 4);

  return (
    <div className="glass-panel p-6 rounded-xl flex flex-col h-full">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xs font-black text-text-primary uppercase tracking-[0.2em] flex items-center gap-2">
          <Play size={14} className="text-accent" />
          Mission Day Plan
        </h2>
        <span className="text-[10px] text-text-muted font-mono uppercase">Status: {isRunning ? "In Progress" : "Awaiting Actions"}</span>
      </div>

      <div className="flex-1 space-y-3 mb-6">
        {displaySuggestions.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center p-4 border border-dashed border-border-dim rounded-lg">
            <p className="text-[10px] text-text-muted uppercase tracking-widest">Systems Nominal. Ready for Execution.</p>
          </div>
        ) : (
          displaySuggestions.map((s, i) => (
            <Link key={s.id} href={s.href}>
              <motion.div 
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className={cn(
                  "p-3 rounded-lg border transition-all hover:scale-[1.02] flex items-center justify-between group cursor-pointer mb-2",
                  s.bg, s.border
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={cn("p-2 rounded bg-bg-void/50 border border-border-dim", s.color)}>
                    <s.icon size={16} />
                  </div>
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-tight text-text-primary">{s.label}</div>
                    <div className={cn("text-[8px] font-mono", s.color)}>{s.priority}</div>
                  </div>
                </div>
                <ChevronRight size={14} className="text-text-muted group-hover:text-text-primary transition-colors" />
              </motion.div>
            </Link>
          ))
        )}
      </div>

      <button 
        onClick={() => advanceDay()}
        className="w-full py-4 bg-accent text-bg-void font-black text-xs uppercase tracking-[0.3em] rounded-xl hover:bg-accent-glow transition-all flex items-center justify-center gap-2 group shadow-[0_0_20px_rgba(45,212,191,0.2)]"
      >
        Execute Day Plan
        <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
      </button>
    </div>
  );
};
