import type { ReactNode } from "react";

interface Props {
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
}

export default function DashboardLayout({ left, center, right }: Props) {
  return (
    <div className="flex-1 grid grid-cols-[30%_45%_25%] overflow-hidden">
      <div className="overflow-y-auto p-3 space-y-3">{left}</div>
      <div className="overflow-y-auto p-3 space-y-3 border-x border-gray-200">
        {center}
      </div>
      <div className="overflow-y-auto p-3 space-y-3">{right}</div>
    </div>
  );
}
