"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { ShieldAlert, Mail } from "lucide-react";

export const AgentPanel = () => {
  const { cofounderMorale, personalCrises } = useGenesisStore();

  const roles = [
    { id: "ceo", label: "CEO", color: "border-role-ceo", glow: "shadow-role-ceo/5" },
    { id: "cto", label: "CTO", color: "border-role-cto", glow: "shadow-role-cto/5" },
    { id: "sales", label: "Sales", color: "border-role-sales", glow: "shadow-role-sales/5" },
    { id: "people", label: "People", color: "border-role-people", glow: "shadow-role-people/5" },
    { id: "cfo", label: "CFO", color: "border-role-cfo", glow: "shadow-role-cfo/5" },
  ];

  return (
    <div className="flex flex-col gap-3 h-full overflow-y-auto pr-1">
       <div className="font-mono text-[10px] text-text-muted uppercase tracking-widest font-bold mb-1">
        Founding Team Status
      </div>
      {roles.map((role, i) => {
        const morale = cofounderMorale[role.id] ?? 0.8;
        const roleCrises = personalCrises.filter(c => c.target_role === role.id && !c.resolved && !c.ignored);
        
        return (
          <motion.div
            key={role.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className={cn(
              "bg-bg-surface/60 backdrop-blur-md border border-border-dim rounded p-4 border-l-4 transition-all hover:bg-bg-hover cursor-pointer shadow-lg",
              role.color
            )}
          >
            <div className="flex justify-between items-start mb-2">
              <div className="font-bold text-sm tracking-tight text-text-primary uppercase">{role.label}</div>
              <div className="flex flex-col items-end gap-1">
                <div className="text-[10px] text-text-muted uppercase font-mono tracking-tighter">Morale: {(morale * 100).toFixed(0)}%</div>
                <div className="w-24 h-1 bg-border-dim rounded-full overflow-hidden">
                  <div 
                    className={cn("h-full", 
                      morale > 0.6 ? "bg-signal-green" : morale > 0.3 ? "bg-signal-amber" : "bg-signal-red"
                    )} 
                    style={{ width: `${morale * 100}%` }} 
                  />
                </div>
              </div>
            </div>

            {roleCrises.length > 0 && (
              <div className="mt-3 p-2 rounded bg-signal-red/10 border border-signal-red/30 flex items-start gap-2">
                <ShieldAlert size={14} className="text-signal-red mt-0.5" />
                <div className="text-[10px] text-signal-red font-medium leading-tight">
                  ACTIVE CRISIS: {roleCrises[0].description.substring(0, 40)}...
                </div>
              </div>
            )}
            
            <div className="mt-4 flex gap-2">
               <button className="flex-1 py-1 rounded border border-border-dim hover:border-accent/50 text-[10px] font-bold uppercase transition-colors text-text-secondary hover:text-text-primary">
                 Briefing
               </button>
               <button className="flex-1 py-1 rounded bg-accent/10 border border-accent/30 hover:bg-accent/20 text-accent text-[10px] font-bold uppercase transition-colors">
                 Decision
               </button>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};
