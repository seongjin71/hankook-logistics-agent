import { useState, useEffect } from "react";
import { Activity } from "lucide-react";
import SimulationControl from "../controls/SimulationControl";
import DemoControl from "../controls/DemoControl";

interface Props {
  isConnected: boolean;
  simulationSpeed: number;
  alertFlash: boolean;
}

export default function Header({ isConnected, simulationSpeed, alertFlash }: Props) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <>
      {/* Connection lost banner */}
      {!isConnected && (
        <div className="bg-critical text-white text-xs text-center py-1.5 font-medium animate-pulse">
          Connection Lost. Reconnecting...
        </div>
      )}

      <header
        className={`h-[60px] bg-dark flex items-center justify-between px-6 shrink-0 transition-colors duration-300 ${
          alertFlash ? "bg-critical/80" : ""
        }`}
      >
        {/* Left: Logo */}
        <div className="flex items-center gap-3">
          <span className="text-primary font-extrabold text-lg tracking-wider">
            HANKOOK
          </span>
          <span className="text-white/50 text-sm">|</span>
          <span className="text-white/80 text-sm font-medium">
            AI Logistics Agent
          </span>
        </div>

        {/* Center: Status + Demo */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? "bg-success" : "bg-critical"
              }`}
            />
            <span className="text-white/70 text-xs">
              {isConnected ? "System Active" : "Disconnected"}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-white/50 text-xs">
            <Activity size={12} />
            <span>
              {time.toLocaleTimeString("ko-KR", { hour12: false })}
            </span>
          </div>
          <DemoControl />
        </div>

        {/* Right: Controls */}
        <SimulationControl currentSpeed={simulationSpeed} />
      </header>
    </>
  );
}
