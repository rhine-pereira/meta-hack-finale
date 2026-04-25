"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useGenesisStore } from "@/lib/store";

interface EpisodeGuardProps {
  children: React.ReactNode;
}

export const EpisodeGuard = ({ children }: EpisodeGuardProps) => {
  const { episodeId } = useGenesisStore();
  const router = useRouter();

  useEffect(() => {
    if (!episodeId) {
      router.push("/");
    }
  }, [episodeId, router]);

  if (!episodeId) {
    return null; // Or a loading state/redirecting message
  }

  return <>{children}</>;
};
