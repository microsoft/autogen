import React from "react";
import { Loader2 } from "lucide-react";

export const LoadingIndicator = ({ size = 16 }: { size: number }) => (
  <div className="inline-flex items-center gap-2 text-accent   mr-2">
    <Loader2 size={size} className="animate-spin" />
  </div>
);

export const LoadingDots = ({ size = 8 }) => {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="bg-accent rounded-full animate-bounce"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          animationDuration: "0.6s",
        }}
      />
      <span
        className="bg-accent rounded-full animate-bounce"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          animationDuration: "0.6s",
          animationDelay: "0.2s",
        }}
      />
      <span
        className="bg-accent rounded-full animate-bounce"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          animationDuration: "0.6s",
          animationDelay: "0.4s",
        }}
      />
    </span>
  );
};

export default LoadingDots;
