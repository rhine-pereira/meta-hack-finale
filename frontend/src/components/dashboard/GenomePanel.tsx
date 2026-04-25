"use client";

import React, { useState } from "react";
import { useGenesisStore } from "@/lib/store";
import { 
  Dna, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Download, 
  RefreshCcw,
  ShieldCheck,
  Zap,
  Target
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

export const GenomePanel: React.FC = () => {
  const { modelId, genomes, genomeExports, exportGenome } = useGenesisStore();
  const [isExporting, setIsExporting] = useState(false);
  
  const genome = modelId ? genomes[modelId] : null;
  const genomeExport = modelId ? genomeExports[modelId] : null;
  const baseUrl = process.env.NEXT_PUBLIC_GENESIS_URL || "http://localhost:7860";
  const pngUrl = genomeExport?.artifacts?.png ? `${baseUrl}/${genomeExport.artifacts.png}` : null;
  const jsonUrl = genomeExport?.artifacts?.json ? `${baseUrl}/${genomeExport.artifacts.json}` : null;

  const handleExport = async () => {
    if (!modelId) return;
    setIsExporting(true);
    try {
      await exportGenome(modelId);
    } catch (err) {
      console.error(err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="glass-panel h-full flex flex-col p-4 relative overflow-hidden">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-accent/10 border border-accent/20">
            <Dna className="text-accent" size={18} />
          </div>
          <h3 className="text-sm font-black text-text-primary uppercase tracking-wider font-mono">
            Founder Genome
          </h3>
        </div>
        <button 
          onClick={handleExport}
          disabled={!modelId || isExporting}
          className="p-2 rounded-lg bg-bg-void/50 border border-border-dim text-text-muted hover:text-accent hover:border-accent/30 transition-all disabled:opacity-50"
          title="Export Genome Card"
        >
          {isExporting ? <RefreshCcw size={14} className="animate-spin" /> : <Download size={14} />}
        </button>
      </div>

      <div className="flex-1 space-y-6">
        {!genome ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-border-dim rounded-xl opacity-50">
            <Activity size={32} className="text-text-muted mb-4 animate-pulse" />
            <p className="text-xs font-mono uppercase tracking-widest text-text-muted">
              {modelId ? "Generate profile to view genome" : "No active session"}
            </p>
            {modelId && (
              <button 
                onClick={handleExport}
                className="mt-4 px-4 py-2 bg-accent/10 border border-accent/30 text-accent text-[10px] font-black uppercase tracking-[0.2em] rounded-lg hover:bg-accent/20 transition-all"
              >
                Execute Analysis
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Exported Card Preview */}
            {pngUrl && (
              <div className="bg-bg-void/40 p-3 rounded-xl border border-border-dim">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-[9px] text-text-muted uppercase font-black tracking-widest font-mono">
                    Genome Card
                  </div>
                  <div className="flex gap-2">
                    {jsonUrl && (
                      <a
                        href={jsonUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-1 rounded bg-bg-void/50 border border-border-dim text-[9px] font-black uppercase tracking-widest text-text-muted hover:text-accent hover:border-accent/30 transition-all"
                      >
                        JSON
                      </a>
                    )}
                    <a
                      href={pngUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="px-2.5 py-1 rounded bg-accent/10 border border-accent/30 text-[9px] font-black uppercase tracking-widest text-accent hover:bg-accent/20 transition-all"
                    >
                      PNG
                    </a>
                  </div>
                </div>
                <div className="rounded-lg overflow-hidden border border-border-dim bg-bg-void/20">
                  <img
                    src={pngUrl}
                    alt={`Founder Genome: ${modelId}`}
                    className="w-full h-auto block"
                  />
                </div>
              </div>
            )}

            {/* Metadata Stats */}
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: "Episodes", value: genome.metadata.episode_count, icon: Target },
                { label: "Avg Difficulty", value: genome.metadata.avg_difficulty, icon: Zap },
                { label: "Avg Days", value: genome.metadata.avg_days_survived, icon: Activity },
              ].map((stat, i) => (
                <div key={i} className="bg-bg-void/40 p-2.5 rounded-lg border border-border-dim">
                  <div className="text-[8px] text-text-muted uppercase font-mono mb-1 flex items-center gap-1">
                    <stat.icon size={10} />
                    {stat.label}
                  </div>
                  <div className="text-sm font-black text-text-primary font-mono">{stat.value}</div>
                </div>
              ))}
            </div>

            {/* Strengths & Weaknesses */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="text-[10px] font-black text-signal-green uppercase tracking-widest flex items-center gap-1.5">
                  <TrendingUp size={12} />
                  Core Strengths
                </div>
                <div className="space-y-1.5">
                  {genome.metadata.strengths.map((s, i) => (
                    <motion.div 
                      key={s} 
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="px-2 py-1.5 rounded bg-signal-green/5 border border-signal-green/20 text-[10px] text-signal-green font-mono uppercase"
                    >
                      {s}
                    </motion.div>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-[10px] font-black text-signal-red uppercase tracking-widest flex items-center gap-1.5">
                  <TrendingDown size={12} />
                  Critical Gaps
                </div>
                <div className="space-y-1.5">
                  {genome.metadata.weaknesses.map((w, i) => (
                    <motion.div 
                      key={w}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="px-2 py-1.5 rounded bg-signal-red/5 border border-signal-red/20 text-[10px] text-signal-red font-mono uppercase"
                    >
                      {w}
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>

            {/* View Full Report Link */}
            <div className="pt-4 border-t border-border-dim">
              <div className="flex items-center gap-2 text-[9px] text-text-muted font-mono leading-relaxed">
                <ShieldCheck size={12} className="text-accent" />
                <span>BENCHMARK VERIFIED: {new Date(genome.metadata.timestamp).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Decorative background element */}
      <div className="absolute -bottom-8 -right-8 opacity-[0.03] pointer-events-none">
        <Dna size={160} />
      </div>
    </div>
  );
};
