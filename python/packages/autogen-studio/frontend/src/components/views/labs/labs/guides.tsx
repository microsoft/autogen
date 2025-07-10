import React from "react";
import { Lab } from "../types";
import ComponentLab from "./component";
import ToolMakerLab from "./tool";

interface LabContentProps {
  lab: Lab;
}

export const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text);
};
export const LabContent: React.FC<LabContentProps> = ({ lab }) => {
  // Render different content based on guide type and id
  switch (lab.id) {
    case "python-setup":
      return <ComponentLab />;
    case "tool-maker":
      return <ToolMakerLab />;
    default:
      return (
        <div className="text-secondary">
          A Lab with the title <strong>{lab.title}</strong> is work in progress!
        </div>
      );
  }
};

export default LabContent;
