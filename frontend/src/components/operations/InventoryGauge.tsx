import { AlertTriangle } from "lucide-react";
import type { LowStockDetail } from "../../types";

interface Props {
  items: LowStockDetail[];
}

function barColor(ratio: number): string {
  if (ratio >= 0.8) return "bg-success";
  if (ratio >= 0.3) return "bg-warning";
  return "bg-critical";
}

export default function InventoryGauge({ items }: Props) {
  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle size={14} className="text-warning" />
        <h3 className="text-sm font-semibold text-dark">Low Stock Items</h3>
        {items.length > 0 && (
          <span className="ml-auto text-[10px] text-gray-400">
            {items.length} items
          </span>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-xs text-gray-400">No critical stock items</p>
      ) : (
        <div className="space-y-2 max-h-[200px] overflow-y-auto">
          {items.map((item, i) => {
            const ratio =
              item.safety_stock > 0
                ? item.available_qty / item.safety_stock
                : 0;
            return (
              <div key={i}>
                <div className="flex justify-between text-xs mb-0.5">
                  <span className="text-gray-600 truncate max-w-[60%]">
                    {item.product_name}
                  </span>
                  <span className="text-gray-400">
                    {item.available_qty}/{item.safety_stock}
                  </span>
                </div>
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${barColor(ratio)}`}
                    style={{ width: `${Math.min(ratio * 100, 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
