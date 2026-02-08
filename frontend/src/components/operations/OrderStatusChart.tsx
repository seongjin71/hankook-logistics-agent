import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const STATUS_COLORS: Record<string, string> = {
  RECEIVED: "#3B82F6",
  PICKING: "#F59E0B",
  PACKED: "#8B5CF6",
  LOADING: "#EC4899",
  SHIPPED: "#10B981",
  DELIVERED: "#6B7280",
};

const STATUS_ORDER = [
  "RECEIVED",
  "PICKING",
  "PACKED",
  "LOADING",
  "SHIPPED",
  "DELIVERED",
];

interface Props {
  byStatus: Record<string, number>;
}

export default function OrderStatusChart({ byStatus }: Props) {
  const data = STATUS_ORDER.map((s) => ({
    status: s,
    count: byStatus[s] ?? 0,
  }));

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-dark mb-3">
        Orders by Status
      </h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} barSize={28}>
          <XAxis
            dataKey="status"
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            axisLine={false}
            tickLine={false}
            width={30}
          />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "none",
              boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
            }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((d) => (
              <Cell
                key={d.status}
                fill={STATUS_COLORS[d.status] ?? "#94a3b8"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
