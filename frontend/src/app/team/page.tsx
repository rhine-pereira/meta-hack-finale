"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { MainLayout } from "@/components/layout/MainLayout";
import { BackToDashboard } from "@/components/navigation/BackToDashboard";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { 
  Users, 
  UserPlus, 
  Heart, 
  Flame, 
  ShieldAlert, 
  Briefcase,
  TrendingUp,
  Radar,
  UserX
} from "lucide-react";

export default function Team() {
  const { 
    employees, candidatePool, cofounderMorale, hireCandidate,
    postJobListing, holdOneOnOne, fireEmployee
  } = useGenesisStore();

  const handlePostJob = async () => {
    const role = prompt("Job Role?", "Senior Neural Engineer");
    if (!role) return;
    const reqs = prompt("Requirements?", "Experience with GRPO and simulation environments.");
    if (!reqs) return;
    const salary = prompt("Salary Range?", "$150k - $220k");
    if (!salary) return;
    
    await postJobListing(role, reqs, salary);
    alert("Job listing posted: " + role);
  };

  const handleHoldOneOnOne = async (empId: string, empName: string) => {
    await holdOneOnOne(empId);
    alert("Held 1:1 session with " + empName);
  };

  const handleFireEmployee = async (empId: string, empName: string) => {
    if (!confirm(`Are you sure you want to terminate ${empName}? This action is irreversible.`)) return;
    await fireEmployee(empId);
    alert(empName + " has been terminated.");
  };

  const avgMorale = employees.length > 0 
    ? employees.reduce((acc, e) => acc + e.morale, 0) / employees.length 
    : 0.8;

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <div className="flex justify-between items-end">
           <div>
             <h1 className="text-2xl font-black text-accent uppercase tracking-tight font-mono">Founders & Personnel</h1>
             <p className="text-text-secondary text-sm">Human capital health and recruitment intelligence.</p>
           </div>
           <div className="flex gap-2">
              <BackToDashboard />
              <button 
                onClick={handlePostJob}
                className="px-4 py-2 rounded bg-accent text-bg-void font-bold text-xs uppercase tracking-widest hover:bg-accent-muted transition-colors flex items-center gap-2"
              >
                <UserPlus size={16} />
                Post Job
              </button>
           </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
           {[
             { label: "Total Headcount", value: employees.length, icon: Users, color: "text-accent" },
             { label: "Avg Morale", value: `${(avgMorale * 100).toFixed(0)}%`, icon: Heart, color: "text-signal-green" },
             { label: "High Burnout", value: employees.filter(e => e.burnout_risk > 0.7).length, icon: Flame, color: "text-signal-amber" },
             { label: "Retention Risk", value: employees.filter(e => e.flight_risk > 0.6).length, icon: UserX, color: "text-signal-red" },
           ].map((kpi, i) => (
             <div key={i} className="glass-panel p-4 rounded-xl flex items-center gap-4">
                <div className={cn("p-3 rounded-lg bg-bg-void/50 border border-border-dim", kpi.color)}>
                  <kpi.icon size={20} />
                </div>
                <div>
                   <div className="text-[10px] text-text-muted uppercase font-bold tracking-widest">{kpi.label}</div>
                   <div className={cn("text-xl font-mono font-bold", kpi.color)}>{kpi.value}</div>
                </div>
             </div>
           ))}
        </div>

        <div className="grid grid-cols-12 gap-6">
           <div className="col-span-12 xl:col-span-8 flex flex-col gap-6">
              <div className="flex items-center justify-between border-b border-border-dim pb-2">
                 <h2 className="text-sm font-bold text-text-primary uppercase flex items-center gap-2">
                    <Users size={18} className="text-accent" />
                    Key Personnel Roster
                 </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                 {employees.length === 0 ? (
                    <div className="col-span-full py-12 glass-panel rounded-xl text-center text-text-muted text-xs uppercase tracking-widest border-dashed">
                       Founding Team Initializing...
                    </div>
                 ) : (
                    employees.map((emp, i) => (
                       <motion.div 
                          key={emp.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className="glass-panel p-5 rounded-xl relative group hover:border-accent/40 transition-all shadow-xl"
                       >
                          <div className="flex items-start gap-4 mb-6">
                             <div className="w-12 h-12 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center text-accent font-black">
                                {emp.name.split(' ').map(n => n[0]).join('')}
                             </div>
                             <div className="flex-1">
                                <div className="text-sm font-bold text-text-primary">{emp.name}</div>
                                <div className="text-[10px] text-text-muted uppercase font-bold tracking-tight">{emp.role}</div>
                             </div>
                             <div className={cn(
                                "px-2 py-0.5 rounded text-[8px] font-bold uppercase",
                                emp.flight_risk > 0.7 ? "bg-signal-red/10 text-signal-red" : 
                                emp.burnout_risk > 0.5 ? "bg-signal-amber/10 text-signal-amber" :
                                "bg-signal-green/10 text-signal-green"
                             )}>
                                {emp.flight_risk > 0.7 ? "At Risk" : "Stable"}
                             </div>
                          </div>

                          <div className="space-y-4">
                             <div>
                                <div className="flex justify-between text-[9px] text-text-muted uppercase font-bold mb-1">
                                   <span>Skill Matrix</span>
                                   <span className="text-accent">{(emp.skill_level * 100).toFixed(0)}/100</span>
                                </div>
                                <div className="h-1 w-full bg-bg-void rounded-full overflow-hidden border border-border-dim">
                                   <div className="h-full bg-accent" style={{ width: `${emp.skill_level * 100}%` }} />
                                </div>
                             </div>
                             <div>
                                <div className="flex justify-between text-[9px] text-text-muted uppercase font-bold mb-1">
                                   <span>Morale</span>
                                   <span className={cn(emp.morale > 0.6 ? "text-signal-green" : "text-signal-red")}>{(emp.morale * 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1 w-full bg-bg-void rounded-full overflow-hidden border border-border-dim">
                                   <div className={cn("h-full", emp.morale > 0.6 ? "bg-signal-green" : "bg-signal-red")} style={{ width: `${emp.morale * 100}%` }} />
                                </div>
                             </div>
                             <div>
                                <div className="flex justify-between text-[9px] text-text-muted uppercase font-bold mb-1">
                                   <span>Burnout</span>
                                   <span className={cn(emp.burnout_risk > 0.7 ? "text-signal-red" : "text-signal-amber")}>{(emp.burnout_risk * 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1 w-full bg-bg-void rounded-full overflow-hidden border border-border-dim">
                                   <div className={cn("h-full", emp.burnout_risk > 0.7 ? "bg-signal-red" : "bg-signal-amber")} style={{ width: `${emp.burnout_risk * 100}%` }} />
                                </div>
                             </div>
                          </div>

                          <div className="mt-6 pt-4 border-t border-border-dim flex justify-between items-center">
                             <div className="text-[9px] text-text-muted font-mono uppercase">Tenure: {emp.months_employed}M</div>
                             <div className="flex gap-2">
                                <button 
                                  onClick={() => handleHoldOneOnOne(emp.id, emp.name)}
                                  className="p-1.5 rounded bg-bg-void border border-border-dim hover:border-accent transition-all text-text-secondary hover:text-accent"
                                >
                                   <Briefcase size={14} />
                                </button>
                                <button 
                                  onClick={() => handleFireEmployee(emp.id, emp.name)}
                                  className="p-1.5 rounded bg-bg-void border border-border-dim hover:border-signal-red transition-all text-text-secondary hover:text-signal-red"
                                >
                                   <UserX size={14} />
                                </button>
                             </div>
                          </div>
                       </motion.div>
                    ))
                 )}
              </div>
           </div>

           <div className="col-span-12 xl:col-span-4 flex flex-col gap-6">
              <div className="glass-panel p-5 rounded-xl">
                 <h3 className="text-[10px] text-text-muted font-bold uppercase tracking-widest mb-4 flex justify-between items-center">
                    Team Morale Indices
                 </h3>
                 <div className="grid grid-cols-5 gap-2">
                    {Object.entries(cofounderMorale).map(([role, morale]) => (
                       <div key={role} className="flex flex-col items-center gap-1">
                          <div className={cn(
                             "w-full h-1 rounded-full",
                             morale > 0.6 ? "bg-signal-green" : morale > 0.3 ? "bg-signal-amber" : "bg-signal-red"
                          )} style={{ height: '4px' }} />
                          <span className="text-[8px] uppercase font-bold text-text-muted">{role}</span>
                       </div>
                    ))}
                 </div>
              </div>

              <div className="glass-panel rounded-xl flex flex-col flex-1">
                 <div className="p-4 border-b border-border-dim flex justify-between items-center bg-bg-surface/50">
                    <h3 className="text-[10px] text-text-primary font-bold uppercase flex items-center gap-2 tracking-widest">
                       <Radar size={14} className="text-accent" />
                       Candidate Pool
                    </h3>
                    <span className="bg-accent/10 border border-accent/30 text-accent px-2 py-0.5 rounded text-[9px] font-bold font-mono">
                       {candidatePool.length} QUEUED
                    </span>
                 </div>
                 
                 <div className="flex-1 overflow-y-auto max-h-[400px]">
                    <table className="w-full text-left border-collapse">
                       <thead className="bg-bg-void/50 border-b border-border-dim text-[9px] text-text-muted uppercase font-bold sticky top-0 z-10">
                          <tr>
                             <th className="p-3">Candidate</th>
                             <th className="p-3 text-right">Skill</th>
                             <th className="p-3 text-right">Interview</th>
                             <th className="p-3 text-center">Action</th>
                          </tr>
                       </thead>
                       <tbody className="text-[11px] divide-y divide-border-dim/50">
                          {candidatePool.length === 0 ? (
                             <tr><td colSpan={4} className="p-8 text-center text-text-muted uppercase tracking-tighter">No candidates available</td></tr>
                          ) : (
                             candidatePool.map((c, i) => (
                                <tr key={c.id} className="hover:bg-bg-hover/50 transition-colors">
                                   <td className="p-3">
                                      <div className="font-bold text-text-primary">{c.name}</div>
                                      <div className="text-[9px] text-text-muted font-mono">{c.role}</div>
                                   </td>
                                   <td className="p-3 text-right font-mono text-signal-green">{(c.skill_level * 100).toFixed(0)}</td>
                                   <td className="p-3 text-right font-mono text-accent">{(c.interview_score * 100).toFixed(0)}</td>
                                   <td className="p-3 text-center">
                                      <button 
                                        onClick={() => hireCandidate(c.id, c.role, 120000)}
                                        className="bg-accent/10 border border-accent/30 text-accent hover:bg-accent/20 px-3 py-1 rounded text-[9px] font-bold uppercase transition-all"
                                      >
                                         Hire
                                      </button>
                                   </td>
                                </tr>
                             ))
                          )}
                       </tbody>
                    </table>
                 </div>
              </div>
           </div>
        </div>
      </div>
    </MainLayout>
  );
}
