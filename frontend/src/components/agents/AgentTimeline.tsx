import {
  Eye,
  Search,
  Scale,
  Play,
} from "lucide-react";
import type { TimelineEvent, AgentEvent } from "../../types";
import { formatTime, severityBg, agentColor } from "../../utils/formatters";

interface Props {
  timeline: TimelineEvent[];
  onSelect: (eventId: string) => void;
  events: AgentEvent[];
}

const PHASE_ICON: Record<string, React.ReactNode> = {
  OBSERVE: <Eye size={12} />,
  ORIENT: <Search size={12} />,
  DECIDE: <Scale size={12} />,
  ACT: <Play size={12} />,
};

export default function AgentTimeline({ timeline, onSelect, events }: Props) {
  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-dark mb-3">Agent Timeline</h3>
      <div className="space-y-0 max-h-[360px] overflow-y-auto">
        {timeline.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">
            No events yet
          </p>
        )}
        {timeline.map((evt, i) => {
          const color = agentColor(evt.agent_type);
          return (
            <div
              key={`${evt.event_id}-${i}`}
              className="flex gap-3 animate-slide-in cursor-pointer hover:bg-gray-50 rounded-lg p-2 transition-colors"
              onClick={() => {
                const full = events.find((e) => e.event_id === evt.event_id);
                if (full) onSelect(evt.event_id);
              }}
            >
              {/* Left line + icon */}
              <div className="flex flex-col items-center">
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-white shrink-0"
                  style={{ backgroundColor: color }}
                >
                  {PHASE_ICON[evt.ooda_phase] ?? <Eye size={12} />}
                </div>
                {i < timeline.length - 1 && (
                  <div
                    className="w-0.5 flex-1 mt-1"
                    style={{ backgroundColor: `${color}40` }}
                  />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-400">
                    {formatTime(evt.timestamp)}
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${severityBg(evt.severity)}`}
                  >
                    {evt.severity}
                  </span>
                </div>
                <p className="text-xs text-dark font-medium mt-0.5 truncate">
                  {evt.title}
                </p>
                <p className="text-[10px] text-gray-400">
                  {evt.agent_type} / {evt.ooda_phase} / {evt.event_type}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
