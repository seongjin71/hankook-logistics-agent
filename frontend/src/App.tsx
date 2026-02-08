import { useEffect, useCallback, useState, useRef } from "react";
import Header from "./components/layout/Header";
import DashboardLayout from "./components/layout/DashboardLayout";
import KPICards from "./components/operations/KPICards";
import OrderStatusChart from "./components/operations/OrderStatusChart";
import InventoryGauge from "./components/operations/InventoryGauge";
import VehicleStatus from "./components/operations/VehicleStatus";
import OODALoopViz from "./components/agents/OODALoopViz";
import AgentTimeline from "./components/agents/AgentTimeline";
import DecisionDetail from "./components/agents/DecisionDetail";
import PriorityShift from "./components/agents/PriorityShift";
import AlertFeed from "./components/actions/AlertFeed";
import ActionList from "./components/actions/ActionList";
import ApprovalQueue from "./components/actions/ApprovalQueue";
import { useWebSocket } from "./hooks/useWebSocket";
import { useDashboard } from "./hooks/useDashboard";
import { useAgentEvents } from "./hooks/useAgentEvents";
import type { OODAPhase, AgentEvent } from "./types";

export default function App() {
  const { isConnected, subscribe } = useWebSocket();
  const { overview, updateOverview } = useDashboard();
  const {
    events,
    timeline,
    pendingActions,
    selectedEvent,
    setSelectedEvent,
    addEvent,
    refreshAll,
    refreshPending,
  } = useAgentEvents();

  const [activePhase, setActivePhase] = useState<OODAPhase | null>(null);
  const [activeEventType, setActiveEventType] = useState<string | null>(null);
  const [alertFlash, setAlertFlash] = useState(false);
  const phaseTimer = useRef<ReturnType<typeof setTimeout>>();

  // WebSocket subscriptions
  useEffect(() => {
    const unsubs = [
      subscribe("dashboard_update", (data) => {
        updateOverview(data);
      }),
      subscribe("agent_event", (data) => {
        const evt = data as AgentEvent;
        addEvent(evt);

        // Animate OODA loop
        clearTimeout(phaseTimer.current);
        setActivePhase(evt.ooda_phase);
        setActiveEventType(evt.event_type);
        phaseTimer.current = setTimeout(() => {
          setActivePhase(null);
          setActiveEventType(null);
        }, 3000);
      }),
      subscribe("anomaly_detected", () => {
        // Red flash on header
        setAlertFlash(true);
        setTimeout(() => setAlertFlash(false), 600);
        refreshAll();
      }),
      subscribe("action_approved", () => {
        refreshPending();
        refreshAll();
      }),
      subscribe("demo_phase" as never, () => {
        refreshAll();
      }),
      subscribe("system_reset" as never, () => {
        refreshAll();
      }),
    ];
    return () => {
      unsubs.forEach((u) => u());
      clearTimeout(phaseTimer.current);
    };
  }, [subscribe, updateOverview, addEvent, refreshAll, refreshPending]);

  const handleTimelineSelect = useCallback(
    (eventId: string) => {
      const evt = events.find((e) => e.event_id === eventId) ?? null;
      setSelectedEvent(evt);
    },
    [events, setSelectedEvent],
  );

  const handleActionDone = useCallback(() => {
    setSelectedEvent(null);
    refreshPending();
    refreshAll();
  }, [setSelectedEvent, refreshPending, refreshAll]);

  return (
    <div className="h-screen flex flex-col bg-bg">
      <Header
        isConnected={isConnected}
        simulationSpeed={overview.simulation.speed}
        alertFlash={alertFlash}
      />
      <DashboardLayout
        left={
          <>
            <KPICards overview={overview} />
            <OrderStatusChart byStatus={overview.orders_summary.by_status} />
            <InventoryGauge items={overview.low_stock_details} />
            <VehicleStatus vehicles={overview.vehicles} />
          </>
        }
        center={
          <>
            <OODALoopViz
              activePhase={activePhase}
              activeEventType={activeEventType}
            />
            <AgentTimeline
              timeline={timeline}
              events={events}
              onSelect={handleTimelineSelect}
            />
            <DecisionDetail
              event={selectedEvent}
              onClose={() => setSelectedEvent(null)}
              onActionDone={handleActionDone}
            />
            <PriorityShift events={events} />
          </>
        }
        right={
          <>
            <AlertFeed alerts={timeline} />
            <ActionList events={events} />
            <ApprovalQueue
              actions={pendingActions}
              onActionDone={handleActionDone}
            />
          </>
        }
      />
    </div>
  );
}
