"use client";

import React, { useEffect } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { KpiStrip } from "@/components/dashboard/KpiStrip";
import { AgentPanel } from "@/components/dashboard/AgentPanel";
import { EventFeed } from "@/components/dashboard/EventFeed";
import { RewardPanel } from "@/components/dashboard/RewardPanel";
import { useGenesisStore } from "@/lib/store";
import { motion } from "framer-motion";
import { Rocket } from "lucide-react";

export default function Dashboard() {
  const { episodeId, isRunning, reset, difficulty, seed } = useGenesisStore();

  useEffect(() => {
    // Auto-reset if no session
    if (!episodeId) {
      reset(difficulty, seed);
    }
  }, [episodeId, reset, difficulty, seed]);

  if (!episodeId) {
    return (
      <div className="min-h-screen bg-bg-void flex items-center justify-center p-6">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="max-w-md w-full glass-panel p-12 text-center rounded-2xl border-accent/20"
        >
          <div className="w-16 h-16 bg-accent/10 border border-accent/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <Rocket className="text-accent animate-pulse" size={32} />
          </div>
          <h1 className="text-3xl font-black text-accent mb-2 tracking-tighter uppercase font-mono">GENESIS</h1>
          <p className="text-text-secondary text-sm mb-8 font-medium">The Autonomous Startup Gauntlet</p>
          <div className="space-y-4">
             <div className="text-xs text-text-muted font-mono animate-pulse">Initializing Neural Interface...</div>
             <div className="h-1 w-full bg-border-dim rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: "100%" }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="h-full bg-accent"
                />
             </div>
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
          
          <div className="lg:col-span-6 h-full overflow-hidden">
            <EventFeed />
          </div>
          
          <div className="lg:col-span-3 h-full overflow-hidden">
            <RewardPanel />
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
