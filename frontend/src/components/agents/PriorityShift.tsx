import type { AgentEvent } from "../../types";

interface Change {
  order_code: string;
  customer_grade: string;
  old_score: number;
  new_score: number;
  direction: string;
}

interface Props {
  events: AgentEvent[];
}

export default function PriorityShift({ events }: Props) {
  // Find the most recent PRIORITY/DECIDE event with changes
  const priorityEvt = events.find(
    (e) =>
      e.ooda_phase === "DECIDE" &&
      e.payload &&
      ((e.payload as Record<string, unknown>).changed_count as number) > 0,
  );

  const changes: Change[] = priorityEvt
    ? ((priorityEvt.payload as Record<string, unknown>).changes as Change[] ?? [])
    : [];

  if (changes.length === 0) {
    return (
      <div className="bg-card rounded-xl p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-dark mb-2">
          Priority Shift
        </h3>
        <p className="text-xs text-gray-400 text-center py-4">
          No priority changes yet
        </p>
      </div>
    );
  }

  // SVG bump chart
  const sorted = [...changes].sort(
    (a, b) => b.new_score - b.old_score - (a.new_score - a.old_score),
  );
  const maxScore = Math.max(...sorted.map((c) => Math.max(c.old_score, c.new_score)), 100);
  const svgH = Math.max(sorted.length * 28 + 20, 80);
  const leftX = 80;
  const rightX = 260;
  const topY = 20;

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-dark mb-2">Priority Shift</h3>
      <div className="overflow-x-auto">
        <svg width={340} height={svgH} viewBox={`0 0 340 ${svgH}`}>
          {/* Axis labels */}
          <text x={leftX} y={12} textAnchor="middle" fill="#94a3b8" fontSize={9}>
            Before
          </text>
          <text x={rightX} y={12} textAnchor="middle" fill="#94a3b8" fontSize={9}>
            After
          </text>

          {sorted.map((c, i) => {
            const y = topY + i * 28 + 14;
            const oldNorm = (c.old_score / maxScore) * 100;
            const newNorm = (c.new_score / maxScore) * 100;
            const isUp = c.direction === "상향";
            const color = isUp ? "#10B981" : "#EF4444";

            return (
              <g key={c.order_code}>
                {/* Order code label */}
                <text x={4} y={y + 4} fill="#64748b" fontSize={9}>
                  {c.order_code.replace("ORD-20260206-", "#")}
                </text>

                {/* Line connecting old → new */}
                <line
                  x1={leftX}
                  y1={y}
                  x2={rightX}
                  y2={y}
                  stroke={color}
                  strokeWidth={2}
                  strokeDasharray={isUp ? "0" : "4 2"}
                  opacity={0.6}
                />

                {/* Old score dot */}
                <circle cx={leftX} cy={y} r={4} fill={color} />
                <text
                  x={leftX}
                  y={y + 14}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize={8}
                >
                  {c.old_score.toFixed(0)}
                </text>

                {/* New score dot */}
                <circle cx={rightX} cy={y} r={4} fill={color} />
                <text
                  x={rightX}
                  y={y + 14}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize={8}
                >
                  {c.new_score.toFixed(0)}
                </text>

                {/* Direction arrow */}
                <text
                  x={rightX + 20}
                  y={y + 4}
                  fill={color}
                  fontSize={10}
                  fontWeight={700}
                >
                  {isUp ? "▲" : "▼"}
                </text>

                {/* Grade */}
                <text x={rightX + 36} y={y + 4} fill="#94a3b8" fontSize={8}>
                  {c.customer_grade}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Description */}
      {priorityEvt && (
        <p className="text-[10px] text-gray-400 mt-2">{priorityEvt.description}</p>
      )}
    </div>
  );
}
