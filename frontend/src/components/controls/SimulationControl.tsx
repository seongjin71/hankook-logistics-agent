import { useState } from "react";
import { Zap, Loader2 } from "lucide-react";
import { setSimSpeed, triggerAnomaly } from "../../api/client";

const SPEEDS = [1, 5, 10] as const;

const SCENARIOS = [
  { value: "ORDER_SURGE", label: "Order Surge" },
  { value: "VEHICLE_BREAKDOWN", label: "Vehicle Breakdown" },
  { value: "STOCK_SHORTAGE", label: "Stock Shortage" },
  { value: "SLA_RISK", label: "SLA Risk" },
  { value: "DOCK_CONGESTION", label: "Dock Congestion" },
];

interface Props {
  currentSpeed: number;
}

export default function SimulationControl({ currentSpeed }: Props) {
  const [speed, setSpeed] = useState(currentSpeed);
  const [scenario, setScenario] = useState(SCENARIOS[0].value);
  const [injecting, setInjecting] = useState(false);

  const handleSpeed = async (s: number) => {
    setSpeed(s);
    await setSimSpeed(s).catch(console.error);
  };

  const handleInject = async () => {
    setInjecting(true);
    try {
      await triggerAnomaly(scenario);
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setInjecting(false), 800);
    }
  };

  return (
    <div className="flex items-center gap-3">
      {/* Speed toggle */}
      <div className="flex rounded-md overflow-hidden border border-white/20">
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => handleSpeed(s)}
            className={`px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              speed === s
                ? "bg-primary text-white"
                : "bg-white/10 text-white/70 hover:bg-white/20"
            }`}
          >
            {s}x
          </button>
        ))}
      </div>

      {/* Anomaly trigger */}
      <select
        value={scenario}
        onChange={(e) => setScenario(e.target.value)}
        className="text-xs bg-white/10 text-white/90 border border-white/20 rounded-md px-2 py-1.5 outline-none"
      >
        {SCENARIOS.map((s) => (
          <option key={s.value} value={s.value} className="text-dark">
            {s.label}
          </option>
        ))}
      </select>

      <button
        onClick={handleInject}
        disabled={injecting}
        className="flex items-center gap-1.5 bg-critical hover:bg-critical/90 disabled:opacity-60 text-white text-xs font-medium px-3 py-1.5 rounded-md transition-colors cursor-pointer"
      >
        {injecting ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Zap size={14} />
        )}
        Inject
      </button>
    </div>
  );
}
