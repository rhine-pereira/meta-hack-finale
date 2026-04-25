"use client";

import React from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { ComparisonPanel } from "@/components/dashboard/ComparisonPanel";
import { GenomePanel } from "@/components/dashboard/GenomePanel";
import { 
  Trophy, 
  Target, 
  Cpu, 
  TrendingUp, 
  Info,
  ExternalLink
} from "lucide-react";

export default function Benchmark() {
  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <div className="flex justify-between items-end">
          <div>
            <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono">Founder Genome Benchmark</h1>
            <p className="text-text-secondary text-sm">Competitive cross-model performance surveillance and persona fingerprinting.</p>
          </div>
          <div className="flex gap-2">
            <a 
              href="https://huggingface.co/openenv" 
              target="_blank" 
              rel="noopener noreferrer"
              className="px-4 py-2 rounded bg-bg-void border border-border-dim text-text-secondary font-bold text-xs uppercase tracking-widest hover:text-accent transition-colors flex items-center gap-2"
            >
              <ExternalLink size={14} />
              OpenEnv Docs
            </a>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { label: "Aggregate Episodes", value: "256", icon: Target, color: "text-accent" },
            { label: "Active Models", value: "12", icon: Cpu, color: "text-signal-blue" },
            { label: "Benchmark Difficulty", value: "GAUNTLET", icon: Trophy, color: "text-signal-amber" },
          ].map((kpi, i) => (
            <div key={i} className="glass-panel p-5 rounded-xl flex items-center gap-5">
              <div className="p-3.5 rounded-xl bg-bg-void/60 border border-border-dim shadow-inner">
                <kpi.icon size={22} className={kpi.color} />
              </div>
              <div>
                <div className="text-[10px] text-text-muted uppercase font-black tracking-[0.2em] mb-1">{kpi.label}</div>
                <div className="text-xl font-mono font-black text-text-primary">{kpi.value}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[700px]">
          <div className="lg:col-span-8">
            <ComparisonPanel />
          </div>
          <div className="lg:col-span-4 flex flex-col gap-6">
            <GenomePanel />
            
            <div className="glass-panel p-6 rounded-xl flex-1 border border-accent/10 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <Info size={80} />
              </div>
              
              <h3 className="text-xs font-black text-text-primary uppercase tracking-widest mb-4 flex items-center gap-2">
                <TrendingUp size={16} className="text-signal-green" />
                Benchmark Methodology
              </h3>
              
              <div className="space-y-4 text-[10px] text-text-secondary leading-relaxed font-mono">
                <p>
                  Genomes are computed by aggregating all reward components across N episodes. 
                  The <span className="text-accent">Differentiator</span> identifies behavioral divergence in high-pressure scenarios (Pivots, Market Shocks).
                </p>
                <div className="space-y-2 pt-2">
                  <div className="flex items-center gap-2">
                    <div className="w-1 h-1 rounded-full bg-accent" />
                    <span>STABILITY PRESET: 540 DAYS (GAUNTLET)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-1 h-1 rounded-full bg-accent" />
                    <span>AGGREGATION: EPISODE-MEAN</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-1 h-1 rounded-full bg-accent" />
                    <span>VERIFICATION: ON-CHAIN CHECKPOINTS</span>
                  </div>
                </div>
              </div>

              <div className="mt-8">
                <div className="text-[9px] font-black text-text-muted uppercase mb-3">Model Distribution</div>
                <div className="flex h-1.5 w-full bg-bg-void rounded-full overflow-hidden border border-border-dim">
                  <div className="h-full bg-accent" style={{ width: "45%" }} />
                  <div className="h-full bg-signal-amber" style={{ width: "30%" }} />
                  <div className="h-full bg-signal-blue" style={{ width: "25%" }} />
                </div>
                <div className="flex justify-between mt-2 text-[8px] font-mono text-text-muted">
                  <span>CLAUDE</span>
                  <span>GPT</span>
                  <span>GEMINI</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
