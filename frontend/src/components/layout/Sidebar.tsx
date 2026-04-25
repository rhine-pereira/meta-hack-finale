"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { 
  ShieldAlert, 
  UserCircle, 
  LayoutDashboard, 
  FileText, 
  Users, 
  Briefcase, 
  BrainCircuit, 
  HelpCircle,
  AlertTriangle,
  History,
  Activity,
  TrendingUp,
  Skull
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";

export const Sidebar = () => {
  const { cofounderMorale } = useGenesisStore();
  const pathname = usePathname();

  const navGroups = [
    {
      label: "Command Hub",
      links: [
        { label: "Mission Control", href: "/", icon: LayoutDashboard },
        { label: "Incident Control", href: "/crises", icon: ShieldAlert, color: "text-signal-red" },
      ]
    },
    {
      label: "Operations",
      links: [
        { label: "Product Matrix", href: "/product", icon: Briefcase },
        { label: "Market Intel", href: "/market", icon: TrendingUp },
        { label: "Founders & Team", href: "/team", icon: Users },
        { label: "Financials", href: "/financials", icon: FileText },
        { label: "Resurrection Engine", href: "/postmortem", icon: Skull, color: "text-signal-red" },
      ]
    },
    {
      label: "Intelligence",
      links: [
        { label: "Cognitive Core", href: "/brain", icon: BrainCircuit },
        { label: "Benchmarks", href: "/benchmark", icon: History },
        { label: "Training", href: "/training", icon: Activity },
      ]
    }
  ];

  return (
    <aside className="fixed left-0 top-0 h-full hidden lg:flex flex-col z-40 bg-bg-surface/80 backdrop-blur-lg w-64 border-r border-accent/10 shadow-inner-teal pt-20 overflow-y-auto custom-scrollbar">
      <div className="p-6 border-b border-white/5">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 rounded bg-accent/20 border border-accent/30 flex items-center justify-center">
            <UserCircle className="text-accent" size={18} />
          </div>
          <div>
            <div className="text-accent font-bold uppercase tracking-tighter text-sm font-mono">
              ORBITAL COMMAND
            </div>
            <div className="text-[10px] text-text-muted font-mono">V 2.0.4 - ACTIVE</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 py-4 flex flex-col font-mono text-xs">
        {navGroups.map((group, gi) => (
          <div key={gi} className={cn("mb-6", gi > 0 && "mt-2 pt-4 border-t border-white/5")}>
            <div className="px-6 py-2 text-[10px] text-text-muted uppercase tracking-widest font-bold mb-1">
              {group.label}
            </div>
            {group.links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "py-3 px-6 flex items-center gap-3 transition-all duration-200",
                  pathname === link.href
                    ? "bg-accent/10 text-accent border-r-2 border-accent opacity-100"
                    : "text-text-secondary opacity-60 hover:bg-white/5 hover:opacity-100"
                )}
              >
                <link.icon size={16} className={link.color} />
                <span className="flex-1">{link.label}</span>
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-white/5 bg-bg-void/50">
        <div className="px-2 mb-4">
          <div className="text-[10px] text-text-muted uppercase tracking-widest font-bold mb-3">
            Founder Morale
          </div>
          <div className="grid grid-cols-5 gap-1">
            {["ceo", "cto", "sales", "people", "cfo"].map(role => (
              <div key={role} className="flex flex-col items-center gap-1">
                <div className={cn(
                  "w-full h-1 rounded-full",
                  (cofounderMorale[role] ?? 0.8) > 0.6 ? "bg-signal-green" : 
                  (cofounderMorale[role] ?? 0.8) > 0.3 ? "bg-signal-amber" : "bg-signal-red"
                )} style={{ height: '4px' }} />
                <span className="text-[8px] uppercase font-bold text-text-muted">{role[0]}</span>
              </div>
            ))}
          </div>
        </div>
        <button className="w-full py-2.5 bg-signal-red/10 border border-signal-red/30 text-signal-red font-mono text-[10px] font-bold tracking-widest hover:bg-signal-red/20 transition-all flex items-center justify-center gap-2 rounded uppercase">
          <AlertTriangle size={14} />
          EMERGENCY OVERRIDE
        </button>
      </div>
    </aside>
  );
};
