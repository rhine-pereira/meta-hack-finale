"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { 
  ShieldAlert, 
  UserCircle, 
  Terminal, 
  LayoutDashboard, 
  FileText, 
  Users, 
  Briefcase, 
  BrainCircuit, 
  HeartPulse, 
  HelpCircle,
  AlertTriangle,
  History,
  Activity
} from "lucide-react";
import { cn } from "@/lib/utils";

export const Sidebar = () => {
  const { cofounderMorale } = useGenesisStore();

  const roles = [
    { id: "ceo", label: "CEO", color: "text-role-ceo" },
    { id: "cto", label: "CTO", color: "text-role-cto" },
    { id: "sales", label: "Sales", color: "text-role-sales" },
    { id: "people", label: "People", color: "text-role-people" },
    { id: "cfo", label: "CFO", color: "text-role-cfo" },
  ];

  return (
    <aside className="fixed left-0 top-0 h-full hidden lg:flex flex-col z-40 bg-bg-surface/80 backdrop-blur-lg w-64 border-r border-accent/10 shadow-inner-teal pt-20">
      <div className="p-6 border-b border-white/5">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 rounded bg-accent/20 border border-accent/30 flex items-center justify-center">
            <UserCircle className="text-accent" size={18} />
          </div>
          <div>
            <div className="text-accent font-bold uppercase tracking-tighter text-sm font-mono">
              ORBITAL COMMAND
            </div>
            <div className="text-[10px] text-text-muted font-mono">V 2.0.4 - ACTIVE</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 py-4 flex flex-col font-mono text-xs">
        <div className="px-6 py-2 text-[10px] text-text-muted uppercase tracking-widest font-bold">
          Founders
        </div>
        {roles.map((role) => (
          <a
            key={role.id}
            href="#"
            className="text-text-secondary py-4 px-6 flex items-center gap-3 opacity-60 hover:bg-white/5 hover:opacity-100 transition-all duration-300 ease-in-out"
          >
            <div className={cn("w-1.5 h-1.5 rounded-full bg-current", role.color)} />
            <span className="flex-1">{role.label}</span>
            <div className="flex flex-col items-end gap-1">
               <div className="w-12 h-1 bg-border-dim rounded-full overflow-hidden">
                 <div 
                   className={cn("h-full", 
                     (cofounderMorale[role.id] ?? 0.8) > 0.6 ? "bg-signal-green" : 
                     (cofounderMorale[role.id] ?? 0.8) > 0.3 ? "bg-signal-amber" : "bg-signal-red"
                   )} 
                   style={{ width: `${(cofounderMorale[role.id] ?? 0.8) * 100}%` }} 
                 />
               </div>
            </div>
          </a>
        ))}

        <div className="mt-6 px-6 py-2 text-[10px] text-text-muted uppercase tracking-widest font-bold border-t border-white/5 pt-6">
          Operations
        </div>
        <a href="#" className="text-text-secondary py-3 px-6 flex items-center gap-3 opacity-60 hover:bg-white/5 hover:opacity-100 transition-all">
          <Activity size={16} /> Diagnostics
        </a>
        <a href="#" className="text-text-secondary py-3 px-6 flex items-center gap-3 opacity-60 hover:bg-white/5 hover:opacity-100 transition-all">
          <HelpCircle size={16} /> Support
        </a>
      </nav>

      <div className="p-4 border-t border-white/5">
        <button className="w-full py-2.5 bg-signal-red/10 border border-signal-red/30 text-signal-red font-mono text-[10px] font-bold tracking-widest hover:bg-signal-red/20 transition-all flex items-center justify-center gap-2 rounded uppercase">
          <AlertTriangle size={14} />
          EMERGENCY OVERRIDE
        </button>
      </div>
    </aside>
  );
};
