import { useState, useEffect, useCallback } from "react";
import { fetchAgentEvents, fetchTimeline, fetchPendingActions } from "../api/client";
import type { AgentEvent, TimelineEvent, PendingAction } from "../types";

export function useAgentEvents() {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<AgentEvent | null>(null);

  const refreshEvents = useCallback(async () => {
    try {
      const data = await fetchAgentEvents({ limit: "50" });
      setEvents((data as { events: AgentEvent[] }).events ?? []);
    } catch (e) {
      console.error("Agent events fetch error:", e);
    }
  }, []);

  const refreshTimeline = useCallback(async () => {
    try {
      const data = await fetchTimeline(30);
      setTimeline((data as { timeline: TimelineEvent[] }).timeline ?? []);
    } catch (e) {
      console.error("Timeline fetch error:", e);
    }
  }, []);

  const refreshPending = useCallback(async () => {
    try {
      const data = await fetchPendingActions();
      setPendingActions(
        (data as { pending_actions: PendingAction[] }).pending_actions ?? [],
      );
    } catch (e) {
      console.error("Pending actions fetch error:", e);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([refreshEvents(), refreshTimeline(), refreshPending()]);
  }, [refreshEvents, refreshTimeline, refreshPending]);

  useEffect(() => {
    refreshAll();
    const id = setInterval(refreshAll, 5000);
    return () => clearInterval(id);
  }, [refreshAll]);

  const addEvent = useCallback((evt: AgentEvent) => {
    setEvents((prev) => [evt, ...prev].slice(0, 50));
    setTimeline((prev) =>
      [
        {
          timestamp: evt.created_at,
          agent_type: evt.agent_type,
          ooda_phase: evt.ooda_phase,
          event_type: evt.event_type,
          severity: evt.severity,
          title: evt.title,
          event_id: evt.event_id,
        },
        ...prev,
      ].slice(0, 100),
    );
    if (evt.execution_mode === "PENDING_APPROVAL") {
      refreshPending();
    }
  }, [refreshPending]);

  return {
    events,
    timeline,
    pendingActions,
    selectedEvent,
    setSelectedEvent,
    addEvent,
    refreshAll,
    refreshPending,
  };
}
