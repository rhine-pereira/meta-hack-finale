"use client";

import React, { useEffect, useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { KpiStrip } from "@/components/dashboard/KpiStrip";
import { AgentPanel } from "@/components/dashboard/AgentPanel";
import { EventFeed } from "@/components/dashboard/EventFeed";
import { RewardPanel } from "@/components/dashboard/RewardPanel";
import { ProofPanel } from "@/components/dashboard/ProofPanel";
import { GenomePanel } from "@/components/dashboard/GenomePanel";
import { DayPlan } from "@/components/dashboard/DayPlan";
import { useGenesisStore } from "@/lib/store";
import { motion } from "framer-motion";
import { Rocket, Cpu, ChevronRight, BrainCircuit } from "lucide-react";
import { cn } from "@/lib/utils";
import { genesisClient } from "@/lib/genesis-client";

export default function Dashboard() {
  const { episodeId, isRunning, reset, difficulty, seed } = useGenesisStore();
  const [selectedModel, setSelectedModel] = useState("claude-3-5-sonnet");
  const [customModels, setCustomModels] = useState<string[]>([]);

  useEffect(() => {
    if (!episodeId) {
      const fetchCustomModels = async () => {
        try {
          const response = await genesisClient.callTool("list_founder_genomes", {});
          if (response.model_ids) {
            setCustomModels(response.model_ids);
          }
        } catch (e) {
          console.error("Failed to load custom models:", e);
        }
      };
      fetchCustomModels();
    }
  }, [episodeId]);

  if (!episodeId) {
    const baseModels = [
      { id: "claude-3-5-sonnet", label: "Anthropic Claude 3.5 Sonnet", icon: Cpu },
      { id: "gpt-4o", label: "OpenAI GPT-4o", icon: Cpu },
      { id: "gemini-1.5-pro", label: "Google Gemini 1.5 Pro", icon: Cpu },
    ];

    return (
      <div className="min-h-screen bg-bg-void flex items-center justify-center p-6">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="max-w-md w-full glass-panel p-12 rounded-2xl border-accent/20"
        >
          <div className="w-16 h-16 bg-accent/10 border border-accent/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <Rocket className="text-accent animate-pulse" size={32} />
          </div>
          <h1 className="text-3xl font-black text-accent mb-2 tracking-tighter uppercase font-mono text-center">GENESIS</h1>
          <p className="text-text-secondary text-sm mb-8 font-medium text-center">The Autonomous Startup Gauntlet</p>
          
          <div className="space-y-6">
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
              <label className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em]">Select Founder Persona</label>
              
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-2">
                  <div className="text-[8px] font-black text-text-muted uppercase tracking-widest px-1">Base Architectures</div>
                  {baseModels.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setSelectedModel(m.id)}
                      className={cn(
                        "flex items-center gap-3 p-3 rounded-xl border transition-all text-left",
                        selectedModel === m.id 
                          ? "bg-accent/10 border-accent text-accent shadow-[0_0_15px_rgba(45,212,191,0.1)]" 
                          : "bg-bg-void/40 border-border-dim text-text-muted hover:border-accent/30"
                      )}
                    >
                      <m.icon size={16} />
                      <span className="text-xs font-mono font-bold uppercase">{m.label}</span>
                    </button>
                  ))}
                </div>

                {customModels.length > 0 && (
                  <div className="grid grid-cols-1 gap-2">
                    <div className="text-[8px] font-black text-accent uppercase tracking-widest px-1">Fine-tuned Synapses</div>
                    {customModels.map((mid) => (
                      <button
                        key={mid}
                        onClick={() => setSelectedModel(mid)}
                        className={cn(
                          "flex items-center gap-3 p-3 rounded-xl border transition-all text-left",
                          selectedModel === mid 
                            ? "bg-accent/20 border-accent text-accent shadow-[0_0_20px_rgba(45,212,191,0.2)]" 
                            : "bg-accent/5 border-border-dim text-accent/70 hover:border-accent/40"
                        )}
                      >
                        <BrainCircuit size={16} />
                        <span className="text-xs font-mono font-bold uppercase">{mid}</span>
                        <div className="ml-auto text-[8px] border border-accent/30 px-1 rounded bg-accent/10">TRAINED</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <button 
              onClick={() => reset(difficulty, seed, selectedModel)}
              className="w-full py-4 bg-accent text-bg-void font-black text-xs uppercase tracking-[0.3em] rounded-xl hover:bg-accent-glow transition-all flex items-center justify-center gap-2 group"
            >
              Initialize Neural Bridge
              <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <MainLayout>
      <div className="flex flex-col h-full gap-6">
        <KpiStrip />
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
          <div className="lg:col-span-3 h-full overflow-hidden">
            <AgentPanel />
          </div>
          
          <div className="lg:col-span-6 h-full flex flex-col gap-6 overflow-hidden">
            <div className="h-fit shrink-0">
              <DayPlan />
            </div>
            <div className="flex-1 min-h-0">
              <EventFeed />
            </div>
          </div>
          
          <div className="lg:col-span-3 h-full flex flex-col gap-6 overflow-hidden">
            <div className="h-[250px] shrink-0">
              <RewardPanel />
            </div>
            <div className="flex-1 min-h-0">
              <GenomePanel />
            </div>
            <div className="h-fit">
              <ProofPanel />
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
