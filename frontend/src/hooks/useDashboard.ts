import { useState, useEffect, useCallback } from "react";
import { fetchOverview } from "../api/client";
import type { DashboardOverview } from "../types";

const EMPTY_OVERVIEW: DashboardOverview = {
  orders_summary: { total: 0, by_status: {}, by_priority: {} },
  inventory_summary: { low_stock_count: 0, total_skus: 0 },
  vehicles_summary: { by_status: {} },
  simulation: { speed: 1, is_running: false },
  vehicles: [],
  low_stock_details: [],
  recent_anomalies: 0,
};

export function useDashboard() {
  const [overview, setOverview] = useState<DashboardOverview>(EMPTY_OVERVIEW);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchOverview();
      setOverview(data as unknown as DashboardOverview);
    } catch (e) {
      console.error("Dashboard fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  const updateOverview = useCallback((data: unknown) => {
    if (!data || typeof data !== "object") return;
    const d = data as Record<string, unknown>;

    // WebSocket dashboard_update sends {orders, inventory, vehicles}
    // which differs from the REST API shape {orders_summary, inventory_summary, vehicles_summary}
    // Map WS keys to the expected DashboardOverview structure
    setOverview((prev) => ({
      ...prev,
      ...(d.orders_summary ? { orders_summary: d.orders_summary as DashboardOverview["orders_summary"] } : {}),
      ...(d.orders ? { orders_summary: d.orders as DashboardOverview["orders_summary"] } : {}),
      ...(d.inventory_summary ? { inventory_summary: d.inventory_summary as DashboardOverview["inventory_summary"] } : {}),
      ...(d.inventory ? { inventory_summary: d.inventory as DashboardOverview["inventory_summary"] } : {}),
      ...(d.vehicles_summary ? { vehicles_summary: d.vehicles_summary as DashboardOverview["vehicles_summary"] } : {}),
      ...(d.vehicles && !Array.isArray(d.vehicles) ? { vehicles_summary: d.vehicles as DashboardOverview["vehicles_summary"] } : {}),
      ...(d.simulation ? { simulation: d.simulation as DashboardOverview["simulation"] } : {}),
    }));
  }, []);

  return { overview, loading, refresh, updateOverview };
}
