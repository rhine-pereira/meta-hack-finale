"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { ShieldAlert, Cpu, User, Hand } from "lucide-react";
import { GhostFounderConsole } from "./GhostFounderConsole";
import type { AgentRoleId } from "@/types/genesis";

export const AgentPanel = () => {
  const {
    cofounderMorale,
    personalCrises,
    roleControllers,
    ghostActiveRole,
    takeControl,
    releaseControl,
    openGhostConsole,
  } = useGenesisStore();

  const roles: Array<{ id: AgentRoleId; label: string; color: string; glow: string }> = [
    { id: "ceo",    label: "CEO",    color: "border-role-ceo",    glow: "shadow-role-ceo/5" },
    { id: "cto",    label: "CTO",    color: "border-role-cto",    glow: "shadow-role-cto/5" },
    { id: "sales",  label: "Sales",  color: "border-role-sales",  glow: "shadow-role-sales/5" },
    { id: "people", label: "People", color: "border-role-people", glow: "shadow-role-people/5" },
    { id: "cfo",    label: "CFO",    color: "border-role-cfo",    glow: "shadow-role-cfo/5" },
  ];

  return (
    <>
      <div className="flex flex-col gap-3 h-full overflow-y-auto pr-1">
        <div className="font-mono text-[10px] text-text-muted uppercase tracking-widest font-bold mb-1 flex items-center justify-between">
          <span>Founding Team Status</span>
          <span className="text-accent/70">Ghost Founder</span>
        </div>
        {roles.map((role, i) => {
          const morale = cofounderMorale[role.id] ?? 0.8;
          const roleCrises = personalCrises.filter(
            (c) => c.target_role === role.id && !c.resolved && !c.ignored
          );
          const controller = roleControllers[role.id] ?? "ai";
          const isHuman = controller === "human";

          return (
            <motion.div
              key={role.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className={cn(
                "bg-bg-surface/60 backdrop-blur-md border border-border-dim rounded p-4 border-l-4 transition-all hover:bg-bg-hover shadow-lg",
                role.color,
                isHuman && "ring-1 ring-signal-purple/50 shadow-signal-purple/10"
              )}
            >
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <div className="font-bold text-sm tracking-tight text-text-primary uppercase">
                    {role.label}
                  </div>
                  <span
                    className={cn(
                      "flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-widest border font-mono",
                      isHuman
                        ? "bg-signal-purple/15 border-signal-purple/40 text-signal-purple"
                        : "bg-accent/10 border-accent/30 text-accent/80"
                    )}
                    title={isHuman ? "Driven by human ghost-founder" : "Driven by AI"}
                  >
                    {isHuman ? <User size={9} /> : <Cpu size={9} />}
                    {isHuman ? "Human" : "AI"}
                  </span>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <div className="text-[10px] text-text-muted uppercase font-mono tracking-tighter">
                    Morale: {(morale * 100).toFixed(0)}%
                  </div>
                  <div className="w-24 h-1 bg-border-dim rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full",
                        morale > 0.6
                          ? "bg-signal-green"
                          : morale > 0.3
                          ? "bg-signal-amber"
                          : "bg-signal-red"
                      )}
                      style={{ width: `${morale * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {roleCrises.length > 0 && (
                <div className="mt-3 p-2 rounded bg-signal-red/10 border border-signal-red/30 flex items-start gap-2">
                  <ShieldAlert size={14} className="text-signal-red mt-0.5" />
                  <div className="text-[10px] text-signal-red font-medium leading-tight">
                    ACTIVE CRISIS: {roleCrises[0].description.substring(0, 40)}...
                  </div>
                </div>
              )}

              <div className="mt-4 grid grid-cols-2 gap-2">
                {isHuman ? (
                  <>
                    <button
                      onClick={() => openGhostConsole(role.id)}
                      className="py-1 rounded bg-signal-purple/15 border border-signal-purple/40 hover:bg-signal-purple/25 text-signal-purple text-[10px] font-black uppercase tracking-widest transition-colors flex items-center justify-center gap-1"
                    >
                      <Hand size={11} />
                      Console
                    </button>
                    <button
                      onClick={() => releaseControl(role.id)}
                      className="py-1 rounded border border-border-dim hover:border-accent/50 text-[10px] font-bold uppercase transition-colors text-text-secondary hover:text-accent"
                      title="Hand this role back to the AI"
                    >
                      Release
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => openGhostConsole(role.id)}
                      className="py-1 rounded border border-border-dim hover:border-accent/50 text-[10px] font-bold uppercase transition-colors text-text-secondary hover:text-text-primary"
                      title="Inspect this role's briefing"
                    >
                      Briefing
                    </button>
                    <button
                      onClick={() => takeControl(role.id)}
                      className="py-1 rounded bg-signal-purple/10 border border-signal-purple/30 hover:bg-signal-purple/20 text-signal-purple text-[10px] font-black uppercase tracking-widest transition-colors flex items-center justify-center gap-1"
                      title="Become this co-founder. The AI will adapt around you."
                    >
                      <Hand size={11} />
                      Take Control
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
      {ghostActiveRole && <GhostFounderConsole />}
    </>
  );
};
