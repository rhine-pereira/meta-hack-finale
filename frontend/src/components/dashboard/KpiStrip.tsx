"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { formatCurrency, formatNumber, cn } from "@/lib/utils";
import { motion } from "framer-motion";

export const KpiStrip = () => {
  const { cash, mrr, runwayDays, valuation, employees, currentReward } = useGenesisStore();

  const kpis = [
    { 
      label: "Cash", 
      value: formatCurrency(cash), 
      color: cash > 200_000 ? "text-signal-green" : cash > 100_000 ? "text-signal-amber" : "text-signal-red" 
    },
    { 
      label: "MRR", 
      value: formatCurrency(mrr), 
      color: "text-signal-green" 
    },
    { 
      label: "Runway", 
      value: runwayDays() === Infinity ? "∞" : `${runwayDays()} Days`, 
      color: runwayDays() > 180 ? "text-signal-green" : runwayDays() > 60 ? "text-signal-amber" : "text-signal-red" 
    },
    { 
      label: "Valuation", 
      value: formatCurrency(valuation), 
      color: "text-accent" 
    },
    { 
      label: "Team", 
      value: `${employees.length} Founders`, 
      color: "text-text-primary" 
    },
    { 
      label: "Reward", 
      value: (currentReward?.total ?? 0).toFixed(3), 
      color: "text-accent",
      isHero: true
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
      {kpis.map((kpi, i) => (
        <motion.div
          key={kpi.label}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className={cn(
            "bg-bg-surface/50 backdrop-blur-md border border-border-dim rounded p-4 flex flex-col justify-between h-[100px]",
            kpi.isHero && "border-accent/40 bg-accent/5 shadow-[0_0_15px_rgba(45,212,191,0.05)]"
          )}
        >
          <div className="font-mono text-[10px] text-text-muted uppercase tracking-widest">
            {kpi.label}
          </div>
          <div className={cn("font-mono text-2xl font-bold tracking-tight", kpi.color)}>
            {kpi.value}
          </div>
          {kpi.label === "Runway" && runwayDays() !== Infinity && (
            <div className="h-1 w-full bg-border-dim mt-2 rounded-full overflow-hidden">
               <div 
                 className={cn("h-full", kpi.color.replace("text-", "bg-"))} 
                 style={{ width: `${Math.min(100, (runwayDays() / 180) * 100)}%` }} 
               />
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
};
