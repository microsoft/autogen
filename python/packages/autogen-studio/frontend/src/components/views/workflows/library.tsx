import React, { useState, useEffect } from "react";
import { Input, Tag, Tooltip, Spin } from "antd";
import {
  ChevronsRight,
  ChevronsLeft,
  Search,
  Clock,
  RefreshCw,
  ArrowRight,
} from "lucide-react";
import { StepConfig } from "./types";
import { workflowAPI } from "./api";
import { Component } from "../../types/datamodel";

interface StepLibraryProps {
  onAddStep: (step: Component<StepConfig>) => void;
  isCompact: boolean;
  onToggleCompact: () => void;
}

export const StepLibrary: React.FC<StepLibraryProps> = ({
  onAddStep,
  isCompact,
  onToggleCompact,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [steps, setSteps] = useState<Component<StepConfig>[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchSteps = async () => {
      try {
        setIsLoading(true);
        const steps = await workflowAPI.getSteps();
        setSteps(steps);
      } catch (error) {
        console.error("Failed to fetch steps", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSteps();
  }, []);

  const filteredSteps = steps.filter((step) =>
    step.config.metadata.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStepType = (step: Component<StepConfig>) => {
    if (step.config.prefix || step.config.suffix) return "echo";
    if (step.config.input_type_name.includes("Message")) return "message";
    if (step.config.output_type_name.includes("Message")) return "message";
    return "transform";
  };

  const getStepTypeColor = (type: string) => {
    switch (type) {
      case "echo":
        return "bg-blue-100 text-blue-700";
      case "message":
        return "bg-green-100 text-green-700";
      case "transform":
        return "bg-purple-100 text-purple-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

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
            <Tooltip
              key={step.config.step_id}
              title={`Add ${step.config.metadata.name}`}
              placement="left"
            >
              <button
                onClick={() => onAddStep(step)}
                className="w-8 h-8 bg-secondary rounded text-primary hover:bg-accent transition-colors flex items-center justify-center text-xs font-medium"
              >
                {step.config.metadata.name.charAt(0).toUpperCase()}
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
        <h3 className="font-semibold text-primary">Step Library</h3>
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
            {filteredSteps.map((step) => {
              const stepType = getStepType(step);
              const hasTimeout = step.config.metadata.timeout_seconds;
              const hasRetries =
                step.config.metadata.max_retries &&
                step.config.metadata.max_retries > 0;

              return (
                <div
                  key={step.config.step_id}
                  onClick={() => onAddStep(step)}
                  className="bg-secondary border border-secondary rounded p-3 cursor-pointer hover:bg-tertiary hover:border-accent transition-colors"
                >
                  {/* Line 1: Name and Type Badge */}
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="font-semibold text-sm text-primary truncate">
                        {step.config.metadata.name}
                      </span>
                      <span
                        className={`px-2 py-0.5 text-xs rounded-full flex-shrink-0 ${getStepTypeColor(
                          stepType
                        )}`}
                      >
                        {stepType}
                      </span>
                    </div>
                    <ArrowRight
                      size={12}
                      className="text-secondary flex-shrink-0"
                    />
                  </div>

                  {/* Line 2: Description and Metadata */}
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      {step.config.metadata.description ? (
                        <p className="text-xs text-secondary truncate">
                          {step.config.metadata.description}
                        </p>
                      ) : (
                        <p className="text-xs text-secondary">
                          {step.config.input_type_name} →{" "}
                          {step.config.output_type_name}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 ml-2">
                      {hasTimeout && (
                        <Tooltip
                          title={`Timeout: ${step.config.metadata.timeout_seconds}s`}
                        >
                          <Clock size={10} className="text-secondary" />
                        </Tooltip>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
