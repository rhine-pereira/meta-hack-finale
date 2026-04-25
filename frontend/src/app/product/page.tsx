"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { MainLayout } from "@/components/layout/MainLayout";
import { BackToDashboard } from "@/components/navigation/BackToDashboard";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { 
  Cpu, 
  Rocket, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  Code2, 
  History, 
  Activity,
  PlusSquare
} from "lucide-react";

export default function Product() {
  const { 
    productMaturity, techDebt, featuresShipped, uptime, pendingFeatures,
    buildFeature 
  } = useGenesisStore();

  const handleBuildFeature = () => {
    const name = prompt("Feature Name?", "Autonomous Scale Engine");
    if (!name) return;
    buildFeature(name, "medium", 1);
  };

  const statuses = [
    { label: "Pending", items: pendingFeatures.filter(f => f.days_remaining > 0 && f.engineers_assigned === 0) },
    { label: "In Progress", items: pendingFeatures.filter(f => f.engineers_assigned > 0) },
    { label: "Shipped", items: Array.from({ length: 5 }).map((_, i) => ({ name: `Feature ${featuresShipped - i}`, complexity: "medium" })) } // Mocking history
  ];

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <div className="flex justify-between items-end">
           <div>
             <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono">Product Matrix</h1>
             <p className="text-text-secondary text-sm">Engineering velocity and system architecture integrity.</p>
           </div>
           <div className="flex gap-2">
              <BackToDashboard />
              <button 
                onClick={handleBuildFeature}
                className="px-4 py-2 rounded bg-accent text-bg-void font-bold text-xs uppercase tracking-widest hover:bg-accent-glow transition-colors flex items-center gap-2"
              >
                <PlusSquare size={16} />
                Build Feature
              </button>
           </div>
        </div>

        <div className="grid grid-cols-12 gap-6 h-full">
           <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
              <div className="glass-panel p-6 rounded-xl flex flex-col items-center text-center relative overflow-hidden group">
                 <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                    <ShieldAlert size={80} />
                 </div>
                 <h3 className="text-[10px] text-text-muted font-bold uppercase tracking-widest mb-4">Tech Debt Gauge</h3>
                 <div className="relative w-32 h-16 mb-4 overflow-hidden border-t-4 border-l-4 border-r-4 border-signal-amber rounded-t-full">
                    <motion.div 
                       className="absolute bottom-0 left-1/2 w-0.5 h-12 bg-text-primary origin-bottom"
                       animate={{ rotate: (techDebt * 180) - 90 }}
                       transition={{ type: "spring", stiffness: 50 }}
                       style={{ translateX: "-50%" }}
                    />
                 </div>
                 <div className={cn("text-3xl font-mono font-bold", techDebt > 0.6 ? "text-signal-red" : "text-signal-amber")}>
                    {(techDebt * 100).toFixed(0)}%
                 </div>
                 <div className="text-[10px] text-text-muted uppercase mt-1">System Entropy Level</div>
              </div>

              <div className="glass-panel p-6 rounded-xl">
                 <div className="flex justify-between items-center mb-4">
                    <h3 className="text-[10px] text-text-muted font-bold uppercase tracking-widest">Uptime</h3>
                    <div className="flex items-center gap-2">
                       <span className="w-2 h-2 rounded-full bg-signal-green animate-pulse" />
                       <span className="text-[10px] text-signal-green font-mono">ONLINE</span>
                    </div>
                 </div>
                 <div className="text-3xl font-mono font-bold text-accent mb-2">{(uptime * 100).toFixed(1)}%</div>
                 <div className="h-1.5 w-full bg-bg-void rounded-full overflow-hidden border border-border-dim">
                    <div className="h-full bg-signal-green" style={{ width: `${uptime * 100}%` }} />
                 </div>
              </div>

              <div className="flex flex-col gap-2 mt-auto">
                 <button className="w-full py-3 bg-accent/10 border border-accent/30 text-accent font-bold text-[10px] uppercase rounded hover:bg-accent/20 transition-all flex items-center justify-center gap-2">
                    <Activity size={14} />
                    Run Load Test
                 </button>
                 <button className="w-full py-3 bg-signal-blue/10 border border-signal-blue/30 text-signal-blue font-bold text-[10px] uppercase rounded hover:bg-signal-blue/20 transition-all flex items-center justify-center gap-2">
                    <Rocket size={14} />
                    Deploy v{featuresShipped}.{featuresShipped % 10}
                 </button>
              </div>
           </div>

           <div className="col-span-12 lg:col-span-9 flex flex-col gap-6">
              <div className="glass-panel p-6 rounded-xl flex-1 flex flex-col">
                 <div className="flex justify-between items-center mb-8 pb-4 border-b border-border-dim">
                    <h2 className="text-sm font-bold text-text-primary uppercase flex items-center gap-2">
                       <Code2 size={18} className="text-accent" />
                       Feature Pipeline
                    </h2>
                 </div>

                 <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1">
                    {statuses.map((col, i) => (
                       <div key={i} className="flex flex-col gap-4">
                          <div className="flex justify-between items-center text-[10px] text-text-muted font-bold uppercase tracking-widest mb-2 px-1">
                             <span>{col.label}</span>
                             <span className="bg-bg-void px-2 py-0.5 rounded border border-border-dim">{col.items.length}</span>
                          </div>
                          
                          <div className="space-y-3">
                             {col.items.length === 0 ? (
                                <div className="p-8 border border-dashed border-border-dim rounded-lg text-center text-text-muted text-[10px] uppercase">
                                   No items
                                </div>
                             ) : (
                                col.items.map((item, idx) => (
                                   <motion.div 
                                      key={idx}
                                      initial={{ opacity: 0, y: 10 }}
                                      animate={{ opacity: 1, y: 0 }}
                                      className={cn(
                                         "p-4 rounded-lg bg-bg-void/60 border border-border-dim transition-all hover:border-accent/40 group",
                                         col.label === "In Progress" && "border-accent/30 shadow-[0_0_15px_rgba(45,212,191,0.05)]"
                                      )}
                                   >
                                      <div className="text-xs font-bold text-text-primary mb-3 group-hover:text-accent transition-colors">{(item as any).name}</div>
                                      <div className="flex justify-between items-center">
                                         <span className={cn(
                                            "px-2 py-0.5 rounded-[4px] text-[9px] font-bold uppercase",
                                            (item as any).complexity === "high" ? "bg-signal-red/10 text-signal-red" :
                                            (item as any).complexity === "medium" ? "bg-signal-amber/10 text-signal-amber" :
                                            "bg-signal-green/10 text-signal-green"
                                         )}>
                                            {(item as any).complexity}
                                         </span>
                                         {(item as any).days_remaining && (
                                            <div className="flex items-center gap-1 text-[10px] text-text-muted font-mono">
                                               <Clock size={10} />
                                               {(item as any).days_remaining}d
                                            </div>
                                         )}
                                      </div>
                                      {(item as any).days_remaining && (
                                         <div className="mt-3 h-1 w-full bg-bg-void rounded-full overflow-hidden border border-border-dim">
                                            <div className="h-full bg-accent" style={{ width: "40%" }} />
                                         </div>
                                      )}
                                   </motion.div>
                                ))
                             )}
                          </div>
                       </div>
                    ))}
                 </div>
              </div>

              <div className="glass-panel p-6 rounded-xl h-48">
                 <h2 className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-4 flex items-center gap-2">
                    <History size={14} />
                    Deploy History
                 </h2>
                 <div className="space-y-3">
                    <div className="flex items-center gap-4 p-3 rounded bg-bg-void/50 border border-border-dim border-l-2 border-l-signal-green">
                       <CheckCircle2 size={16} className="text-signal-green" />
                       <div className="flex-1">
                          <div className="text-[11px] font-bold text-text-primary">v2.0.4 - System Stability Patch</div>
                          <div className="text-[9px] text-text-muted uppercase">Successfully deployed 12m ago</div>
                       </div>
                       <span className="text-[9px] font-mono text-signal-green bg-signal-green/10 px-1.5 py-0.5 rounded">SUCCESS</span>
                    </div>
                    <div className="flex items-center gap-4 p-3 rounded bg-bg-void/50 border border-border-dim border-l-2 border-l-signal-red opacity-70">
                       <ShieldAlert size={16} className="text-signal-red" />
                       <div className="flex-1">
                          <div className="text-[11px] font-bold text-text-primary">v2.0.3 - Auth Layer Rollout</div>
                          <div className="text-[9px] text-text-muted uppercase">Rolled back 2h ago - High Latency Detected</div>
                       </div>
                       <span className="text-[9px] font-mono text-signal-red bg-signal-red/10 px-1.5 py-0.5 rounded">FAILED</span>
                    </div>
                 </div>
              </div>
           </div>
        </div>
      </div>
    </MainLayout>
  );
}
