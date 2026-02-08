import { X, Clock, Tag, CheckCircle2, XCircle } from "lucide-react";
import type { AgentEvent } from "../../types";
import { formatTime, severityBg, executionModeBadge } from "../../utils/formatters";
import { approveAction, rejectAction } from "../../api/client";

interface Props {
  event: AgentEvent | null;
  onClose: () => void;
  onActionDone: () => void;
}

export default function DecisionDetail({ event, onClose, onActionDone }: Props) {
  if (!event) {
    return (
      <div className="bg-card rounded-xl p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-dark mb-2">Decision Detail</h3>
        <p className="text-xs text-gray-400 text-center py-6">
          Click a timeline event to view details
        </p>
      </div>
    );
  }

  const handleApprove = async () => {
    await approveAction(event.event_id);
    onActionDone();
  };

  const handleReject = async () => {
    await rejectAction(event.event_id, "Dashboard reject");
    onActionDone();
  };

  const badge = event.execution_mode
    ? executionModeBadge(event.execution_mode)
    : null;

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-dark">Decision Detail</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 cursor-pointer"
        >
          <X size={16} />
        </button>
      </div>

      {/* Header */}
      <div className="space-y-2 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${severityBg(event.severity)}`}
          >
            {event.severity}
          </span>
          {badge && (
            <span
              className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${badge.className}`}
            >
              {badge.label}
            </span>
          )}
          <span className="text-[10px] text-gray-400">
            {event.agent_type} / {event.ooda_phase}
          </span>
        </div>
        <h4 className="text-sm font-semibold text-dark">{event.title}</h4>
      </div>

      {/* Meta */}
      <div className="grid grid-cols-2 gap-2 text-xs mb-3">
        <div className="flex items-center gap-1 text-gray-500">
          <Clock size={11} /> {formatTime(event.created_at)}
        </div>
        <div className="flex items-center gap-1 text-gray-500">
          <Tag size={11} /> {event.event_type}
        </div>
      </div>

      {/* Description */}
      <div className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 mb-3">
        {event.description}
      </div>

      {/* Reasoning */}
      {event.reasoning && (
        <div className="mb-3">
          <h5 className="text-xs font-semibold text-gray-500 mb-1">Reasoning</h5>
          <div className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap">
            {event.reasoning}
          </div>
        </div>
      )}

      {/* Action taken */}
      {event.action_taken && (
        <div className="mb-3">
          <h5 className="text-xs font-semibold text-gray-500 mb-1">Action</h5>
          <div className="text-xs text-gray-600">{event.action_taken}</div>
        </div>
      )}

      {/* Confidence */}
      {event.confidence != null && (
        <div className="mb-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-gray-500">Confidence</span>
            <span className="font-medium">
              {(event.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${event.confidence * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Approve / Reject */}
      {event.execution_mode === "PENDING_APPROVAL" && (
        <div className="flex gap-2 mt-4">
          <button
            onClick={handleApprove}
            className="flex-1 flex items-center justify-center gap-1 bg-success hover:bg-success/90 text-white text-xs font-medium py-2 rounded-lg transition-colors cursor-pointer"
          >
            <CheckCircle2 size={14} /> Approve
          </button>
          <button
            onClick={handleReject}
            className="flex-1 flex items-center justify-center gap-1 bg-critical hover:bg-critical/90 text-white text-xs font-medium py-2 rounded-lg transition-colors cursor-pointer"
          >
            <XCircle size={14} /> Reject
          </button>
        </div>
      )}
    </div>
  );
}
