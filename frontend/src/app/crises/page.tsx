"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { MainLayout } from "@/components/layout/MainLayout";
import { BackToDashboard } from "@/components/navigation/BackToDashboard";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { 
  ShieldAlert, 
  History, 
  CheckCircle2, 
  Ban, 
  Clock, 
  Activity,
  ChevronRight,
  Filter
} from "lucide-react";

export default function Crises() {
  const { 
    personalCrises, eventLog, handleCrisis
  } = useGenesisStore();

  const activeCrises = personalCrises.filter(c => !c.resolved && !c.ignored);
  const resolvedCrises = personalCrises.filter(c => c.resolved);
  const ignoredCrises = personalCrises.filter(c => c.ignored);

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <div className="flex justify-between items-end">
           <div>
             <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono">Incident Control</h1>
             <p className="text-text-secondary text-sm">Critical event surveillance and crisis mitigation management.</p>
           </div>
           <div className="flex gap-2">
              <BackToDashboard />
           </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
           {[
             { label: "Active Crises", value: activeCrises.length, color: "text-signal-red" },
             { label: "Resolved (Total)", value: resolvedCrises.length, color: "text-signal-green" },
             { label: "Ignored (Total)", value: ignoredCrises.length, color: "text-text-muted" },
             { label: "Total Handled", value: personalCrises.length, color: "text-signal-blue" },
           ].map((kpi, i) => (
             <div key={i} className="glass-panel p-3 rounded-lg flex flex-col items-center justify-center text-center">
                <div className="text-[9px] text-text-muted uppercase font-black mb-1">{kpi.label}</div>
                <div className={cn("text-xl font-mono font-black", kpi.color)}>{kpi.value}</div>
             </div>
           ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
           <div className="lg:col-span-8 flex flex-col gap-6">
              <div className="flex items-center justify-between border-b border-border-dim pb-2">
                 <h2 className="text-sm font-bold text-text-primary uppercase flex items-center gap-2">
                    <Emergency size={18} className="text-signal-red" />
                    Active Neural Crises
                 </h2>
                 <span className="px-2 py-0.5 rounded bg-signal-red/10 border border-signal-red/30 text-signal-red text-[9px] font-black animate-pulse">IMMEDIATE ACTION REQUIRED</span>
              </div>

              <div className="space-y-4">
                 {activeCrises.length === 0 ? (
                    <div className="py-20 glass-panel rounded-xl text-center text-text-muted text-xs uppercase tracking-widest border-dashed italic">
                       No Critical Alerts in Buffer
                    </div>
                 ) : (
                    activeCrises.map((crisis, i) => (
                       <motion.div 
                          key={crisis.id}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="glass-panel p-6 rounded-xl border-l-4 border-l-signal-red bg-gradient-to-br from-signal-red/5 to-transparent shadow-2xl relative overflow-hidden"
                       >
                          <div className="flex justify-between items-start mb-6">
                             <div>
                                <div className="flex items-center gap-2 mb-2">
                                   <span className="px-1.5 py-0.5 rounded bg-signal-red/20 text-signal-red text-[9px] font-black border border-signal-red/30 uppercase">SEV-1</span>
                                   <span className="px-1.5 py-0.5 rounded bg-accent/10 text-accent text-[9px] font-black border border-accent/30 uppercase">TARGET: {crisis.target_role}</span>
                                </div>
                                <h3 className="text-lg font-black text-text-primary uppercase tracking-tight">{crisis.description.split('.')[0]}</h3>
                             </div>
                             <div className="text-[10px] font-mono text-text-muted bg-bg-void px-2 py-1 rounded border border-border-dim">
                                T-MINUS {14 - (0)}D
                             </div>
                          </div>

                          <p className="text-sm text-text-secondary leading-relaxed mb-6 font-medium italic">
                             "{crisis.description}"
                          </p>

                          <div className="space-y-4 mb-8">
                             <div>
                                <div className="flex justify-between text-[9px] font-black text-text-muted uppercase mb-1">
                                   <span>Criticality Magnitude</span>
                                   <span className="text-signal-red">{(crisis.severity * 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1 w-full bg-bg-void rounded-full overflow-hidden flex gap-0.5">
                                   {Array.from({ length: 10 }).map((_, idx) => (
                                      <div 
                                         key={idx} 
                                         className={cn(
                                            "flex-1 transition-all duration-1000",
                                            idx < crisis.severity * 10 ? "bg-signal-red" : "bg-border-dim"
                                         )} 
                                      />
                                   ))}
                                </div>
                             </div>
                          </div>

                          <div className="flex gap-3">
                             <button 
                               onClick={() => handleCrisis(crisis.id, "I understand the situation and have a plan to resolve it immediately.")}
                               className="bg-accent text-bg-void font-black text-[10px] uppercase tracking-widest px-6 py-2.5 rounded hover:shadow-[0_0_20px_rgba(45,212,191,0.4)] transition-all"
                             >
                               Intervene Now
                             </button>
                          </div>
                       </motion.div>
                    ))
                 )}
              </div>

              <div className="mt-8">
                 <div className="flex items-center justify-between border-b border-border-dim pb-2 mb-6">
                    <h2 className="text-sm font-bold text-text-primary uppercase flex items-center gap-2 tracking-tight">
                       <History size={18} className="text-text-muted" />
                       Historical Vector Log
                    </h2>
                    <div className="flex gap-2">
                       <button className="p-1.5 rounded border border-accent bg-accent/10 text-accent"><Filter size={14} /></button>
                    </div>
                 </div>
                 
                 <div className="space-y-3 relative before:absolute before:inset-y-0 before:left-[17px] before:w-px before:bg-border-dim/50">
                    {eventLog.slice(0, 10).map((event, i) => (
                       <div key={i} className="flex items-center gap-6 group pl-2">
                          <div className={cn(
                             "w-2 h-2 rounded-full z-10 outline outline-4 outline-bg-void transition-transform group-hover:scale-125",
                             event.type === "positive" ? "bg-signal-green" :
                             event.type === "negative" ? "bg-signal-red" :
                             "bg-signal-blue"
                          )} />
                          <div className="flex-1 glass-panel p-3 rounded-lg flex items-center gap-4 group-hover:border-accent/30 transition-all">
                             <div className="flex flex-col gap-1 flex-1">
                                <div className="flex items-center gap-2">
                                   <span className="text-[8px] font-black text-text-muted uppercase tracking-tighter bg-bg-void px-1 rounded">LOG_{i}</span>
                                   <span className="text-[10px] font-mono text-text-muted">{String(event.day).padStart(3, '0')}</span>
                                </div>
                                <div className="text-[12px] font-medium text-text-primary leading-tight">{event.text}</div>
                             </div>
                             <ChevronRight size={16} className="text-text-muted opacity-0 group-hover:opacity-100 transition-all" />
                          </div>
                       </div>
                    ))}
                 </div>
              </div>
           </div>

           <div className="lg:col-span-4 flex flex-col gap-6">
              <div className="glass-panel p-6 rounded-xl flex-1 flex flex-col">
                 <h3 className="text-sm font-black text-text-primary uppercase mb-6 tracking-tight">Recently Mitigated</h3>
                 <div className="space-y-3">
                    {[...resolvedCrises, ...ignoredCrises].slice(0, 8).map((crisis, i) => (
                       <div key={i} className="p-3 rounded bg-bg-void/40 border border-border-dim flex justify-between items-center opacity-60 hover:opacity-100 transition-opacity">
                          <div className="flex-1 pr-4">
                             <div className={cn(
                                "text-[9px] font-black uppercase mb-1", 
                                crisis.resolved ? "text-signal-green" : "text-text-muted"
                             )}>
                                {crisis.resolved ? "RESOLVED" : "IGNORED"}
                             </div>
                             <div className="text-[11px] font-medium text-text-secondary line-clamp-2">{crisis.description}</div>
                          </div>
                          {crisis.resolved ? (
                             <CheckCircle2 size={16} className="text-signal-green flex-shrink-0" />
                          ) : (
                             <Ban size={16} className="text-text-muted flex-shrink-0" />
                          )}
                       </div>
                    ))}
                    {[...resolvedCrises, ...ignoredCrises].length === 0 && (
                       <div className="text-[10px] text-text-muted uppercase italic text-center py-10">No history available</div>
                    )}
                 </div>
              </div>
           </div>
        </div>
      </div>
    </MainLayout>
  );
}

const Emergency = ({ size, className }: { size: number, className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m18 8-4-4-4 4" /><path d="M2 12h20" /><path d="m6 16 4 4 4-4" />
  </svg>
);
