"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { MainLayout } from "@/components/layout/MainLayout";
import { formatCurrency, cn } from "@/lib/utils";
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line
} from "recharts";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, DollarSign, PieChart, Landmark } from "lucide-react";

export default function Financials() {
  const { 
    cash, mrr, burnRateDaily, investors, episodeId, runwayDays 
  } = useGenesisStore();

  // Mock data for charts - in real app this would come from store history
  const chartData = [
    { day: "D10", cash: 500000, mrr: 0 },
    { day: "D20", cash: 480000, mrr: 1000 },
    { day: "D30", cash: 465000, mrr: 2500 },
    { day: "D40", cash: 452000, mrr: 5000 },
    { day: "D50", cash: 440000, mrr: 8000 },
  ];

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <div className="flex justify-between items-end">
           <div>
             <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono">Financial Command</h1>
             <p className="text-text-secondary text-sm">Liquidity management and investor relations surveillance.</p>
           </div>
           <div className="flex gap-2">
              <button className="px-4 py-2 rounded bg-accent text-bg-void font-bold text-xs uppercase tracking-widest hover:bg-accent-muted transition-colors">
                Recalculate Model
              </button>
           </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
           {[
             { label: "Cash in Bank", value: formatCurrency(cash), icon: DollarSign, color: "text-accent" },
             { label: "Monthly Revenue", value: formatCurrency(mrr), icon: TrendingUp, color: "text-signal-green" },
             { label: "Daily Burn", value: formatCurrency(burnRateDaily), icon: TrendingDown, color: "text-signal-red" },
             { label: "Runway", value: `${runwayDays()} Days`, icon: Landmark, color: "text-signal-amber" },
           ].map((kpi, i) => (
             <div key={i} className="glass-panel p-4 rounded-xl flex items-center gap-4">
                <div className={cn("p-3 rounded-lg bg-bg-void/50 border border-border-dim", kpi.color)}>
                  <kpi.icon size={20} />
                </div>
                <div>
                   <div className="text-[10px] text-text-muted uppercase font-bold tracking-widest">{kpi.label}</div>
                   <div className={cn("text-xl font-mono font-bold", kpi.color)}>{kpi.value}</div>
                </div>
             </div>
           ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
           <div className="lg:col-span-8 flex flex-col gap-6">
              <div className="glass-panel p-6 rounded-xl h-[350px] flex flex-col">
                 <h2 className="text-sm font-bold text-text-primary uppercase mb-6 flex items-center gap-2">
                    <Activity size={16} className="text-accent" />
                    Liquidity Vector (90D Projection)
                 </h2>
                 <div className="flex-1 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                       <AreaChart data={chartData}>
                          <defs>
                             <linearGradient id="colorCash" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#2dd4bf" stopOpacity={0.3}/>
                                <stop offset="95%" stopColor="#2dd4bf" stopOpacity={0}/>
                             </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2a" vertical={false} />
                          <XAxis dataKey="day" stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} />
                          <YAxis stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v/1000}k`} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: "#0c0c10", borderColor: "#1e1e2a", color: "#e4e4e7" }}
                            itemStyle={{ color: "#2dd4bf" }}
                          />
                          <Area type="monotone" dataKey="cash" stroke="#2dd4bf" fillOpacity={1} fill="url(#colorCash)" />
                       </AreaChart>
                    </ResponsiveContainer>
                 </div>
              </div>

              <div className="glass-panel p-6 rounded-xl h-[250px] flex flex-col">
                 <h2 className="text-sm font-bold text-text-primary uppercase mb-6 flex items-center gap-2">
                    <TrendingUp size={16} className="text-signal-green" />
                    Revenue Trajectory
                 </h2>
                 <div className="flex-1 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                       <LineChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2a" vertical={false} />
                          <XAxis dataKey="day" stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} />
                          <YAxis stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v/1000}k`} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: "#0c0c10", borderColor: "#1e1e2a", color: "#e4e4e7" }}
                            itemStyle={{ color: "#22c55e" }}
                          />
                          <Line type="monotone" dataKey="mrr" stroke="#22c55e" strokeWidth={2} dot={{ r: 4, fill: "#22c55e" }} />
                       </LineChart>
                    </ResponsiveContainer>
                 </div>
              </div>
           </div>

           <div className="lg:col-span-4 flex flex-col gap-6">
              <div className="glass-panel p-6 rounded-xl flex flex-col h-full">
                 <div className="flex justify-between items-center mb-6">
                    <h2 className="text-sm font-bold text-text-primary uppercase">Investor Intelligence</h2>
                    <span className="px-2 py-0.5 rounded bg-signal-amber/10 border border-signal-amber/30 text-signal-amber text-[9px] font-bold font-mono">SERIES A</span>
                 </div>
                 
                 <div className="flex-1 space-y-4">
                    {investors.length === 0 ? (
                       <div className="h-full flex items-center justify-center text-text-muted text-xs font-mono uppercase tracking-widest">
                          No Active Leads
                       </div>
                    ) : (
                       investors.map((inv, i) => (
                          <motion.div 
                            key={inv.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                            className="p-4 rounded-lg bg-bg-void/40 border border-border-dim hover:border-accent/30 transition-all group"
                          >
                             <div className="flex justify-between items-start mb-3">
                                <div>
                                   <div className="text-xs font-bold text-text-primary">{inv.name}</div>
                                   <div className="text-[10px] text-text-muted font-mono uppercase tracking-tighter">{inv.thesis}</div>
                                </div>
                                <div className={cn(
                                   "w-2 h-2 rounded-full",
                                   inv.sentiment > 0.6 ? "bg-signal-green" : inv.sentiment > 0.3 ? "bg-signal-amber" : "bg-signal-red"
                                )} />
                             </div>
                             
                             <div className="space-y-2">
                                <div className="flex justify-between text-[10px]">
                                   <span className="text-text-muted uppercase">Sentiment</span>
                                   <span className="text-text-primary font-mono">{(inv.sentiment * 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1 w-full bg-border-dim rounded-full overflow-hidden">
                                   <div 
                                      className={cn(
                                         "h-full transition-all duration-500",
                                         inv.sentiment > 0.6 ? "bg-signal-green" : inv.sentiment > 0.3 ? "bg-signal-amber" : "bg-signal-red"
                                      )}
                                      style={{ width: `${inv.sentiment * 100}%` }}
                                   />
                                </div>
                             </div>

                             <button className="w-full mt-4 py-1.5 rounded border border-border-dim text-[10px] font-bold uppercase text-text-secondary hover:text-accent hover:border-accent/50 transition-all">
                                Negotiate
                             </button>
                          </motion.div>
                       ))
                    )}
                 </div>
              </div>
           </div>
        </div>
      </div>
    </MainLayout>
  );
}

const Activity = ({ size, className }: { size: number, className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);
