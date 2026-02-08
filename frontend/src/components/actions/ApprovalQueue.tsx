import { useState } from "react";
import { ShieldQuestion, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import type { PendingAction } from "../../types";
import { approveAction, rejectAction } from "../../api/client";
import { timeAgo } from "../../utils/formatters";

interface Props {
  actions: PendingAction[];
  onActionDone: () => void;
}

export default function ApprovalQueue({ actions, onActionDone }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  const handleApprove = async (id: string) => {
    setLoading(id);
    try {
      await approveAction(id);
      onActionDone();
    } finally {
      setLoading(null);
    }
  };

  const handleReject = async (id: string) => {
    setLoading(id);
    try {
      await rejectAction(id, "Dashboard reject");
      onActionDone();
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <ShieldQuestion size={14} className="text-warning" />
        <h3 className="text-sm font-semibold text-dark">Approval Queue</h3>
        {actions.length > 0 && (
          <span className="ml-auto bg-warning text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
            {actions.length}
          </span>
        )}
      </div>

      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {actions.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-3">
            No pending approvals
          </p>
        )}
        {actions.map((a) => (
          <div
            key={a.event_id}
            className="border border-warning/30 rounded-lg p-3 space-y-2"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-dark">
                  {a.action_type}
                </p>
                <p className="text-[10px] text-gray-400">{a.event_type}</p>
              </div>
              {a.created_at && (
                <span className="text-[10px] text-gray-400 whitespace-nowrap">
                  {timeAgo(a.created_at)}
                </span>
              )}
            </div>

            {a.reason && (
              <p className="text-[11px] text-gray-500">{a.reason}</p>
            )}

            {/* Confidence bar */}
            {a.confidence != null && (
              <div>
                <div className="flex justify-between text-[10px] mb-0.5">
                  <span className="text-gray-400">Confidence</span>
                  <span className="font-medium text-dark">
                    {(a.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-warning rounded-full"
                    style={{ width: `${a.confidence * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => handleApprove(a.event_id)}
                disabled={loading === a.event_id}
                className="flex-1 flex items-center justify-center gap-1 bg-success hover:bg-success/90 disabled:opacity-60 text-white text-[11px] font-medium py-1.5 rounded-md transition-colors cursor-pointer"
              >
                {loading === a.event_id ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <CheckCircle2 size={12} />
                )}
                Approve
              </button>
              <button
                onClick={() => handleReject(a.event_id)}
                disabled={loading === a.event_id}
                className="flex-1 flex items-center justify-center gap-1 bg-gray-100 hover:bg-gray-200 disabled:opacity-60 text-gray-600 text-[11px] font-medium py-1.5 rounded-md transition-colors cursor-pointer"
              >
                <XCircle size={12} /> Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
