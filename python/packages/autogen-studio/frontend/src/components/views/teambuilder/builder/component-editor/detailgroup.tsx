import React from "react";

interface DetailGroupProps {
  title: string;
  children: React.ReactNode;
}

const DetailGroup: React.FC<DetailGroupProps> = ({ title, children }) => {
  return (
    <div className="relative mt-2 mb-4">
      {/* Border container with padding */}
      <div className="border border-secondary rounded-lg p-2 px-3 pt-6">
        {/* Floating title */}
        <div className="absolute -top-3 left-3 px-2 bg-primary">
          <span className="text-xs text-primary">{title}</span>
        </div>
        {/* Content */}
        <div>{children}</div>
      </div>
    </div>
  );
};

export default DetailGroup;
