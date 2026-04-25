"use client";

import React, { ReactNode } from "react";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";
import { EpisodeGuard } from "../session/EpisodeGuard";

interface MainLayoutProps {
  children: ReactNode;
}

export const MainLayout = ({ children }: MainLayoutProps) => {
  return (
    <EpisodeGuard>
      <div className="flex min-h-screen">
        <TopBar />
        <Sidebar />
        <main className="flex-1 lg:ml-64 pt-20 p-6 min-h-screen overflow-y-auto">
          {children}
        </main>
      </div>
    </EpisodeGuard>
  );
};
