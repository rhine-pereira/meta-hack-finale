"use client";

import React, { useState } from "react";
import { useGenesisStore } from "@/lib/store";
import { 
  Users, 
  TrendingUp, 
  TrendingDown, 
  Zap, 
  ChevronRight,
  BarChart4,
  Cpu,
  ArrowRightLeft
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

export const ComparisonPanel: React.FC = () => {
  const { comparison, compareGenomes } = useGenesisStore();
  const [modelInput, setModelInput] = useState("");
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleAddModel = () => {
    if (modelInput && !selectedModels.includes(modelInput)) {
      setSelectedModels([...selectedModels, modelInput]);
      setModelInput("");
    }
  };

  const handleCompare = async () => {
    if (selectedModels.length < 2) return;
    setIsLoading(true);
    try {
      await compareGenomes(selectedModels);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const removeModel = (m: string) => {
    setSelectedModels(selectedModels.filter(id => id !== m));
  };

  return (
    <div className="glass-panel h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-signal-amber/10 border border-signal-amber/20">
            <ArrowRightLeft className="text-signal-amber" size={20} />
          </div>
          <div>
            <h3 className="text-sm font-black text-text-primary uppercase tracking-[0.15em] font-mono">
              Model Intelligence Differentiator
            </h3>
            <p className="text-[10px] text-text-muted uppercase font-mono mt-0.5">
              Comparative Analysis of Founder Personas
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-4 mb-8">
        <div className="flex-1 relative">
          <input 
            type="text" 
            value={modelInput}
            onChange={(e) => setModelInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddModel()}
            placeholder="ENTER MODEL ID (E.G. CLAUDE-3-OPUS)"
            className="w-full bg-bg-void/60 border border-border-dim rounded-lg px-4 py-2.5 text-xs font-mono focus:border-accent/50 focus:outline-none transition-all pr-10"
          />
          <button 
            onClick={handleAddModel}
            className="absolute right-2 top-1.5 p-1.5 text-text-muted hover:text-accent transition-colors"
          >
            <ChevronRight size={18} />
          </button>
        </div>
        <button 
          onClick={handleCompare}
          disabled={selectedModels.length < 2 || isLoading}
          className="px-6 py-2.5 bg-accent text-bg-void font-black text-xs uppercase tracking-widest rounded-lg hover:bg-accent-glow disabled:opacity-50 disabled:bg-border-dim transition-all flex items-center gap-2"
        >
          {isLoading ? <BarChart4 size={16} className="animate-pulse" /> : <BarChart4 size={16} />}
          Compare
        </button>
      </div>

      {selectedModels.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-8">
          {selectedModels.map(m => (
            <div key={m} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-bg-elevated border border-border-dim text-[10px] font-mono uppercase text-text-secondary group hover:border-accent/40 transition-all">
              <Cpu size={12} className="text-accent/60" />
              {m}
              <button 
                onClick={() => removeModel(m)}
                className="hover:text-signal-red transition-colors ml-1"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex-1">
        {!comparison ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-12 border-2 border-dashed border-border-dim rounded-2xl opacity-40">
            <Users size={48} className="text-text-muted mb-6" />
            <h4 className="text-sm font-black text-text-primary uppercase mb-2">Initialize Comparative Benchmark</h4>
            <p className="text-[10px] font-mono text-text-muted max-w-[280px]">
              Select at least two models to analyze behavioral divergence across the 11-dimensional reward space.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full overflow-y-auto pr-2 custom-scrollbar">
            {Object.entries(comparison.comparison).map(([id, genome], idx) => (
              <motion.div 
                key={id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="bg-bg-void/40 p-5 rounded-2xl border border-border-dim relative overflow-hidden group hover:border-accent/20 transition-all"
              >
                <div className="flex justify-between items-start mb-6">
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      idx === 0 ? "bg-accent" : idx === 1 ? "bg-signal-amber" : "bg-signal-blue"
                    )} />
                    <span className="text-xs font-black text-text-primary uppercase font-mono">{id}</span>
                  </div>
                  <div className="text-[9px] font-mono text-text-muted">
                    n={genome.metadata.episode_count} episodes
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="text-[9px] font-black text-signal-green uppercase tracking-[0.2em]">Dominant Traits</div>
                    <div className="flex flex-wrap gap-2">
                      {genome.metadata.strengths.map(s => (
                        <span key={s} className="px-2 py-1 rounded bg-signal-green/10 border border-signal-green/20 text-[9px] text-signal-green font-mono uppercase">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="text-[9px] font-black text-signal-red uppercase tracking-[0.2em]">Vulnerabilities</div>
                    <div className="flex flex-wrap gap-2">
                      {genome.metadata.weaknesses.map(w => (
                        <span key={w} className="px-2 py-1 rounded bg-signal-red/10 border border-signal-red/20 text-[9px] text-signal-red font-mono uppercase">
                          {w}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-8 pt-4 border-t border-border-dim/50 flex justify-between items-center">
                  <div className="text-[9px] font-mono text-text-muted flex items-center gap-1.5">
                    <Zap size={10} className="text-signal-amber" />
                    EFFICIENCY: {((genome.profile.product_velocity + genome.profile.runway_management) / 2 * 100).toFixed(0)}%
                  </div>
                  <div className="text-[9px] font-mono text-text-muted flex items-center gap-1.5">
                    <Users size={10} className="text-accent" />
                    CULTURE: {(genome.profile.team_morale * 100).toFixed(0)}%
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
