import { useState } from "react";
import { Truck } from "lucide-react";
import type { VehicleDetail } from "../../types";

const STATUS_COLOR: Record<string, string> = {
  AVAILABLE: "bg-success",
  IN_TRANSIT: "bg-info",
  LOADING: "bg-warning",
  MAINTENANCE: "bg-gray-400",
  BREAKDOWN: "bg-critical",
};

const STATUS_LABEL: Record<string, string> = {
  AVAILABLE: "Available",
  IN_TRANSIT: "In Transit",
  LOADING: "Loading",
  MAINTENANCE: "Maint.",
  BREAKDOWN: "Breakdown",
};

interface Props {
  vehicles: VehicleDetail[];
}

export default function VehicleStatus({ vehicles }: Props) {
  const [hover, setHover] = useState<string | null>(null);

  const statusCounts: Record<string, number> = {};
  vehicles.forEach((v) => {
    statusCounts[v.status] = (statusCounts[v.status] ?? 0) + 1;
  });

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Truck size={14} className="text-info" />
        <h3 className="text-sm font-semibold text-dark">Fleet Status</h3>
        <span className="text-xs text-gray-400 ml-auto">
          {vehicles.length} vehicles
        </span>
      </div>

      {/* Status summary */}
      <div className="flex gap-3 mb-3 flex-wrap">
        {Object.entries(statusCounts).map(([st, cnt]) => (
          <div key={st} className="flex items-center gap-1">
            <span
              className={`w-2 h-2 rounded-full ${STATUS_COLOR[st] ?? "bg-gray-300"}`}
            />
            <span className="text-[10px] text-gray-500">
              {STATUS_LABEL[st] ?? st} {cnt}
            </span>
          </div>
        ))}
      </div>

      {/* Vehicle grid */}
      <div className="grid grid-cols-5 gap-2">
        {vehicles.map((v) => (
          <div
            key={v.vehicle_code}
            className="relative flex flex-col items-center cursor-pointer"
            onMouseEnter={() => setHover(v.vehicle_code)}
            onMouseLeave={() => setHover(null)}
          >
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center ${STATUS_COLOR[v.status] ?? "bg-gray-300"} text-white`}
            >
              <Truck size={14} />
            </div>
            <span className="text-[9px] text-gray-500 mt-0.5">
              {v.vehicle_code.replace("VH-", "")}
            </span>

            {/* Tooltip */}
            {hover === v.vehicle_code && (
              <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-dark text-white text-[10px] rounded-lg p-2 w-32 z-50 shadow-lg">
                <div className="font-medium">{v.vehicle_code}</div>
                <div className="text-white/70">{v.vehicle_type}</div>
                <div className="text-white/70">
                  {STATUS_LABEL[v.status] ?? v.status}
                </div>
                {v.destination && (
                  <div className="text-white/70">To: {v.destination}</div>
                )}
                <div className="text-white/70">
                  Fuel: {v.fuel_level.toFixed(0)}% | {v.speed_kmh.toFixed(0)}km/h
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
