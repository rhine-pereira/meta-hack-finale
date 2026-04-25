"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { Play, SkipForward, RotateCcw, Activity } from "lucide-react";

export const EventFeed = () => {
  const { eventLog, advanceDay, isRunning, reset, difficulty, seed } = useGenesisStore();

  return (
    <div className="flex flex-col h-full bg-bg-surface/40 backdrop-blur-sm border border-border-dim rounded-lg overflow-hidden">
      <div className="p-4 border-b border-border-dim bg-bg-surface/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-accent" />
          <h3 className="font-heading-section text-sm font-bold text-text-primary uppercase tracking-tight">Mission Log</h3>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={() => advanceDay()}
            className="p-1.5 rounded border border-accent/30 bg-accent/10 text-accent hover:bg-accent/20 transition-all"
            title="Advance Day"
          >
            <Play size={16} />
          </button>
          <button 
            className="p-1.5 rounded border border-border-dim text-text-secondary hover:text-text-primary transition-all"
            title="Run 7 Days"
          >
            <SkipForward size={16} />
          </button>
          <button 
            onClick={() => reset(difficulty, seed)}
            className="p-1.5 rounded border border-border-dim text-text-secondary hover:text-signal-red transition-all"
            title="Restart Session"
          >
            <RotateCcw size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
        <AnimatePresence initial={false}>
          {eventLog.length === 0 ? (
            <div className="h-full flex items-center justify-center text-text-muted font-mono text-xs uppercase tracking-widest">
              Initializing systems...
            </div>
          ) : (
            eventLog.map((event, i) => (
              <motion.div
                key={`${event.day}-${i}`}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className={cn(
                  "p-3 rounded border border-border-dim bg-bg-surface/80 border-l-2 relative overflow-hidden",
                  event.type === "positive" ? "border-l-signal-green" :
                  event.type === "negative" ? "border-l-signal-red" :
                  event.type === "warning" ? "border-l-signal-amber" :
                  event.type === "special" ? "border-l-signal-purple" :
                  "border-l-signal-blue"
                )}
              >
                <div className="flex justify-between items-start gap-3">
                  <div className="text-[12px] font-medium leading-relaxed text-text-primary">
                    {event.text}
                  </div>
                  <div className="text-[10px] font-mono text-text-muted whitespace-nowrap bg-bg-void px-1.5 py-0.5 rounded border border-border-dim/50">
                    DAY {String(event.day).padStart(3, "0")}
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
