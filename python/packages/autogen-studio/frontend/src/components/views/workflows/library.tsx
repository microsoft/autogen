import React, { useState, useEffect } from "react";
import { Input, Card, Tag, Tooltip, Spin } from "antd";
import { ChevronsRight, ChevronsLeft, Search } from "lucide-react";
import { Step } from "./types";
import { workflowAPI } from "./api";

interface StepLibraryProps {
  onAddStep: (step: Step) => void;
  isCompact: boolean;
  onToggleCompact: () => void;
}

export const StepLibrary: React.FC<StepLibraryProps> = ({
  onAddStep,
  isCompact,
  onToggleCompact,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchSteps = async () => {
      try {
        setIsLoading(true);
        const response = await workflowAPI.getSteps();
        if (response.success) {
          setSteps(response.data);
        }
      } catch (error) {
        console.error("Failed to fetch steps", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSteps();
  }, []);

  const filteredSteps = steps.filter((step) =>
    step.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (isCompact) {
    return (
      <div className="p-2 flex flex-col items-center">
        <Tooltip title="Expand Library" placement="left">
          <button
            onClick={onToggleCompact}
            className="p-2 text-secondary hover:text-primary rounded hover:bg-secondary/20 mb-3"
          >
            <ChevronsLeft size={16} />
          </button>
        </Tooltip>
        <div className="space-y-2">
          {steps?.slice(0, 5).map((step) => (
            <Tooltip key={step.id} title={`Add ${step.name}`} placement="left">
              <button
                onClick={() => onAddStep(step)}
                className="w-8 h-8 bg-secondary rounded text-primary hover:bg-accent transition-colors flex items-center justify-center text-xs font-medium"
              >
                {step.name.charAt(0).toUpperCase()}
              </button>
            </Tooltip>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-primary">Step Library</h3>
        <Tooltip title="Collapse Library">
          <button
            onClick={onToggleCompact}
            className="p-2 text-secondary hover:text-primary rounded hover:bg-secondary/20"
          >
            <ChevronsRight size={16} />
          </button>
        </Tooltip>
      </div>
      <div className="relative mb-4">
        <Input
          placeholder="Search steps..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          prefix={<Search size={14} className="text-secondary mr-2" />}
          className="bg-tertiary border-secondary"
        />
      </div>
      <div className="flex-1 overflow-y-auto pr-2">
        {isLoading ? (
          <div className="flex justify-center mt-4">
            <Spin />
          </div>
        ) : (
          <div className="space-y-2">
            {filteredSteps.map((step) => (
              <Card
                key={step.id}
                hoverable
                className="bg-secondary border-secondary shadow-sm hover:shadow-md transition-shadow"
                onClick={() => onAddStep(step)}
                size="small"
              >
                <div className="font-semibold text-primary">{step.name}</div>
                <p className="text-xs text-secondary mt-1 mb-2">
                  {step.description}
                </p>
                <div className="flex flex-wrap gap-1">
                  <Tag color="blue" className="text-xs">
                    {step.model || "Default Model"}
                  </Tag>
                  {step.tools && step.tools.length > 0 && (
                    <Tag color="geekblue" className="text-xs">
                      {step.tools.length} tools
                    </Tag>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
