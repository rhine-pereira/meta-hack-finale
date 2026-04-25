"use client";

import React, { useEffect, useState } from "react";
import { useGenesisStore } from "@/lib/store";
import { genesisClient } from "@/lib/genesis-client";
import { SensorsIcon, TerminalIcon, SettingsIcon } from "lucide-react"; // Using standard Lucide icons
import { 
  Activity, 
  Terminal, 
  Settings, 
  Flame, 
  Monitor, 
  Cpu, 
  Users, 
  TrendingUp 
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export const TopBar = () => {
  const { 
    day, 
    maxDays, 
    isRunning, 
    difficulty, 
    episodeId, 
    serverOnline, 
    setServerOnline,
    companyBrain,
    personalCrises 
  } = useGenesisStore();
  
  const pathname = usePathname();

  const activeCrisesCount = personalCrises.filter(c => !c.resolved && !c.ignored).length;

  useEffect(() => {
    const checkServer = async () => {
      const online = await genesisClient.checkHealth();
      setServerOnline(online);
    };
    
    checkServer();
    const interval = setInterval(checkServer, 10000);
    return () => clearInterval(interval);
  }, [setServerOnline]);

  const difficultyLabel = [
    "TUTORIAL", "SEED", "GROWTH", "GAUNTLET", "NIGHTMARE"
  ][difficulty - 1] || "GAUNTLET";

  const difficultyColor = [
    "text-signal-green border-signal-green/30",
    "text-signal-blue border-signal-blue/30",
    "text-signal-amber border-signal-amber/30",
    "text-role-ceo border-role-ceo/30",
    "text-signal-red border-signal-red/30"
  ][difficulty - 1] || "text-accent border-accent/30";

  return (
    <header className="fixed w-full top-0 z-50 bg-bg-void/90 backdrop-blur-xl border-b border-accent/20 shadow-2xl shadow-accent/10 flex flex-col w-full h-auto py-2 px-6">
      <div className="flex items-center justify-between w-full h-10">
        <div className="flex items-center gap-8">
          <div className="text-2xl font-black text-accent drop-shadow-[0_0_10px_rgba(45,212,191,0.5)] tracking-widest font-mono uppercase">
            GENESIS
          </div>
          <nav className="hidden md:flex items-center gap-4 font-mono tracking-tighter uppercase text-xs">
            {[
              { label: "Dashboard", href: "/" },
              { label: "Benchmark", href: "/benchmark" },
              { label: "Training", href: "/training" },
              { label: "Financials", href: "/financials" },
              { label: "Product", href: "/product" },
              { label: "Team", href: "/team" },
              { label: "Market", href: "/market" },
              { label: "Brain", href: "/brain" },
              { label: "Crises", href: "/crises", badge: activeCrisesCount > 0 ? activeCrisesCount : null },
            ].map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "px-2 pb-1 transition-all duration-200 border-b-2 relative",
                  pathname === link.href 
                    ? "text-accent border-accent font-bold" 
                    : "text-text-secondary border-transparent font-medium hover:text-text-primary hover:bg-accent/10"
                )}
              >
                {link.label}
                {link.badge && (
                  <span className="absolute -top-2 -right-2 flex h-4 w-4 items-center justify-center rounded-full bg-signal-red text-[10px] font-black text-white animate-pulse">
                    {link.badge}
                  </span>
                )}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 bg-accent/10 border border-accent/30 rounded text-accent font-mono text-[10px] uppercase">
              <span className={cn(
                "w-2 h-2 rounded-full",
                isRunning && serverOnline ? "bg-signal-green animate-pulse" : "bg-text-muted"
              )} />
              {isRunning && serverOnline ? "LIVE" : "PAUSED"}
            </div>
            
            <div className="px-3 py-1 border border-border-dim rounded text-text-secondary font-mono text-[10px] uppercase">
              DAY {String(day).padStart(3, "0")} / {maxDays}
            </div>
          </div>

          <div className="flex items-center gap-2 border-l border-border-dim pl-4">
            <div className={cn(
              "px-2 py-1 border rounded text-[10px] font-bold tracking-widest uppercase flex items-center gap-1",
              difficultyColor
            )}>
              <Flame size={12} />
              {difficultyLabel}
            </div>
            
            <div className="flex items-center gap-1 ml-2">
              <button className={cn(
                "p-1 transition-colors",
                serverOnline ? "text-accent" : "text-signal-red"
              )} title={serverOnline ? "Server Online" : "Server Offline"}>
                <Activity size={18} />
              </button>
              <button className="text-text-secondary hover:text-accent p-1">
                <Terminal size={18} />
              </button>
              <button className="text-text-secondary hover:text-accent p-1">
                <Settings size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div className="h-0.5 w-full bg-border-dim mt-2 overflow-hidden">
        <div 
          className="h-full bg-accent transition-all duration-500" 
          style={{ width: `${(day / maxDays) * 100}%` }}
        />
      </div>
    </header>
  );
};
