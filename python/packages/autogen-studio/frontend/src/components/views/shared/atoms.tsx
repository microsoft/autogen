import React from "react";
import { Loader2 } from "lucide-react";

export const LoadingIndicator = ({ size = 16 }: { size: number }) => (
  <div className="inline-flex items-center gap-2 text-accent   mr-2">
    <Loader2 size={size} className="animate-spin" />
  </div>
);
