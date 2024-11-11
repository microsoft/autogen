import React from "react";
import { ThreadState } from "./types";
import { AgentMessageConfig, Message } from "../../../types/datamodel";
import { RenderMessage } from "./rendermessage";
import {
  StopCircle,
  User,
  Network,
  MessageSquare,
  Loader2,
  CheckCircle,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { LoadingIndicator } from "../../shared/atoms";

const landing = require("../../../../images/landing/welcome.svg");

interface MessageListProps {
  messages: Message[];
  threadMessages: Record<string, ThreadState>;
  setThreadMessages: React.Dispatch<
    React.SetStateAction<Record<string, ThreadState>>
  >;
  onRetry: (content: string) => void;
  onCancel: (runId: string) => void;
  loading?: boolean;
}

interface MessagePair {
  userMessage: Message;
  botMessage: Message;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  threadMessages,
  setThreadMessages,
  onRetry,
  onCancel,
  loading = false,
}) => {
  const messagePairs = React.useMemo(() => {
    const pairs: MessagePair[] = [];
    for (let i = 0; i < messages.length; i += 2) {
      if (messages[i] && messages[i + 1]) {
        pairs.push({
          userMessage: messages[i],
          botMessage: messages[i + 1],
        });
      }
    }
    return pairs;
  }, [messages]);

  // Create a ref map to store refs for each thread container
  const threadContainerRefs = React.useRef<
    Record<string, HTMLDivElement | null>
  >({});

  // Effect to handle scrolling when thread messages update
  React.useEffect(() => {
    Object.entries(threadMessages).forEach(([runId, thread]) => {
      if (thread.isExpanded && threadContainerRefs.current[runId]) {
        const container = threadContainerRefs.current[runId];
        if (container) {
          container.scrollTo({
            top: container.scrollHeight,
            behavior: "smooth",
          });
        }
      }
    });
  }, [threadMessages]); // This will trigger when any thread messages update

  const toggleThread = (runId: string) => {
    setThreadMessages((prev) => ({
      ...prev,
      [runId]: {
        ...prev[runId],
        isExpanded: !prev[runId]?.isExpanded,
      },
    }));
  };

  const calculateThreadTokens = (messages: AgentMessageConfig[]) => {
    return messages.reduce((total, msg) => {
      if (!msg.models_usage) return total;
      return (
        total +
        (msg.models_usage.prompt_tokens || 0) +
        (msg.models_usage.completion_tokens || 0)
      );
    }, 0);
  };

  const getStatusIcon = (status: ThreadState["status"]) => {
    switch (status) {
      case "streaming":
        return (
          <div className="inline-block mr-1">
            <Loader2
              size={20}
              className="inline-block mr-1 text-accent animate-spin"
            />{" "}
            Processing ...
          </div>
        );

      case "complete":
        return (
          <CheckCircle size={20} className="inline-block mr-1 text-accent" />
        );
      case "error":
        return (
          <AlertTriangle size={20} className="inline-block mr-1 text-red-500" />
        );
      case "cancelled":
        return (
          <StopCircle size={20} className="inline-block mr-1 text-red-500" />
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6 p-4 h-full">
      {messagePairs.map(({ userMessage, botMessage }, pairIndex) => {
        const isLast = pairIndex === messagePairs.length - 1;
        const thread = threadMessages[botMessage.run_id];
        const hasThread = thread && thread.messages.length > 0;
        const isStreaming = thread?.status === "streaming";

        return (
          <div key={`pair-${botMessage.run_id}`} className="space-y-6">
            {/* User message - first */}
            <div className="flex flex-col items-end">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-primary">User</span>
                <div className="p-1.5 rounded bg-secondary text-accent">
                  <User size={20} />
                </div>
              </div>
              <div className="w-[90%]">
                <RenderMessage message={userMessage.config} isLast={false} />
              </div>
            </div>

            {/* Team response - second */}
            <div className="flex flex-col items-start">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 rounded bg-secondary text-primary">
                  <Network size={20} />
                </div>
                <span className="text-sm font-medium text-primary">
                  Agent Team
                </span>
              </div>

              {/* Main response container */}
              <div className="w-[90%]">
                <div className="p-4 bg-secondary border border-secondary rounded-lg">
                  <div className="text-primary">
                    {getStatusIcon(thread?.status)}{" "}
                    {thread?.finalResult?.content}
                  </div>
                </div>

                {/* Thread section with left border for hierarchy */}
                {hasThread && (
                  <div className="mt-2 pl-4 border-l-2 border-secondary/30">
                    <div className="  flex">
                      <div className="flex-1">
                        <button
                          onClick={() => toggleThread(botMessage.run_id)}
                          className="  flex items-center gap-1 text-sm text-secondary hover:text-primary transition-colors"
                        >
                          <MessageSquare size={16} />
                          <span className="text-accent">
                            {" "}
                            {thread.isExpanded ? "Hide" : "Show"}
                          </span>{" "}
                          agent discussion
                        </button>
                      </div>

                      <div className="text-sm text-secondary">
                        {" "}
                        {calculateThreadTokens(thread.messages)} tokens |{" "}
                        {thread.messages.length} messages
                      </div>
                    </div>
                    {thread.isExpanded && (
                      <div className="mt-2 border border-secondary rounded-lg bg-primary">
                        {/* Status bar - fixed at top */}
                        <div className="sticky top-0 z-10 flex bg-primary rounded-t items-center justify-between p-3 border-b border-secondary bg-secondary/10">
                          <div className="text-sm text-primary">
                            {isStreaming ? (
                              "Agents discussing..."
                            ) : (
                              <>
                                <span className="font-semibold mr-2">
                                  Stop Reason
                                </span>
                                {thread.reason}
                              </>
                            )}
                          </div>
                          {isStreaming && (
                            <button
                              onClick={() => onCancel(botMessage.run_id)}
                              className="flex items-center gap-1 px-3 py-1 rounded bg-red-500 hover:bg-red-600 text-white text-xs font-medium transition-colors"
                            >
                              <StopCircle size={12} />
                              <span>Stop</span>
                            </button>
                          )}
                        </div>

                        {/* Scrollable thread messages - now with ref */}
                        <div
                          ref={(el) =>
                            (threadContainerRefs.current[botMessage.run_id] =
                              el)
                          }
                          className="max-h-[400px] overflow-y-auto scroll"
                        >
                          <div className="p-3 space-y-3">
                            {thread.messages.map((threadMsg, threadIndex) => (
                              <div key={`thread-${threadIndex}`}>
                                <RenderMessage
                                  message={threadMsg}
                                  isLast={
                                    threadIndex === thread.messages.length - 1
                                  }
                                />
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}

      {messages.length === 0 && !loading && (
        <div className="text-center text-secondary h-full  ">
          {/* <img src={landing} alt="No messages" /> */}
          <div>No messages yet</div>
        </div>
      )}
    </div>
  );
};
