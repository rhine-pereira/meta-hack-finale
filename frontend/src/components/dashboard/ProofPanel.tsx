"use client";

import React from "react";
import { useGenesisStore } from "@/lib/store";
import { motion } from "framer-motion";
import { Shield, ExternalLink, Activity, Database, AlertTriangle } from "lucide-react";

export const ProofPanel: React.FC = () => {
  const { 
    lastSignature, 
    leafCount, 
    checkpointIndex, 
    isSolanaConfigured,
    commitProof,
    day
  } = useGenesisStore();

  const explorerUrl = lastSignature 
    ? `https://explorer.solana.com/tx/${lastSignature}?cluster=devnet`
    : null;

  return (
    <div className="glass-panel h-full flex flex-col p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="text-accent" size={18} />
          <h3 className="text-sm font-black text-text-primary uppercase tracking-wider font-mono">
            Verifiable Proofs
          </h3>
        </div>
        <div className={`text-[10px] px-2 py-0.5 rounded-full font-bold font-mono ${
          isSolanaConfigured ? "bg-signal-green/10 text-signal-green" : "bg-signal-amber/10 text-signal-amber"
        }`}>
          {isSolanaConfigured ? "SOLANA: ACTIVE" : "SOLANA: NOT CONFIGURED"}
        </div>
      </div>

      <div className="space-y-4 flex-1">
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-bg-elevated/50 p-3 rounded-lg border border-border-dim">
            <div className="text-[10px] text-text-muted uppercase font-mono mb-1">State Hashes</div>
            <div className="text-xl font-black text-text-primary font-mono">{leafCount}</div>
          </div>
          <div className="bg-bg-elevated/50 p-3 rounded-lg border border-border-dim">
            <div className="text-[10px] text-text-muted uppercase font-mono mb-1">Checkpoints</div>
            <div className="text-xl font-black text-text-primary font-mono">{checkpointIndex}</div>
          </div>
        </div>

        <div className="bg-bg-void/40 p-3 rounded-lg border border-border-dim">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] text-text-muted uppercase font-mono">Last On-Chain Commit</div>
            {explorerUrl && (
              <a 
                href={explorerUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-accent hover:text-accent-glow transition-colors"
              >
                <ExternalLink size={12} />
              </a>
            )}
          </div>
          {lastSignature ? (
            <div className="text-[10px] font-mono text-text-secondary break-all line-clamp-2">
              {lastSignature}
            </div>
          ) : (
            <div className="text-[10px] font-mono text-text-muted italic">
              No commits yet for this session.
            </div>
          )}
        </div>

        {!isSolanaConfigured && (
          <div className="bg-signal-amber/5 border border-signal-amber/20 p-3 rounded-lg flex gap-3">
            <AlertTriangle className="text-signal-amber shrink-0" size={16} />
            <p className="text-[10px] text-signal-amber leading-tight">
              Solana credentials missing in .env. Commits will fail.
            </p>
          </div>
        )}
      </div>

      <button
        onClick={() => commitProof()}
        disabled={!isSolanaConfigured || leafCount === 0}
        className="w-full mt-4 py-3 bg-accent hover:bg-accent/90 disabled:bg-border-dim disabled:text-text-muted text-bg-void font-black text-xs uppercase tracking-widest rounded-lg transition-all flex items-center justify-center gap-2 group"
      >
        <Activity size={14} className="group-hover:animate-pulse" />
        Commit Checkpoint
      </button>

      <div className="mt-4 pt-4 border-t border-border-dim text-[9px] text-text-muted font-mono leading-relaxed">
        <div className="flex items-center gap-1.5 mb-1 text-text-secondary">
          <Database size={10} />
          <span>CANONICAL REPLICATION LOG</span>
        </div>
        Each daily state is hashed and added to a Merkle tree. 
        Committing signs the root on Solana devnet for immutable auditability.
      </div>
    </div>
  );
};
