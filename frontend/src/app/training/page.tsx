"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { MainLayout } from "@/components/layout/MainLayout";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { 
  BarChart3, 
  ShowChart, 
  Cpu, 
  Target, 
  Zap, 
  ShieldCheck, 
  ArrowDown, 
  ArrowUp,
  Activity,
  History,
  Info
} from "lucide-react";
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { GenesisClient } from "@/lib/genesis-client";
import Link from "next/link";

export default function Training() {
  const { 
    rewardHistory, currentReward, difficulty, episodeId 
  } = useGenesisStore();
  const [completedModels, setCompletedModels] = React.useState<string[]>([]);

  React.useEffect(() => {
    const fetchGenomes = async () => {
      try {
        const client = new GenesisClient();
        const response = await client.callTool("list_founder_genomes", {});
        if (response.model_ids) {
          setCompletedModels(response.model_ids);
        }
      } catch (error) {
        console.error("Failed to fetch genomes:", error);
      }
    };
    fetchGenomes();
  }, []);

  const data = rewardHistory.map((r, i) => ({ step: i, reward: r }));

  if (!episodeId && completedModels.length === 0) {
    return (
      <MainLayout>
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-6">
          <div className="w-20 h-20 bg-accent/10 rounded-full flex items-center justify-center mb-6">
            <Activity size={40} className="text-accent animate-pulse" />
          </div>
          <h1 className="text-3xl font-black text-text-primary uppercase mb-2">Inference Buffer Empty</h1>
          <p className="text-text-secondary max-w-md mb-8">
            No active training session detected. Start a new episode from the Dashboard or run <code className="bg-bg-void px-2 py-1 rounded text-accent">uv run train.py</code> to begin.
          </p>
          <div className="flex gap-4">
            <Link href="/" className="px-6 py-3 bg-accent text-bg-void font-black uppercase tracking-widest rounded hover:brightness-110 transition-all">
              Go to Dashboard
            </Link>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <div className="flex justify-between items-end">
           <div>
             <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono">Neural Training Analytics</h1>
             <p className="text-text-secondary text-sm">Real-time surveillance of reinforcement learning convergence and model weights.</p>
           </div>
           <div className="flex gap-2">
              <button className="px-4 py-2 rounded bg-accent/10 border border-accent/30 text-accent font-bold text-xs uppercase tracking-widest hover:bg-accent/20 transition-all flex items-center gap-2">
                <Cpu size={16} />
                Export Model
              </button>
           </div>
        </div>

        {/* ... (rest of the KPIs) */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
           {[
             { label: "Current Reward", value: currentReward?.toFixed(4) || "0.0000", icon: Zap, color: "text-accent" },
             { label: "Steps in Episode", value: data.length.toString(), icon: History, color: "text-text-primary" },
             { label: "Current Level", value: `Lvl ${difficulty || 1}`, icon: ArrowUp, color: "text-signal-green" },
             { label: "Completed Models", value: completedModels.length.toString(), icon: Target, color: "text-signal-green" },
             { label: "Exploration ε", value: "0.05", icon: Info, color: "text-signal-blue" },
             { label: "Compute Status", value: episodeId ? "ACTIVE" : "IDLE", icon: Activity, color: episodeId ? "text-signal-green" : "text-text-muted" },
           ].map((kpi, i) => (
             <div key={i} className="glass-panel p-4 rounded-xl flex flex-col justify-between h-[110px] relative overflow-hidden group hover:border-accent/40 transition-all">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-accent opacity-20 group-hover:opacity-100 transition-opacity" />
                <div className="text-[9px] text-text-muted uppercase font-black tracking-widest">{kpi.label}</div>
                <div className="flex items-baseline gap-2">
                   <div className={cn("text-xl font-mono font-black", kpi.color)}>{kpi.value}</div>
                   <kpi.icon size={14} className={kpi.color} />
                </div>
             </div>
           ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
           <div className="lg:col-span-8 glass-panel active p-6 rounded-xl flex flex-col h-[600px] relative overflow-hidden">
              <div className="flex justify-between items-center mb-8">
                 <h2 className="text-sm font-black text-text-primary uppercase flex items-center gap-2">
                    <ShowChart size={18} className="text-accent" />
                    {episodeId ? `Session ${episodeId.slice(0, 8)} Reward History` : "Historical Data Stream"}
                 </h2>
                 <div className="flex gap-2">
                    <button className="px-3 py-1 text-[9px] font-black text-accent border border-accent/30 rounded bg-accent/10 uppercase tracking-widest">REALTIME</button>
                 </div>
              </div>

              <div className="flex-1 w-full relative">
                 {data.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-text-muted uppercase tracking-widest text-[10px] flex-col gap-4">
                       <div className="w-12 h-12 border-2 border-accent/20 border-t-accent rounded-full animate-spin" />
                       Awaiting Data Pulse...
                    </div>
                 ) : (
                    <ResponsiveContainer width="100%" height="100%">
                       <AreaChart data={data}>
                          <defs>
                             <linearGradient id="colorReward" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#2dd4bf" stopOpacity={0.3}/>
                                <stop offset="95%" stopColor="#2dd4bf" stopOpacity={0}/>
                             </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2a" vertical={false} />
                          <XAxis dataKey="step" hide />
                          <YAxis stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: "#0c0c10", borderColor: "#1e1e2a", color: "#e4e4e7" }}
                          />
                          <Area type="monotone" dataKey="reward" stroke="#2dd4bf" strokeWidth={2} fillOpacity={1} fill="url(#colorReward)" />
                       </AreaChart>
                    </ResponsiveContainer>
                 )}
              </div>
           </div>

           <div className="lg:col-span-4 flex flex-col gap-6">
              <div className="glass-panel p-6 rounded-xl flex flex-col h-[280px]">
                 <h3 className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-signal-blue animate-pulse" />
                    Completed Founders
                 </h3>
                 <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                    {completedModels.length === 0 ? (
                      <div className="text-[10px] text-text-muted uppercase tracking-widest py-10 text-center">No genomes exported yet.</div>
                    ) : (
                      completedModels.map((mid, i) => (
                        <div key={i} className="flex items-center justify-between group p-2 hover:bg-accent/5 rounded transition-colors">
                           <div className="flex items-center gap-3">
                              <Cpu size={14} className="text-accent" />
                              <div className="text-[11px] font-mono text-text-primary uppercase">{mid}</div>
                           </div>
                           <div className="text-[9px] text-accent font-black uppercase opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">View Genome</div>
                        </div>
                      ))
                    )}
                 </div>
              </div>

              <div className="glass-panel p-6 rounded-xl flex-1 flex flex-col">
                 <div className="flex justify-between items-center mb-6">
                    <h3 className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em]">Training Protocol</h3>
                    <span className="px-2 py-0.5 bg-bg-void border border-border-dim text-[9px] font-mono rounded text-text-secondary uppercase">v.3.0.0</span>
                 </div>
                 
                 <div className="grid grid-cols-2 gap-x-4 gap-y-6 flex-1">
                    {[
                       { label: "Type", value: "GRPO / Adaptive" },
                       { label: "Observation Space", value: "Box(0, 1, (256,))" },
                       { label: "Reward Engine", value: "11-Component Rubric" },
                       { label: "Learning Rate", value: "5e-5" },
                    ].map((item, i) => (
                       <div key={i}>
                          <div className="text-[9px] text-text-muted uppercase font-black mb-1">{item.label}</div>
                          <div className="text-[11px] font-mono text-text-primary">{item.value}</div>
                       </div>
                    ))}
                    
                    <div className="col-span-2 pt-4 border-t border-border-dim/50">
                       <div className="flex justify-between text-[9px] font-black text-text-muted uppercase mb-2">
                          <span>Convergence Velocity</span>
                          <span className={cn("font-black", episodeId ? "text-signal-green" : "text-text-muted")}>
                            {episodeId ? "58% STABLE" : "IDLE"}
                          </span>
                       </div>
                       <div className="flex gap-1 h-1.5 w-full bg-bg-void rounded-full overflow-hidden border border-border-dim">
                          <div className="h-full bg-signal-green" style={{ width: episodeId ? "58%" : "0%" }} />
                          <div className="h-full bg-signal-red opacity-30" style={{ width: episodeId ? "42%" : "0%" }} />
                       </div>
                    </div>
                 </div>

                 <button className="w-full mt-8 py-2.5 bg-accent/10 border border-accent/30 text-accent font-black text-[10px] uppercase tracking-widest rounded hover:bg-accent/20 transition-all flex items-center justify-center gap-2">
                    <Activity size={14} />
                    {episodeId ? "Pause Inference" : "Awaiting Client"}
                 </button>
              </div>
           </div>
        </div>
      </div>
    </MainLayout>
  );
}

const ShowChart = ({ size, className }: { size: number, className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-3 3" />
  </svg>
);

const Emergency = ({ size, className }: { size: number, className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m18 8-4-4-4 4" /><path d="M2 12h20" /><path d="m6 16 4 4 4-4" />
  </svg>
);
