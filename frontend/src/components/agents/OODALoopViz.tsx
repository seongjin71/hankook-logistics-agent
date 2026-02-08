import { useEffect, useState } from "react";
import type { OODAPhase } from "../../types";

interface Props {
  activePhase: OODAPhase | null;
  activeEventType: string | null;
}

const PHASES: { phase: OODAPhase; label: string; agent: string; color: string }[] = [
  { phase: "OBSERVE", label: "Observe", agent: "Monitor", color: "#6366F1" },
  { phase: "ORIENT", label: "Orient", agent: "Anomaly", color: "#EC4899" },
  { phase: "DECIDE", label: "Decide", agent: "Priority", color: "#F59E0B" },
  { phase: "ACT", label: "Act", agent: "Action", color: "#10B981" },
];

export default function OODALoopViz({ activePhase, activeEventType }: Props) {
  const [highlight, setHighlight] = useState<OODAPhase | null>(null);

  useEffect(() => {
    setHighlight(activePhase);
  }, [activePhase]);

  const cx = 130;
  const cy = 130;
  const r = 95;
  const arcWidth = 32;

  function arcPath(index: number): string {
    const gap = 0.04;
    const startAngle = (index * Math.PI) / 2 + gap - Math.PI / 2;
    const endAngle = ((index + 1) * Math.PI) / 2 - gap - Math.PI / 2;
    const outerR = r;
    const innerR = r - arcWidth;
    const x1 = cx + outerR * Math.cos(startAngle);
    const y1 = cy + outerR * Math.sin(startAngle);
    const x2 = cx + outerR * Math.cos(endAngle);
    const y2 = cy + outerR * Math.sin(endAngle);
    const x3 = cx + innerR * Math.cos(endAngle);
    const y3 = cy + innerR * Math.sin(endAngle);
    const x4 = cx + innerR * Math.cos(startAngle);
    const y4 = cy + innerR * Math.sin(startAngle);
    return `M${x1},${y1} A${outerR},${outerR} 0 0 1 ${x2},${y2} L${x3},${y3} A${innerR},${innerR} 0 0 0 ${x4},${y4} Z`;
  }

  function labelPos(index: number): { x: number; y: number } {
    const angle = ((index + 0.5) * Math.PI) / 2 - Math.PI / 2;
    const lr = r - arcWidth / 2;
    return { x: cx + lr * Math.cos(angle), y: cy + lr * Math.sin(angle) };
  }

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-dark mb-2">OODA Loop</h3>
      <div className="flex justify-center">
        <svg width={260} height={260} viewBox="0 0 260 260">
          {PHASES.map((p, i) => {
            const active = highlight === p.phase;
            const lp = labelPos(i);
            return (
              <g key={p.phase}>
                <path
                  d={arcPath(i)}
                  fill={active ? p.color : `${p.color}33`}
                  stroke={p.color}
                  strokeWidth={active ? 2 : 0.5}
                  style={{ transition: "fill 0.4s, stroke-width 0.3s" }}
                />
                <text
                  x={lp.x}
                  y={lp.y - 6}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={active ? "#fff" : p.color}
                  fontSize={11}
                  fontWeight={700}
                >
                  {p.label}
                </text>
                <text
                  x={lp.x}
                  y={lp.y + 8}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={active ? "#ffffffcc" : `${p.color}99`}
                  fontSize={8}
                >
                  {p.agent}
                </text>
              </g>
            );
          })}

          {/* Center text */}
          <text
            x={cx}
            y={cy - 6}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#1A1A2E"
            fontSize={11}
            fontWeight={600}
          >
            {highlight ? activeEventType ?? "Processing" : "Monitoring..."}
          </text>
          <text
            x={cx}
            y={cy + 10}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#94a3b8"
            fontSize={9}
          >
            {highlight ? highlight : "IDLE"}
          </text>
        </svg>
      </div>
    </div>
  );
}
