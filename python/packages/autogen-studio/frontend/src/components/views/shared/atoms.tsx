import React from "react";
import { Loader2 } from "lucide-react";

export const LoadingIndicator = () => (
  <div className="flex items-center gap-2 text-accent">
    <Loader2 size={16} className="animate-spin" />
  </div>
);
