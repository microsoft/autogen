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
  Play,
  Pause,
  RotateCcw,
} from "lucide-react";
import { Run, Message, TeamConfig, Component } from "../../../types/datamodel";
import AgentFlow from "./agentflow/agentflow";
import { RenderMessage } from "./rendermessage";
import InputRequestView from "./inputrequest";
import { Tooltip, Dropdown, MenuProps } from "antd";
import { getRelativeTimeString, LoadingDots } from "../../atoms";
import { useSettingsStore } from "../../settings/store";

interface RunViewProps {
  run: Run;
  teamConfig?: Component<TeamConfig>;
  onInputResponse?: (response: string) => void;
  onCancel?: () => void;
  isFirstRun?: boolean;
  streamingContent?: {
    runId: number;
    content: string;
    source: string;
  } | null;
}

interface StreamingMessageProps {
  content: string;
  source: string;
}

const StreamingMessage: React.FC<StreamingMessageProps> = ({
  content,
  source,
}) => {
  const [showCursor, setShowCursor] = useState(true);

  // Blinking cursor effect
  useEffect(() => {
    const interval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 530);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-start gap-2 p-2 rounded bg-tertiary border border-secondary transition-all duration-200 mb-6">
      <div className="p-1.5 rounded bg-light text-primary">
        <Bot size={14} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-primary">{source}</span>
        </div>
        <div className="text-sm text-secondary break-all">
          {content}
          {showCursor && (
            <span className="inline-block w-2 h-4 ml-1 bg-accent/70 animate-pulse" />
          )}
        </div>
      </div>
    </div>
  );
};

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
  streamingContent,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const threadContainerRef = useRef<HTMLDivElement | null>(null);
  const isActive = run.status === "active" || run.status === "awaiting_input";

  const { uiSettings } = useSettingsStore();
  const [isFlowVisible, setIsFlowVisible] = useState(
    uiSettings.show_agent_flow_by_default ?? true
  );

  // Replay state
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayMessageIndex, setReplayMessageIndex] = useState(0);
  const [originalRun, setOriginalRun] = useState<Run | null>(null);
  const replayIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [replaySpeed, setReplaySpeed] = useState(1); // 1x speed by default

  // Create a run object for display (either original or replaying version)
  const displayRun = useMemo(() => {
    if (!isReplaying || !originalRun) return run;

    return {
      ...originalRun,
      messages: originalRun.messages.slice(0, replayMessageIndex + 1),
      status:
        replayMessageIndex < originalRun.messages.length - 1
          ? ("active" as const)
          : originalRun.status,
    };
  }, [run, isReplaying, originalRun, replayMessageIndex]);

  const visibleMessages = useMemo(() => {
    if (uiSettings.show_llm_call_events) {
      return displayRun.messages;
    }
    return displayRun.messages.filter(
      (msg) => msg.config.source !== "llm_call_event"
    );
  }, [displayRun.messages, uiSettings.show_llm_call_events]);

  // Replay functions
  const startReplay = () => {
    if (
      run.status !== "complete" &&
      run.status !== "error" &&
      run.status !== "stopped"
    )
      return;

    setOriginalRun(run);
    setReplayMessageIndex(0);
    setIsReplaying(true);
    setIsExpanded(true); // Ensure the messages are visible

    // Start the replay interval with current speed
    const intervalTime = 800 / replaySpeed; // Base time 800ms divided by speed multiplier
    replayIntervalRef.current = setInterval(() => {
      setReplayMessageIndex((prev) => {
        if (prev >= run.messages.length - 1) {
          setIsReplaying(false);
          if (replayIntervalRef.current) {
            clearInterval(replayIntervalRef.current);
            replayIntervalRef.current = null;
          }
          return prev;
        }
        return prev + 1;
      });
    }, intervalTime);
  };

  const pauseReplay = () => {
    if (replayIntervalRef.current) {
      clearInterval(replayIntervalRef.current);
      replayIntervalRef.current = null;
    }
    setIsReplaying(false);
  };

  const resetReplay = () => {
    if (replayIntervalRef.current) {
      clearInterval(replayIntervalRef.current);
      replayIntervalRef.current = null;
    }
    setIsReplaying(false);
    setReplayMessageIndex(0);
    setOriginalRun(null);
  };

  const changeReplaySpeed = (newSpeed: number) => {
    setReplaySpeed(newSpeed);

    // If currently replaying, restart with new speed
    if (isReplaying && replayIntervalRef.current) {
      clearInterval(replayIntervalRef.current);
      const intervalTime = 800 / newSpeed;
      replayIntervalRef.current = setInterval(() => {
        setReplayMessageIndex((prev) => {
          if (
            prev >=
            (originalRun?.messages.length || run.messages.length) - 1
          ) {
            setIsReplaying(false);
            if (replayIntervalRef.current) {
              clearInterval(replayIntervalRef.current);
              replayIntervalRef.current = null;
            }
            return prev;
          }
          return prev + 1;
        });
      }, intervalTime);
    }
  };

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (replayIntervalRef.current) {
        clearInterval(replayIntervalRef.current);
      }
    };
  }, []);

  // Determine if replay is available
  const canReplay =
    (run.status === "complete" ||
      run.status === "error" ||
      run.status === "stopped") &&
    run.messages.length > 0;

  console.log("Run task", run.task);

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
  }, [displayRun.messages, streamingContent]);
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
    // If we're replaying, show replay status instead
    if (isReplaying && originalRun) {
      return (
        <div className="inline-block mr-1">
          <Play size={20} className="inline-block mr-1 text-accent" />
          <span className="inline-block mr-2 ml-1">Replaying</span>
          <LoadingDots size={8} />
        </div>
      );
    }

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

  const lastResultMessage =
    displayRun.team_result?.task_result?.messages.slice(-1)[0];
  const lastMessage = getLastMeaningfulMessage(visibleMessages);

  return (
    <div className="space-y-6  mr-2 ">
      {/* Run Header */}
      <div
        className={`${
          isFirstRun ? "mb-2" : "mt-4"
        } mb-4 pb-2 pt-2 border-b border-dashed border-secondary`}
      >
        <div id="run-header" className="flex items-center justify-between">
          <div className="text-xs text-secondary">
            <Tooltip
              title={
                <div className="text-xs">
                  <div>ID: {run.id}</div>
                  <div>
                    Created: {new Date(run.created_at).toLocaleString()}
                  </div>
                  <div>Status: {run.status}</div>
                </div>
              }
            >
              <span className="cursor-help">
                Run ...{run.id} | {getRelativeTimeString(run?.created_at || "")}{" "}
              </span>
            </Tooltip>
            {!isFirstRun && (
              <>
                {" "}
                |{" "}
                <TriangleAlertIcon className="w-4 h-4 -mt-1 inline-block mr-1 ml-1" />
                Note: Each run does not share data with previous runs in the
                same session yet.
              </>
            )}
          </div>

          {/* Replay Controls */}
          {canReplay && (
            <div className="flex items-center gap-2">
              {!isReplaying && !originalRun && (
                <div className="flex items-center gap-0">
                  <button
                    onClick={startReplay}
                    className="p-1 px-2 rounded-l hover:bg-secondary transition-colors text-secondary hover:text-primary"
                  >
                    <Play className="inline-block" size={16} />
                    <span className="inline-block text-xs text-secondary ml-1">
                      Replay Run ({replaySpeed}x)
                    </span>
                  </button>
                  <Dropdown
                    menu={{
                      items: [
                        {
                          key: "0.1",
                          label: "0.1x",
                          onClick: () => changeReplaySpeed(0.1),
                        },
                        {
                          key: "0.5",
                          label: "0.5x",
                          onClick: () => changeReplaySpeed(0.5),
                        },
                        {
                          key: "1",
                          label: "1x",
                          onClick: () => changeReplaySpeed(1),
                        },
                        {
                          key: "2",
                          label: "2x",
                          onClick: () => changeReplaySpeed(2),
                        },
                        {
                          key: "5",
                          label: "5x",
                          onClick: () => changeReplaySpeed(5),
                        },
                      ],
                      selectedKeys: [replaySpeed.toString()],
                    }}
                    trigger={["click"]}
                  >
                    <button className="p-1 px-1 rounded-r hover:bg-secondary transition-colors text-secondary hover:text-primary border-l border-secondary">
                      <ChevronDown className="inline-block" size={12} />
                    </button>
                  </Dropdown>
                </div>
              )}

              {isReplaying && (
                <div className="flex items-center gap-0">
                  <button
                    onClick={pauseReplay}
                    className="p-1 px-2 rounded-l hover:bg-secondary transition-colors text-accent hover:text-primary"
                  >
                    <Pause className="inline-block" size={16} />
                    <span className="inline-block text-xs text-accent ml-1">
                      Pause Replay ({replaySpeed}x)
                    </span>
                  </button>

                  <Dropdown
                    menu={{
                      items: [
                        {
                          key: "0.1",
                          label: "0.1x",
                          onClick: () => changeReplaySpeed(0.1),
                        },
                        {
                          key: "0.5",
                          label: "0.5x",
                          onClick: () => changeReplaySpeed(0.5),
                        },
                        {
                          key: "1",
                          label: "1x",
                          onClick: () => changeReplaySpeed(1),
                        },
                        {
                          key: "2",
                          label: "2x",
                          onClick: () => changeReplaySpeed(2),
                        },
                        {
                          key: "5",
                          label: "5x",
                          onClick: () => changeReplaySpeed(5),
                        },
                      ],
                      selectedKeys: [replaySpeed.toString()],
                    }}
                    trigger={["click"]}
                  >
                    <button className="p-1 px-1 rounded-r hover:bg-secondary transition-colors text-secondary hover:text-primary border-l border-secondary">
                      <ChevronDown className="inline-block" size={12} />
                    </button>
                  </Dropdown>
                </div>
              )}

              {(isReplaying || originalRun) && (
                <button
                  onClick={resetReplay}
                  className="p-1 px-2 rounded hover:bg-secondary transition-colors text-secondary hover:text-primary"
                >
                  <RotateCcw className="inline-block" size={16} />{" "}
                  <span className="inline-block text-xs text-secondary">
                    Reset Replay
                  </span>
                </button>
              )}

              {(isReplaying || originalRun) && (
                <div className="text-xs text-secondary">
                  {replayMessageIndex + 1}/
                  {originalRun?.messages.length || run.messages.length}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* User Message */}
      <div className="flex flex-col items-end w-full">
        <div className="w-full">
          <RenderMessage message={displayRun.task} isLast={false} />
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
              <div className="text-primary">
                {getStatusIcon(displayRun.status)}
              </div>

              {/* Cancel Button - More prominent placement */}
              {isActive && onCancel && !isReplaying && (
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
            {displayRun.status !== "awaiting_input" &&
              displayRun.status !== "active" && (
                <div className="text-sm break-all">
                  <div className="text-xs bg-tertiary mb-1 text-secondary border-secondary -mt-2 bdorder rounded p-2">
                    Stop reason:{" "}
                    {displayRun.team_result?.task_result?.stop_reason}
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
                      {streamingContent &&
                        streamingContent.runId === run.id &&
                        !isReplaying && (
                          <div className="mr-2 mb-10">
                            <StreamingMessage
                              content={streamingContent.content}
                              source={streamingContent.source}
                            />
                          </div>
                        )}

                      {/* Input Request UI */}
                      {displayRun.status === "awaiting_input" &&
                        onInputResponse &&
                        !isReplaying && (
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
                          {getStatusIcon(displayRun.status)}
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
                              ...displayRun,
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
