"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { MainLayout } from "@/components/layout/MainLayout";
import { BackToDashboard } from "@/components/navigation/BackToDashboard";
import { formatCurrency, cn } from "@/lib/utils";
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  PieChart, 
  Landmark,
  Activity
} from "lucide-react";

export default function Financials() {
  const { 
    cash, mrr, burnRateDaily, investors, valuation, runwayDays, 
    negotiateWithInvestor, createFinancialModel
  } = useGenesisStore();

  const handleRecalculate = async () => {
    await createFinancialModel({ 
      projection_days: 90,
      include_risk_factors: true
    });
    alert("Financial model recalculated based on current state.");
  };

  const handleNegotiate = async (invId: string, invName: string) => {
    const offerVal = prompt(`Enter valuation offer for ${invName} (Current: ${formatCurrency(valuation)})`, String(valuation));
    if (!offerVal) return;
    const equity = prompt(`Enter equity offer (e.g. 0.1 for 10%)`, "0.1");
    if (!equity) return;

    await negotiateWithInvestor(invId, Number(offerVal), Number(equity));
    alert(`Negotiation initiated with ${invName}`);
  };

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <div className="flex justify-between items-end">
           <div>
             <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono">Financial Command</h1>
             <p className="text-text-secondary text-sm">Liquidity management and investor relations surveillance.</p>
           </div>
           <div className="flex gap-2">
              <BackToDashboard />
              <button 
                onClick={handleRecalculate}
                className="px-4 py-2 rounded bg-accent text-bg-void font-bold text-xs uppercase tracking-widest hover:bg-accent-muted transition-colors"
              >
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
              <div className="glass-panel p-8 rounded-xl flex-1 flex flex-col justify-center items-center text-center border-dashed border-2 border-border-dim/50">
                 <div className="p-6 rounded-full bg-accent/5 border border-accent/10 mb-6">
                    <PieChart size={48} className="text-accent opacity-20" />
                 </div>
                 <h2 className="text-lg font-black text-text-primary uppercase mb-2 tracking-tight">
                    Financial Model Active
                 </h2>
                 <p className="text-text-muted text-sm max-w-md mb-8">
                    Projections are calculated based on current MRR growth vectors and net burn velocity.
                 </p>
                 <div className="grid grid-cols-2 gap-8 w-full max-w-lg">
                    <div className="p-4 rounded-lg bg-bg-void/40 border border-border-dim">
                       <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Company Valuation</div>
                       <div className="text-2xl font-mono font-black text-accent">{formatCurrency(valuation)}</div>
                    </div>
                    <div className="p-4 rounded-lg bg-bg-void/40 border border-border-dim">
                       <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Implied ARR</div>
                       <div className="text-2xl font-mono font-black text-signal-green">{formatCurrency(mrr * 12)}</div>
                    </div>
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

                             <button 
                               onClick={() => handleNegotiate(inv.id, inv.name)}
                               className="w-full mt-4 py-1.5 rounded border border-border-dim text-[10px] font-bold uppercase text-text-secondary hover:text-accent hover:border-accent/50 transition-all"
                             >
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

// Removed duplicate Activity SVG

