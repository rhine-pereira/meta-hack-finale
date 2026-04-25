"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const BackToDashboard = () => {
  return (
    <Link href="/">
      <button className="px-4 py-2 rounded bg-bg-void border border-border-dim text-text-secondary font-bold text-xs uppercase tracking-widest hover:text-accent hover:border-accent/50 transition-all flex items-center gap-2 group">
        <ArrowLeft size={14} className="group-hover:-translate-x-1 transition-transform" />
        Back to Dashboard
      </button>
    </Link>
  );
};
