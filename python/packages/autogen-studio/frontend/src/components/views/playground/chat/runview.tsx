import React, { useState, useRef, useEffect, useMemo } from "react";
import {
  StopCircle,
  MessageSquare,
  Loader2,
  CheckCircle,
  AlertTriangle,
  TriangleAlertIcon,
  ChevronDown,
  ChevronUp,
  Bot,
  PanelRightClose,
  PanelRightOpen,
} from "lucide-react";
import { Run, Message, TeamConfig, Component } from "../../../types/datamodel";
import AgentFlow from "./agentflow/agentflow";
import { RenderMessage } from "./rendermessage";
import InputRequestView from "./inputrequest";
import { Tooltip } from "antd";
import { getRelativeTimeString, LoadingDots } from "../../atoms";
import { useSettingsStore } from "../../settings/store";

interface RunViewProps {
  run: Run;
  teamConfig?: Component<TeamConfig>;
  onInputResponse?: (response: string) => void;
  onCancel?: () => void;
  isFirstRun?: boolean;
}

export const getAgentMessages = (messages: Message[]): Message[] => {
  return messages.filter((msg) => msg.config.source !== "llm_call_event");
};

export const getLastMeaningfulMessage = (
  messages: Message[]
): Message | undefined => {
  return messages
    .filter((msg) => msg.config.source !== "llm_call_event")
    .slice(-1)[0];
};

// Type guard for message arrays
export const isAgentMessage = (message: Message): boolean => {
  return message.config.source !== "llm_call_event";
};

const RunView: React.FC<RunViewProps> = ({
  run,
  onInputResponse,
  onCancel,
  teamConfig,
  isFirstRun = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const threadContainerRef = useRef<HTMLDivElement | null>(null);
  const isActive = run.status === "active" || run.status === "awaiting_input";
  const [isFlowVisible, setIsFlowVisible] = useState(true);

  const showLLMEvents = useSettingsStore(
    (state) => state.playground.showLLMEvents
  );
  console.log("showLLMEvents", showLLMEvents);

  const visibleMessages = useMemo(() => {
    if (showLLMEvents) {
      return run.messages;
    }
    return run.messages.filter((msg) => msg.config.source !== "llm_call_event");
  }, [run.messages, showLLMEvents]);

  // Replace existing scroll effect with this simpler one
  useEffect(() => {
    setTimeout(() => {
      if (threadContainerRef.current) {
        threadContainerRef.current.scrollTo({
          top: threadContainerRef.current.scrollHeight,
          behavior: "smooth",
        });
      }
    }, 450);
  }, [run.messages]); // Only depend on messages changing
  // console.log("run", run);
  const calculateThreadTokens = (messages: Message[]) => {
    // console.log("messages", messages);
    return messages.reduce((total, msg) => {
      if (!msg.config?.models_usage) return total;
      return (
        total +
        (msg.config.models_usage.prompt_tokens || 0) +
        (msg.config.models_usage.completion_tokens || 0)
      );
    }, 0);
  };

  const getStatusIcon = (status: Run["status"]) => {
    switch (status) {
      case "active":
        return (
          <div className="inline-block mr-1">
            <Loader2
              size={20}
              className="inline-block mr-1 text-accent animate-spin"
            />
            <span className="inline-block mr-2 ml-1 ">Processing</span>
            <LoadingDots size={8} />
          </div>
        );
      case "awaiting_input":
        return (
          <div className="text-sm mb-2">
            <MessageSquare
              size={20}
              className="inline-block mr-2 text-accent"
            />
            <span className="inline-block mr-2">Waiting for your input </span>
            <LoadingDots size={8} />
          </div>
        );
      case "complete":
        return (
          <div className="text-sm mb-2">
            <CheckCircle size={20} className="inline-block mr-2 text-accent" />
            Task completed
          </div>
        );
      case "error":
        return (
          <div className="text-sm mb-2">
            <AlertTriangle
              size={20}
              className="inline-block mr-2 text-red-500"
            />
            {run.error_message || "An error occurred"}
          </div>
        );
      case "stopped":
        return (
          <div className="text-sm mb-2">
            <StopCircle size={20} className="inline-block mr-2 text-red-500" />
            Task was stopped
          </div>
        );
      default:
        return null;
    }
  };

  const lastResultMessage = run.team_result?.task_result.messages.slice(-1)[0];
  const lastMessage = getLastMeaningfulMessage(visibleMessages);

  return (
    <div className="space-y-6  mr-2 ">
      {/* Run Header */}
      <div
        className={`${
          isFirstRun ? "mb-2" : "mt-4"
        } mb-4 pb-2 pt-2 border-b border-dashed border-secondary`}
      >
        <div className="text-xs text-secondary">
          <Tooltip
            title={
              <div className="text-xs">
                <div>ID: {run.id}</div>
                <div>Created: {new Date(run.created_at).toLocaleString()}</div>
                <div>Status: {run.status}</div>
              </div>
            }
          >
            <span className="cursor-help">
              Run ...{run.id.slice(-6)} |{" "}
              {getRelativeTimeString(run?.created_at || "")}{" "}
            </span>
          </Tooltip>
          {!isFirstRun && (
            <>
              {" "}
              |{" "}
              <TriangleAlertIcon className="w-4 h-4 -mt-1 inline-block mr-1 ml-1" />
              Note: Each run does not share data with previous runs in the same
              session yet.
            </>
          )}
        </div>
      </div>

      {/* User Message */}
      <div className="flex flex-col items-end w-full">
        <div className="w-full">
          <RenderMessage message={run.task} isLast={false} />
        </div>
      </div>

      {/* Team Response */}
      <div className="flex flex-col items-start">
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded bg-secondary text-primary">
            <Bot size={20} />
          </div>
          <span className="text-sm font-medium text-primary">Agent Team</span>
        </div>

        <div className="   w-full">
          {/* Main Response Container */}
          <div className="p-4 bg-secondary border border-secondary rounded">
            <div className="flex justify-between items-start mb-2">
              <div className="text-primary">{getStatusIcon(run.status)}</div>

              {/* Cancel Button - More prominent placement */}
              {isActive && onCancel && (
                <button
                  onClick={onCancel}
                  className="px-4 text-sm py-2 bg-red-500 hover:bg-red-600 text-white rounded-md transition-colors flex items-center gap-2"
                >
                  <StopCircle size={16} />
                  Cancel Run
                </button>
              )}
            </div>

            {/* Final Response */}
            {run.status !== "awaiting_input" && run.status !== "active" && (
              <div className="text-sm break-all">
                <div className="text-xs bg-tertiary mb-1 text-secondary border-secondary -mt-2 bdorder rounded p-2">
                  Stop reason: {run.team_result?.task_result?.stop_reason}
                </div>

                {lastMessage ? (
                  <RenderMessage message={lastMessage.config} isLast={true} />
                ) : (
                  <>
                    {lastResultMessage && (
                      <RenderMessage message={lastResultMessage} />
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Thread Section */}
          <div className="">
            {visibleMessages.length > 0 && (
              <div className="mt-2 pl-4 border-secondary rounded-b border-l-2 border-secondary/30">
                <div className="flex pt-2">
                  <div className="flex-1">
                    <button
                      onClick={() => setIsExpanded(!isExpanded)}
                      className="flex items-center gap-1 text-sm text-secondary hover:text-primary transition-colors"
                    >
                      <MessageSquare size={16} /> Agent steps [
                      <span className="text-accent text-xs">
                        {isExpanded ? (
                          <span>
                            <ChevronUp
                              size={16}
                              className="inline-block mr-1"
                            />
                            Hide
                          </span>
                        ) : (
                          <span>
                            {" "}
                            <ChevronDown
                              size={16}
                              className="inline-block mr-1"
                            />{" "}
                            Show more
                          </span>
                        )}
                      </span>{" "}
                      ]
                    </button>
                  </div>

                  <div className="text-sm text-secondary">
                    {calculateThreadTokens(visibleMessages)} tokens |{" "}
                    {visibleMessages.length} messages
                  </div>
                </div>

                {isExpanded && (
                  <div className="flex relative flex-row gap-4">
                    {!isFlowVisible && (
                      <div className="z-50 absolute right-2 top-2 bg-tertiary rounded p-2 hover:opacity-100 opacity-80">
                        <Tooltip title="Show message flow graph">
                          <button
                            onClick={() => setIsFlowVisible(true)}
                            className=" p-1 rounded-md bg-tertiary  hover:bg-secondary  transition-colors"
                          >
                            <PanelRightOpen strokeWidth={1.5} size={22} />
                          </button>
                        </Tooltip>
                      </div>
                    )}
                    {/* Messages Thread */}
                    <div
                      ref={threadContainerRef}
                      className="flex-1 mt-2 overflow-y-auto max-h-[400px] scroll-smooth scroll pb-2 relative"
                    >
                      <div id="scroll-gradient" className="scroll-gradient h-8">
                        {" "}
                        <span className="  inline-block h-6"></span>{" "}
                      </div>
                      {visibleMessages.map((msg, idx) => (
                        <div
                          key={"message_id" + idx + run.id}
                          className="  mr-2"
                        >
                          <RenderMessage
                            message={msg.config}
                            isLast={idx === visibleMessages.length - 1}
                          />
                        </div>
                      ))}

                      {/* Input Request UI */}
                      {run.status === "awaiting_input" && onInputResponse && (
                        <div className="mt-4 mr-2">
                          <InputRequestView
                            prompt="Type your response..."
                            onSubmit={onInputResponse}
                          />
                        </div>
                      )}
                      <div className="text-primary mt-2">
                        <div className="w-4 h-4 inline-block  border-secondary rounded-bl-lg border-l-2 border-b-2"></div>{" "}
                        <div className="inline-block ">
                          {getStatusIcon(run.status)}
                        </div>
                      </div>
                    </div>

                    {/* Agent Flow Visualization */}
                    {isFlowVisible && (
                      <div className="bg-tertiary flex-1 rounded mt-2 relative">
                        <div className="z-10 absolute left-2 top-2 p-2 hover:opacity-100 opacity-80">
                          <Tooltip title="Hide message flow">
                            <button
                              onClick={() => setIsFlowVisible(false)}
                              className=" p-1 rounded-md bg-tertiary hover:bg-secondary transition-colors"
                            >
                              <PanelRightClose strokeWidth={1.5} size={22} />
                            </button>
                          </Tooltip>
                        </div>
                        {teamConfig && (
                          <AgentFlow
                            teamConfig={teamConfig}
                            run={{
                              ...run,
                              messages: getAgentMessages(visibleMessages),
                            }}
                          />
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RunView;
