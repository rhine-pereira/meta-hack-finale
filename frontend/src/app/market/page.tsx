"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { MainLayout } from "@/components/layout/MainLayout";
import { BackToDashboard } from "@/components/navigation/BackToDashboard";
import { formatCurrency, cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { 
  Target, 
  TrendingUp, 
  Users, 
  Search, 
  Mail, 
  PieChart, 
  ShieldCheck, 
  ArrowUpRight,
  Globe
} from "lucide-react";

export default function Market() {
  const { 
    customers, competitors, mrr, analyzeMarket
  } = useGenesisStore();

  const handleAnalyzeMarket = () => {
    analyzeMarket("Enterprise SaaS");
  };

  const totalArr = mrr * 12;

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <div className="flex justify-between items-end">
           <div>
             <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono">Market Intelligence</h1>
             <p className="text-text-secondary text-sm">Real-time surveillance of customer health and competitor vectors.</p>
           </div>
           <div className="flex gap-2">
              <BackToDashboard />
              <button className="px-4 py-2 rounded glass-panel text-text-primary border border-border-dim font-bold text-xs uppercase tracking-widest hover:border-accent/50 hover:bg-accent/5 transition-all flex items-center gap-2">
                <Mail size={16} />
                Email Customer
              </button>
              <button 
                onClick={handleAnalyzeMarket}
                className="px-4 py-2 rounded bg-accent text-bg-void font-bold text-xs uppercase tracking-widest hover:bg-accent-glow transition-colors flex items-center gap-2 shadow-[0_0_15px_rgba(45,212,191,0.2)]"
              >
                <Search size={16} />
                Analyze Market
              </button>
           </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
           <div className="lg:col-span-2 glass-panel p-6 rounded-xl relative overflow-hidden group hover:border-accent/30 transition-all">
              <div className="absolute right-0 top-0 w-64 h-full bg-gradient-to-l from-accent/5 to-transparent pointer-events-none" />
              <div className="flex justify-between items-start mb-6">
                 <div>
                    <div className="text-[10px] text-text-muted font-bold uppercase tracking-widest mb-2 flex items-center gap-2">
                       <PieChart size={14} className="text-accent" />
                       Total Addressable Market (TAM)
                    </div>
                    <div className="text-4xl font-black text-text-primary tracking-tighter font-mono">$500M</div>
                 </div>
                 <Globe size={40} className="text-accent/10 group-hover:text-accent/20 transition-all duration-500" />
              </div>
              <div className="mt-8 flex items-center justify-between border-t border-border-dim/50 pt-4">
                 <div className="flex items-center gap-2 text-signal-green bg-signal-green/10 px-2 py-1 rounded border border-signal-green/20 text-[11px] font-bold">
                    <TrendingUp size={14} /> +14.2% YoY Growth
                 </div>
                 <div className="text-[10px] text-text-muted font-mono uppercase">Expansion Vector: Enterprise SaaS</div>
              </div>
           </div>

           <div className="grid grid-rows-2 gap-6">
              <div className="glass-panel p-5 rounded-xl flex flex-col justify-center relative overflow-hidden">
                 <div className="absolute bottom-0 left-0 w-full h-[2px] bg-border-dim">
                    <div className="h-full bg-accent" style={{ width: "7.8%" }} />
                 </div>
                 <div className="text-[10px] text-text-muted font-bold uppercase tracking-widest mb-1">Market Penetration</div>
                 <div className="text-2xl font-black text-accent font-mono">7.8%</div>
              </div>
              <div className="glass-panel p-5 rounded-xl flex flex-col justify-center relative overflow-hidden">
                 <div className="absolute bottom-0 left-0 w-full h-[2px] bg-border-dim">
                    <div className="h-full bg-signal-amber" style={{ width: "42%" }} />
                 </div>
                 <div className="text-[10px] text-text-muted font-bold uppercase tracking-widest mb-1">Avg Churn Velocity</div>
                 <div className="text-2xl font-black text-signal-amber font-mono">1.2% / mo</div>
              </div>
           </div>
        </div>

        <div className="glass-panel rounded-xl overflow-hidden shadow-2xl">
           <div className="p-4 border-b border-border-dim flex items-center justify-between bg-bg-surface/50">
              <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] flex items-center gap-2">
                 <Heart size={14} className="text-accent" />
                 Customer Health Matrix
              </h2>
              <span className="text-[9px] text-text-muted font-mono uppercase tracking-widest">Active Accounts: {customers.length}</span>
           </div>
           
           <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                 <thead className="bg-bg-void/50 border-b border-border-dim text-[9px] text-text-muted uppercase font-black">
                    <tr>
                       <th className="py-4 px-6">Entity Designation</th>
                       <th className="py-4 px-6">ARR Pipeline</th>
                       <th className="py-4 px-6">Satisfaction Index</th>
                       <th className="py-4 px-6">Churn Probability</th>
                       <th className="py-4 px-6 text-right">Action Vector</th>
                    </tr>
                 </thead>
                 <tbody className="text-xs divide-y divide-border-dim/50">
                    {customers.length === 0 ? (
                       <tr><td colSpan={5} className="py-12 text-center text-text-muted uppercase tracking-widest border-dashed">No Active Contracts</td></tr>
                    ) : (
                       customers.map((cust, i) => (
                          <motion.tr 
                             key={cust.id}
                             initial={{ opacity: 0 }}
                             animate={{ opacity: 1 }}
                             transition={{ delay: i * 0.05 }}
                             className="hover:bg-bg-hover/40 transition-colors group"
                          >
                             <td className="py-4 px-6 font-bold text-text-primary group-hover:text-accent transition-colors">{cust.name}</td>
                             <td className="py-4 px-6 font-mono text-text-secondary">{formatCurrency(cust.arr)}</td>
                             <td className="py-4 px-6">
                                <div className="flex items-center gap-3">
                                   <span className={cn(
                                      "w-6 text-right font-mono font-bold",
                                      cust.satisfaction > 0.7 ? "text-signal-green" : cust.satisfaction > 0.4 ? "text-signal-amber" : "text-signal-red"
                                   )}>
                                      {(cust.satisfaction * 100).toFixed(0)}
                                   </span>
                                   <div className="flex-1 max-w-[100px] h-1 bg-border-dim rounded-full overflow-hidden flex">
                                      <div 
                                         className={cn("h-full", cust.satisfaction > 0.7 ? "bg-signal-green" : cust.satisfaction > 0.4 ? "bg-signal-amber" : "bg-signal-red")} 
                                         style={{ width: `${cust.satisfaction * 100}%` }} 
                                      />
                                   </div>
                                </div>
                             </td>
                             <td className="py-4 px-6">
                                <span className={cn(
                                   "inline-block px-2 py-0.5 rounded-[4px] font-bold text-[9px] border",
                                   cust.churn_risk < 0.2 ? "bg-signal-green/10 text-signal-green border-signal-green/20" :
                                   cust.churn_risk < 0.5 ? "bg-signal-amber/10 text-signal-amber border-signal-amber/20" :
                                   "bg-signal-red/10 text-signal-red border-signal-red/20 animate-pulse"
                                )}>
                                   {cust.churn_risk < 0.2 ? "LOW" : cust.churn_risk < 0.5 ? "MEDIUM" : "CRITICAL"}
                                </span>
                             </td>
                             <td className="py-4 px-6 text-right">
                                <button className="text-text-muted hover:text-accent transition-colors">
                                   <ArrowUpRight size={18} />
                                </button>
                             </td>
                          </motion.tr>
                       ))
                    )}
                 </tbody>
              </table>
           </div>
        </div>

        <div className="mt-4">
           <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] flex items-center gap-2 mb-4">
              <Target size={14} className="text-role-cto" />
              Competitor Intelligence
           </h2>
           <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {competitors.length === 0 ? (
                 <div className="col-span-full py-12 glass-panel rounded-xl text-center text-text-muted text-[10px] uppercase border-dashed">No Intelligence Gathered</div>
              ) : (
                 competitors.map((comp, i) => (
                    <motion.div 
                       key={comp.id}
                       initial={{ opacity: 0, scale: 0.98 }}
                       animate={{ opacity: 1, scale: 1 }}
                       transition={{ delay: i * 0.1 }}
                       className="glass-panel p-5 rounded-xl hover:border-border-active transition-all group"
                    >
                       <div className="flex justify-between items-start mb-6">
                          <div>
                             <div className="text-[9px] text-text-muted font-bold uppercase tracking-widest mb-1">Threat Level: {comp.strength > 0.7 ? "High" : comp.strength > 0.4 ? "Medium" : "Emerging"}</div>
                             <div className="text-lg font-black text-text-primary group-hover:text-accent transition-colors font-mono">{comp.name}</div>
                          </div>
                          <div className={cn(
                             "p-2 rounded-lg bg-bg-void/50 border border-border-dim",
                             comp.strength > 0.7 ? "text-signal-red" : "text-signal-amber"
                          )}>
                             <Target size={20} />
                          </div>
                       </div>
                       
                       <div className="space-y-4 mb-6">
                          <div>
                             <div className="flex justify-between text-[9px] text-text-muted font-bold uppercase mb-1">
                                <span>Feature Parity</span>
                                <span className="text-text-primary">{(comp.strength * 100).toFixed(0)}%</span>
                             </div>
                             <div className="h-1 bg-border-dim rounded-full overflow-hidden">
                                <div 
                                   className={cn("h-full", comp.strength > 0.7 ? "bg-signal-red" : "bg-signal-amber")} 
                                   style={{ width: `${comp.strength * 100}%` }} 
                                />
                             </div>
                          </div>
                       </div>

                       <div className="p-3 bg-bg-void/60 border border-border-dim rounded-lg text-[10px] font-mono leading-relaxed group-hover:border-accent/20 transition-all">
                          <span className="text-accent mr-1 font-bold">LATEST MOVE:</span>
                          <span className="text-text-secondary">{comp.recent_move ?? "No recent updates detected."}</span>
                       </div>
                    </motion.div>
                 ))
              )}
           </div>
        </div>
      </div>
    </MainLayout>
  );
}

const Heart = ({ size, className }: { size: number, className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
  </svg>
);
