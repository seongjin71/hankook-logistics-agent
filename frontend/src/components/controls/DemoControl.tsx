import { useState, useEffect, useCallback } from "react";
import { Play, Square, RotateCcw, Loader2 } from "lucide-react";
import { startDemo, stopDemo, getDemoStatus, resetSimulation } from "../../api/client";

interface DemoStatus {
  status: string;
  phase_name: string | null;
  phase_index: number | null;
  total_phases: number;
  phase_elapsed: number;
  phase_duration: number;
  elapsed_seconds: number;
  total_seconds: number;
}

export default function DemoControl() {
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const poll = useCallback(async () => {
    try {
      const data = (await getDemoStatus()) as unknown as DemoStatus;
      setStatus(data);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    poll();
    const id = setInterval(poll, 1000);
    return () => clearInterval(id);
  }, [poll]);

  const isRunning = status?.status === "running";

  const handleStart = async () => {
    setLoading(true);
    try {
      await startDemo();
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    await stopDemo();
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await resetSimulation();
    } finally {
      setLoading(false);
    }
  };

  const progress =
    isRunning && status?.phase_duration
      ? Math.min((status.phase_elapsed / status.phase_duration) * 100, 100)
      : 0;

  return (
    <div className="flex items-center gap-2">
      {isRunning ? (
        <>
          {/* Progress display */}
          <div className="flex flex-col items-end mr-1">
            <span className="text-[10px] text-white/60">
              Phase {(status?.phase_index ?? 0) + 1}/{status?.total_phases ?? 5}:{" "}
              {status?.phase_name}
            </span>
            <div className="w-32 h-1.5 bg-white/20 rounded-full overflow-hidden mt-0.5">
              <div
                className="h-full bg-primary rounded-full transition-all duration-1000"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
          <button
            onClick={handleStop}
            className="flex items-center gap-1 bg-white/20 hover:bg-white/30 text-white text-xs px-2.5 py-1.5 rounded-md transition-colors cursor-pointer"
          >
            <Square size={12} /> Stop
          </button>
        </>
      ) : (
        <>
          <button
            onClick={handleStart}
            disabled={loading}
            className="flex items-center gap-1 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white text-xs font-medium px-3 py-1.5 rounded-md transition-colors cursor-pointer"
          >
            {loading ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Play size={12} />
            )}
            Demo
          </button>
          <button
            onClick={handleReset}
            disabled={loading}
            title="Reset all data"
            className="flex items-center gap-1 bg-white/10 hover:bg-white/20 disabled:opacity-60 text-white/70 text-xs px-2 py-1.5 rounded-md transition-colors cursor-pointer"
          >
            <RotateCcw size={12} />
          </button>
        </>
      )}
    </div>
  );
}
