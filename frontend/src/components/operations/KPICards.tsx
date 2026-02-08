import {
  Package,
  ShieldCheck,
  Clock,
  BrainCircuit,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import type { DashboardOverview } from "../../types";
import { formatNumber } from "../../utils/formatters";

interface Props {
  overview: DashboardOverview;
}

interface CardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  trend?: "up" | "down" | null;
  alert?: boolean;
}

function Card({ icon, label, value, sub, trend, alert }: CardProps) {
  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-gray-400">{icon}</span>
        {trend === "up" && <TrendingUp size={14} className="text-success" />}
        {trend === "down" && (
          <TrendingDown size={14} className="text-critical" />
        )}
      </div>
      <div
        className={`text-2xl font-bold ${alert ? "text-critical" : "text-dark"}`}
      >
        {value}
      </div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function KPICards({ overview }: Props) {
  const { orders_summary, vehicles_summary, recent_anomalies } = overview;
  const totalOrders = orders_summary.total;
  const shipped =
    (orders_summary.by_status["SHIPPED"] ?? 0) +
    (orders_summary.by_status["DELIVERED"] ?? 0);
  const slaRate = totalOrders > 0 ? shipped / totalOrders : 1;
  const slaAlert = slaRate < 0.95;

  const activeVehicles = Object.entries(vehicles_summary.by_status)
    .filter(([s]) => s === "IN_TRANSIT" || s === "LOADING")
    .reduce((acc, [, c]) => acc + c, 0);
  const totalVehicles = Object.values(vehicles_summary.by_status).reduce(
    (a, b) => a + b,
    0,
  );

  return (
    <div className="grid grid-cols-2 gap-3">
      <Card
        icon={<Package size={18} />}
        label="Total Orders"
        value={formatNumber(totalOrders)}
        trend={totalOrders > 0 ? "up" : null}
      />
      <Card
        icon={<ShieldCheck size={18} />}
        label="SLA Rate"
        value={`${(slaRate * 100).toFixed(1)}%`}
        alert={slaAlert}
        trend={slaAlert ? "down" : "up"}
      />
      <Card
        icon={<Clock size={18} />}
        label="Active Vehicles"
        value={`${activeVehicles} / ${totalVehicles}`}
        sub="vehicles in operation"
      />
      <Card
        icon={<BrainCircuit size={18} />}
        label="Agent Interventions"
        value={formatNumber(recent_anomalies)}
        trend={recent_anomalies > 5 ? "up" : null}
      />
    </div>
  );
}
