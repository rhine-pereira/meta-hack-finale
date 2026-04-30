"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { Award, Info } from "lucide-react";

export const RewardPanel = () => {
  const { currentReward } = useGenesisStore();

  const components = [
    { key: "company_valuation", label: "Valuation", weight: 0.20 },
    { key: "series_a_success", label: "Series A", weight: 0.10 },
    { key: "runway_management", label: "Runway", weight: 0.10 },
    { key: "product_velocity", label: "Velocity", weight: 0.10 },
    { key: "customer_retention", label: "Retention", weight: 0.10 },
    { key: "team_morale", label: "Team Morale", weight: 0.10 },
    { key: "cofounder_alignment", label: "Alignment", weight: 0.05 },
    { key: "personal_crisis_handling", label: "Crises", weight: 0.05 },
    { key: "decision_coherence", label: "Coherence", weight: 0.10 },
    { key: "company_brain_quality", label: "Brain", weight: 0.05 },
    { key: "pivot_execution", label: "Pivot", weight: 0.05 },
  ];

  return (
    <div className="flex flex-col h-full bg-bg-surface/40 backdrop-blur-sm border border-border-dim rounded-lg overflow-hidden p-pad-card">
      <div className="flex items-center justify-between mb-3 border-b border-border-dim pb-2">
        <div className="flex items-center gap-2">
          <Award size={18} className="text-accent" />
          <h3 className="font-heading-section text-sm font-bold text-text-primary uppercase tracking-tight">Reward Rubric</h3>
        </div>
        <div className="text-xl font-mono font-black text-accent drop-shadow-[0_0_8px_rgba(45,212,191,0.3)]">
          {(currentReward?.total ?? 0).toFixed(3)}
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <div className="grid grid-cols-2 gap-x-3 gap-y-2">
          {components.map((comp, i) => {
            const value = (currentReward as any)?.[comp.key] ?? 0;
            return (
              <motion.div
                key={comp.key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.02 }}
                className="rounded-md border border-border-dim bg-bg-void/30 px-2 py-1.5"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-[9px] font-black text-text-primary uppercase tracking-tight leading-none truncate">
                      {comp.label}
                    </div>
                    <div className="text-[8px] text-text-muted font-mono leading-none mt-0.5">
                      w={comp.weight.toFixed(2)}
                    </div>
                  </div>
                  <div
                    className={cn(
                      "shrink-0 font-mono text-[10px] font-black tabular-nums",
                      value > 0.7 ? "text-signal-green" : value > 0.4 ? "text-signal-amber" : "text-signal-red"
                    )}
                  >
                    {value.toFixed(2)}
                  </div>
                </div>
                <div className="mt-1 h-1 w-full bg-bg-void rounded-full border border-border-dim overflow-hidden flex relative">
                  <div
                    className={cn(
                      "h-full transition-all duration-700 ease-out",
                      value > 0.7 ? "bg-signal-green" : value > 0.4 ? "bg-signal-amber" : "bg-signal-red"
                    )}
                    style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent pointer-events-none" />
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-border-dim">
         <div className="flex items-start gap-2 p-2 rounded bg-accent/5 border border-accent/20">
           <Info size={14} className="text-accent mt-0.5" />
           <p className="text-[9px] text-text-secondary leading-tight italic">
             Optimization of one component at the expense of another creates cascading systemic risks within 30-90 days.
           </p>
         </div>
      </div>
    </div>
  );
};
