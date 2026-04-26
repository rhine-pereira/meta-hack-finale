"use client";

import React, { useState } from "react";
import { useGenesisStore } from "@/lib/store";
import { MainLayout } from "@/components/layout/MainLayout";
import { BackToDashboard } from "@/components/navigation/BackToDashboard";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { 
  BrainCircuit, 
  Search, 
  Database, 
  Code, 
  History, 
  TableProperties,
  ArrowRight,
  PlusCircle,
  FileCode,
  Zap
} from "lucide-react";

export default function Brain() {
  const { 
    companyBrain, employees, cofounderAlignment, injectMemory
  } = useGenesisStore();

  const handleInjectMemory = () => {
    const key = prompt("Memory Key?", "strategic_pivot_2026");
    const value = prompt("Memory Value?", "Focus on vertical integration of AI agents.");
    if (!key || !value) return;
    injectMemory(key, value);
  };

  const [search, setSearch] = useState("");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const keys = Object.keys(companyBrain).filter(k => 
    k.toLowerCase().includes(search.toLowerCase()) || 
    companyBrain[k].toLowerCase().includes(search.toLowerCase())
  );

  const storageUsed = (JSON.stringify(companyBrain).length / 1024).toFixed(1);

  return (
    <MainLayout>
      <div className="flex flex-col gap-6 h-[calc(100vh-120px)]">
        <div className="flex justify-between items-end flex-none">
           <div>
             <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono">Cognitive Core</h1>
             <p className="text-text-secondary text-sm">Central repository for shared strategic memory and agent directives.</p>
           </div>
           <div className="flex gap-2">
              <BackToDashboard />
              <button 
                onClick={handleInjectMemory}
                className="px-4 py-2 rounded bg-accent text-bg-void font-bold text-xs uppercase tracking-widest hover:bg-accent-glow transition-colors flex items-center gap-2 shadow-[0_0_15px_rgba(45,212,191,0.2)]"
              >
                <PlusCircle size={16} />
                Inject Memory
              </button>
           </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 flex-none">
           {[
             { label: "Total Keys", value: Object.keys(companyBrain).length, icon: Database, color: "text-accent" },
             { label: "Storage Used", value: `${storageUsed} KB`, icon: BrainCircuit, color: "text-signal-purple" },
             { label: "Founder Alignment", value: `${(cofounderAlignment * 100).toFixed(0)}%`, icon: Zap, color: "text-signal-green" },
           ].map((kpi, i) => (
             <div key={i} className="glass-panel p-4 rounded-xl flex items-center gap-4">
                <div className={cn("p-3 rounded-lg bg-bg-void/50 border border-border-dim", kpi.color)}>
                  <kpi.icon size={20} />
                </div>
                <div>
                   <div className="text-[10px] text-text-muted uppercase font-bold tracking-widest">{kpi.label}</div>
                   <div className={cn("text-lg font-mono font-black", kpi.color)}>{kpi.value}</div>
                </div>
             </div>
           ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 flex-1 min-h-0">
           <div className="xl:col-span-7 flex flex-col gap-6 min-h-0">
              <div className="glass-panel rounded-xl flex flex-col flex-1 overflow-hidden shadow-2xl relative">
                 <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-accent/30 to-transparent" />
                 
                 <div className="p-4 border-b border-border-dim flex justify-between items-center bg-bg-surface/90 backdrop-blur z-10">
                    <div className="flex items-center gap-2 text-accent">
                       <TableProperties size={18} />
                       <h2 className="text-sm font-bold text-text-primary m-0 uppercase tracking-tight">Memory Registry</h2>
                    </div>
                    <div className="flex items-center gap-3">
                       <div className="relative">
                          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                          <input 
                             type="text" 
                             placeholder="Search vectors..."
                             className="bg-bg-void border border-border-dim text-text-primary text-xs rounded-full py-1.5 pl-9 pr-4 focus:border-accent focus:ring-1 focus:ring-accent/20 outline-none w-48 transition-all"
                             value={search}
                             onChange={(e) => setSearch(e.target.value)}
                          />
                       </div>
                    </div>
                 </div>

                 <div className="flex-1 overflow-y-auto custom-scrollbar bg-bg-void/20">
                    <table className="w-full text-left border-collapse">
                       <thead className="bg-bg-void border-b border-border-dim text-[9px] text-text-muted uppercase font-black sticky top-0 z-20">
                          <tr>
                             <th className="py-3 px-6 w-2/5">Vector Designation</th>
                             <th className="py-3 px-6 w-1/5">Encoding</th>
                             <th className="py-3 px-6 text-right">Magnitude</th>
                          </tr>
                       </thead>
                       <tbody className="text-xs font-mono divide-y divide-border-dim/50">
                          {keys.length === 0 ? (
                             <tr><td colSpan={3} className="py-20 text-center text-text-muted uppercase tracking-widest italic">Core is Vacant</td></tr>
                          ) : (
                             keys.map((key) => (
                                <motion.tr 
                                   key={key}
                                   onClick={() => setSelectedKey(key)}
                                   className={cn(
                                      "hover:bg-accent/5 cursor-pointer transition-colors group",
                                      selectedKey === key && "bg-accent/10 border-l-2 border-l-accent"
                                   )}
                                >
                                   <td className="py-3 px-6">
                                      <span className={cn(
                                         "transition-colors",
                                         selectedKey === key ? "text-accent" : "text-text-secondary group-hover:text-text-primary"
                                      )}>{key}</span>
                                   </td>
                                   <td className="py-3 px-6">
                                      <span className="px-1.5 py-0.5 rounded bg-bg-elevated text-[9px] border border-border-dim">RAW</span>
                                   </td>
                                   <td className="py-3 px-6 text-right text-text-muted">
                                      {companyBrain[key].length}B
                                   </td>
                                </motion.tr>
                             ))
                          )}
                       </tbody>
                    </table>
                 </div>
              </div>
           </div>

           <div className="xl:col-span-5 flex flex-col gap-6 min-h-0 h-full">
              <div className="glass-panel border-border-active rounded-xl flex flex-col flex-1 shadow-[0_0_30px_rgba(45,212,191,0.05)] relative overflow-hidden">
                 <div className="absolute top-0 left-0 w-full h-[1px] bg-accent/40" />
                 <div className="px-4 py-3 border-b border-border-active flex justify-between items-center bg-bg-elevated z-10">
                    <div className="flex items-center gap-2">
                       <FileCode size={14} className="text-accent" />
                       <span className="text-[11px] font-mono text-text-primary opacity-80 uppercase tracking-widest">{selectedKey ?? "Vector Inspector"}</span>
                    </div>
                    <div className="flex gap-2">
                       <button className="text-text-muted hover:text-text-primary transition-colors">
                          <History size={14} />
                       </button>
                    </div>
                 </div>
                 
                 <div className="flex-1 p-6 overflow-auto bg-bg-void/80 font-mono text-sm leading-relaxed">
                    {selectedKey ? (
                       <div className="space-y-4">
                          <div className="text-accent font-bold pb-2 border-b border-accent/20">DATA PAYLOAD</div>
                          <pre className="text-text-primary whitespace-pre-wrap">
                             {companyBrain[selectedKey]}
                          </pre>
                       </div>
                    ) : (
                       <div className="h-full flex flex-col items-center justify-center text-center opacity-30 grayscale">
                          <BrainCircuit size={64} className="mb-4 text-accent animate-pulse" />
                          <div className="text-xs uppercase tracking-widest">Select a vector to inspect its content</div>
                       </div>
                    )}
                 </div>
              </div>

              <div className="glass-panel p-6 rounded-xl h-64 flex flex-none flex-col gap-4">
                 <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-text-primary">
                       <History size={16} />
                       <h3 className="text-[10px] font-bold uppercase tracking-widest m-0">Write Operations Log</h3>
                    </div>
                    <span className="text-[10px] text-signal-green flex items-center gap-1">
                       <span className="w-1.5 h-1.5 rounded-full bg-signal-green animate-pulse" /> LIVE
                    </span>
                 </div>
                 
                 <div className="flex-1 overflow-y-auto space-y-4 border-l border-border-dim/50 ml-2 pl-4 relative">
                    {keys.slice(0, 5).map((key, i) => (
                       <div key={i} className="relative group">
                          <div className="absolute -left-[21px] top-1 w-2 h-2 rounded-full bg-accent shadow-[0_0_8px_rgba(45,212,191,0.5)] border-2 border-bg-surface" />
                          <div className="flex flex-col gap-0.5">
                             <div className="flex items-center justify-between w-full">
                                <span className="text-[10px] font-black text-accent uppercase">UPDATE</span>
                                <span className="text-[9px] font-mono text-text-muted">DAY {String(i).padStart(3, "0")}</span>
                             </div>
                             <span className="text-[11px] font-mono text-text-primary truncate">{key}</span>
                          </div>
                       </div>
                    ))}
                 </div>
              </div>
           </div>
        </div>
      </div>
    </MainLayout>
  );
}

const ShieldCheck = ({ size, className }: { size: number, className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
    <path d="m9 12 2 2 4-4" />
  </svg>
);
