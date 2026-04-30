"use client";

import React from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { RewardPanel } from "@/components/dashboard/RewardPanel";
import { useGenesisStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Award, Sigma } from "lucide-react";
import Link from "next/link";

const REWARD_COMPONENTS = [
  { key: "company_valuation", label: "Company valuation", weight: 0.20 },
  { key: "series_a_success", label: "Series A success", weight: 0.10 },
  { key: "runway_management", label: "Runway management", weight: 0.10 },
  { key: "product_velocity", label: "Product velocity", weight: 0.10 },
  { key: "customer_retention", label: "Customer retention", weight: 0.10 },
  { key: "team_morale", label: "Team morale", weight: 0.10 },
  { key: "cofounder_alignment", label: "Cofounder alignment", weight: 0.05 },
  { key: "personal_crisis_handling", label: "Personal crisis handling", weight: 0.05 },
  { key: "decision_coherence", label: "Decision coherence", weight: 0.10 },
  { key: "company_brain_quality", label: "Company brain quality", weight: 0.05 },
  { key: "pivot_execution", label: "Pivot execution", weight: 0.05 },
] as const;

export default function RewardsPage() {
  const { currentReward, episodeId } = useGenesisStore();

  return (
    <MainLayout requireEpisode={false}>
      <div className="flex flex-col gap-6">
        {!episodeId && (
          <div className="rounded-2xl border border-accent/20 bg-accent/5 p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div className="min-w-0">
              <div className="text-[10px] font-black uppercase tracking-[0.22em] text-accent">
                No active episode
              </div>
              <div className="mt-1 text-[11px] text-text-secondary">
                Start a run on Mission Control to populate live reward values.
              </div>
            </div>
            <Link
              href="/"
              className="shrink-0 inline-flex items-center justify-center rounded-xl border border-accent/30 bg-accent/10 hover:bg-accent/15 transition-colors px-4 py-2 text-[10px] font-black uppercase tracking-[0.22em] text-accent font-mono"
            >
              Go to Mission Control
            </Link>
          </div>
        )}

        <div className="flex items-end justify-between gap-6">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/25 flex items-center justify-center shadow-[0_0_22px_rgba(45,212,191,0.12)]">
                <Award className="text-accent" size={18} />
              </div>
              <div className="min-w-0">
                <h1 className="text-xl md:text-2xl font-black tracking-tight uppercase font-mono text-text-primary">
                  Rewards
                </h1>
                <p className="text-[11px] text-text-muted font-mono mt-0.5">
                  Full breakdown of the 11-component reward rubric.
                </p>
              </div>
            </div>
          </div>

          <div className="shrink-0 rounded-xl border border-border-dim bg-bg-surface/40 backdrop-blur-sm px-4 py-3">
            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted flex items-center gap-2">
              <Sigma size={14} className="text-accent/80" />
              Total reward
            </div>
            <div className="mt-1 text-2xl font-mono font-black text-accent tabular-nums drop-shadow-[0_0_10px_rgba(45,212,191,0.25)]">
              {(currentReward?.total ?? 0).toFixed(3)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          <div className="xl:col-span-4">
            <div className="h-[520px]">
              <RewardPanel />
            </div>
          </div>

          <div className="xl:col-span-8">
            <div className="rounded-2xl border border-border-dim bg-bg-surface/40 backdrop-blur-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.25em] text-text-muted">
                    Component contributions
                  </div>
                  <div className="text-xs text-text-secondary mt-1">
                    Contribution is computed as \(weight \times value\).
                  </div>
                </div>
                <div className="text-[10px] font-mono text-text-muted">
                  values in \([0,1]\)
                </div>
              </div>

              <div className="p-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {REWARD_COMPONENTS.map((c) => {
                    const raw = (currentReward as any)?.[c.key] ?? 0;
                    const value = Math.max(0, Math.min(1, Number(raw) || 0));
                    const contribution = c.weight * value;
                    const tone =
                      value > 0.7 ? "signal-green" : value > 0.4 ? "signal-amber" : "signal-red";

                    return (
                      <div
                        key={c.key}
                        className="rounded-xl border border-border-dim bg-bg-void/35 p-4 hover:border-accent/25 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <div className="text-[11px] font-black uppercase tracking-tight text-text-primary truncate">
                              {c.label}
                            </div>
                            <div className="mt-1 text-[10px] font-mono text-text-muted">
                              w={c.weight.toFixed(2)}
                            </div>
                          </div>

                          <div className="text-right">
                            <div
                              className={cn(
                                "text-[12px] font-mono font-black tabular-nums",
                                tone === "signal-green"
                                  ? "text-signal-green"
                                  : tone === "signal-amber"
                                    ? "text-signal-amber"
                                    : "text-signal-red"
                              )}
                            >
                              {value.toFixed(2)}
                            </div>
                            <div className="mt-1 text-[10px] font-mono text-text-muted tabular-nums">
                              +{contribution.toFixed(3)}
                            </div>
                          </div>
                        </div>

                        <div className="mt-3 h-1.5 w-full bg-bg-void rounded-full border border-border-dim overflow-hidden">
                          <div
                            className={cn(
                              "h-full transition-all duration-700 ease-out",
                              tone === "signal-green"
                                ? "bg-signal-green"
                                : tone === "signal-amber"
                                  ? "bg-signal-amber"
                                  : "bg-signal-red"
                            )}
                            style={{ width: `${value * 100}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="mt-5 rounded-xl border border-accent/20 bg-accent/5 p-4">
                  <div className="text-[10px] font-black uppercase tracking-[0.22em] text-accent">
                    Interactions
                  </div>
                  <p className="mt-2 text-[11px] text-text-secondary leading-relaxed">
                    Pushing a single metric to the ceiling can create hidden failure modes in adjacent systems.
                    Use this page to spot “green islands” surrounded by red/amber risk.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

