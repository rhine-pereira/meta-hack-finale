"use client";

import { useState, useEffect, useRef } from "react";

export interface DemoEvent {
  id: number;
  ts: string;
  phase: number;
  phase_title: string;
  step: string;
  detail: string;
  status: "ok" | "warn" | "error" | "info";
  data?: any;
}

export interface DemoState {
  events: DemoEvent[];
  current_phase: number;
  phase_title: string | null;
}

export function useDemoStream() {
  const [events, setEvents] = useState<DemoEvent[]>([]);
  const [currentPhase, setCurrentPhase] = useState(0);
  const [phaseTitle, setPhaseTitle] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const baseUrl = process.env.NEXT_PUBLIC_GENESIS_URL || "http://localhost:7860";

  useEffect(() => {
    // 1. Fetch initial state
    const fetchInitialState = async () => {
      try {
        const res = await fetch(`${baseUrl}/demo/state`);
        if (res.ok) {
          const data: DemoState = await res.json();
          setEvents(data.events);
          setCurrentPhase(data.current_phase);
          setPhaseTitle(data.phase_title);
        }
      } catch (e) {
        console.error("Failed to fetch demo state:", e);
      }
    };

    fetchInitialState();

    // 2. Setup SSE
    const connectSSE = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const es = new EventSource(`${baseUrl}/demo/events`);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        console.log("Demo SSE Connected");
      };

      es.onmessage = (event) => {
        try {
          const newEvent: DemoEvent = JSON.parse(event.data);
          setEvents((prev) => {
            // Avoid duplicates if SSE pushes something we already have from state
            if (prev.some(e => e.id === newEvent.id)) return prev;
            return [...prev, newEvent];
          });
          if (newEvent.phase) {
            setCurrentPhase(newEvent.phase);
            setPhaseTitle(newEvent.phase_title);
          }
        } catch (e) {
          console.error("Failed to parse demo event:", e);
        }
      };

      es.onerror = (e) => {
        console.error("Demo SSE Error:", e);
        setIsConnected(false);
        es.close();
        // Simple reconnect logic
        setTimeout(connectSSE, 3000);
      };
    };

    connectSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [baseUrl]);

  return { events, currentPhase, phaseTitle, isConnected };
}
