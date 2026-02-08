/* ── Dashboard Overview (matches backend schema) ── */
export interface OrdersSummary {
  total: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface InventorySummary {
  low_stock_count: number;
  total_skus: number;
}

export interface VehiclesSummary {
  by_status: Record<string, number>;
}

export interface VehicleDetail {
  vehicle_code: string;
  vehicle_type: string;
  status: string;
  destination: string | null;
  fuel_level: number;
  speed_kmh: number;
}

export interface LowStockDetail {
  warehouse_code: string;
  product_code: string;
  product_name: string;
  available_qty: number;
  safety_stock: number;
}

export interface SimulationStatus {
  speed: number;
  is_running: boolean;
}

export interface DashboardOverview {
  orders_summary: OrdersSummary;
  inventory_summary: InventorySummary;
  vehicles_summary: VehiclesSummary;
  simulation: SimulationStatus;
  vehicles: VehicleDetail[];
  low_stock_details: LowStockDetail[];
  recent_anomalies: number;
}

/* ── Orders ── */
export type OrderStatus =
  | "RECEIVED"
  | "PICKING"
  | "PACKED"
  | "LOADING"
  | "SHIPPED"
  | "DELIVERED";

export interface Order {
  id: number;
  order_code: string;
  customer_name: string;
  customer_grade: string;
  warehouse_code: string;
  status: OrderStatus;
  priority_score: number;
  order_date: string;
  due_date: string;
  total_amount: number;
  item_count: number;
}

/* ── Agent Events ── */
export type AgentType = "MONITOR" | "ANOMALY" | "PRIORITY" | "ACTION";
export type OODAPhase = "OBSERVE" | "ORIENT" | "DECIDE" | "ACT";
export type Severity = "INFO" | "WARNING" | "CRITICAL";
export type ExecutionMode =
  | "AUTO"
  | "HUMAN_APPROVED"
  | "PENDING_APPROVAL"
  | "ESCALATED";

export interface AgentEvent {
  id: number;
  event_id: string;
  agent_type: AgentType;
  ooda_phase: OODAPhase;
  event_type: string;
  severity: Severity;
  title: string;
  description: string;
  payload: Record<string, unknown> | null;
  reasoning: string | null;
  confidence: number | null;
  action_taken: string | null;
  execution_mode: ExecutionMode | null;
  parent_event_id: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface TimelineEvent {
  timestamp: string;
  agent_type: AgentType;
  ooda_phase: OODAPhase;
  event_type: string;
  severity: Severity;
  title: string;
  event_id: string;
}

/* ── Pending Action ── */
export interface PendingAction {
  event_id: string;
  event_type: string;
  title: string;
  description: string;
  action_type: string;
  reason: string;
  confidence: number | null;
  created_at: string | null;
}

/* ── WebSocket ── */
export type WSMessageType =
  | "dashboard_update"
  | "new_order"
  | "anomaly_detected"
  | "agent_event"
  | "vehicle_update"
  | "priority_changed"
  | "action_executed"
  | "action_approved";

export interface WSMessage {
  type: WSMessageType;
  data: unknown;
  timestamp?: string;
}
