import React, { useEffect, useRef } from "react";
import { ChevronDown, ChevronRight, RotateCcw, User, Bot } from "lucide-react";
import { ThreadView } from "./thread";
import { MessageListProps } from "./types";

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  threadMessages,
  setThreadMessages,
  onRetry,
  onCancel,
  loading,
}) => {
  const messageListRef = useRef<HTMLDivElement>(null);

  const messagePairs = React.useMemo(() => {
    const pairs = [];
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

  const toggleThread = (runId: string) => {
    setThreadMessages((prev) => ({
      ...prev,
      [runId]: {
        ...prev[runId],
        isExpanded: !prev[runId].isExpanded,
      },
    }));
  };

  return (
    <div
      ref={messageListRef}
      className="flex flex-col space-y-4 p-4 overflow-y-hidden overflow-x-hidden"
    >
      {messagePairs.map(({ userMessage, botMessage }, idx) => {
        const thread = threadMessages[botMessage.run_id];
        const isStreaming = thread?.status === "streaming";
        const isError = thread?.status === "error";

        return (
          <div key={idx} className="space-y-2 text-primary">
            {/* User Message */}
            <div className="flex items-start gap-2  ]">
              <div className="p-1.5 rounded bg-light text-accent">
                <User size={24} />
              </div>
              <div className="flex-1">
                <div className="p-2 bg-accent rounded text-white">
                  {userMessage.config.content}
                </div>
                {userMessage.config.models_usage && (
                  <div className="text-xs text-secondary mt-1">
                    Tokens:{" "}
                    {userMessage.config.models_usage.prompt_tokens +
                      userMessage.config.models_usage.completion_tokens}
                  </div>
                )}
              </div>
            </div>

            {/* Bot Response */}
            <div className="flex items-start gap-2 ml-auto ">
              <div className="flex-1">
                <div className="p-2 bg-secondary rounded text-primary">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 text-sm">
                      {isStreaming ? (
                        <>Processing...</>
                      ) : (
                        <>
                          {" "}
                          {thread?.finalResult?.content}
                          <div className="mt-2 mb-2 text-sm text-secondary">
                            {thread?.reason}
                          </div>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      {isError && (
                        <button
                          onClick={() => onRetry(userMessage.config.content)}
                          className="p-1 text-secondary hover:text-primary transition-colors"
                        >
                          <RotateCcw size={14} />
                        </button>
                      )}
                      {thread && thread.messages?.length > 0 && (
                        <button
                          onClick={() => toggleThread(botMessage.run_id)}
                          className="p-1 text-secondary hover:text-primary transition-colors"
                        >
                          {thread.isExpanded ? (
                            <ChevronDown size={14} />
                          ) : (
                            <ChevronRight size={14} />
                          )}
                        </button>
                      )}
                    </div>
                  </div>

                  {botMessage.config.models_usage && (
                    <div className="text-sm text-secondary -mt-4">
                      {botMessage.config.models_usage.prompt_tokens +
                        botMessage.config.models_usage.completion_tokens}{" "}
                      tokens | {thread.messages.length} messages
                    </div>
                  )}
                  {/* Thread View */}
                  {thread && thread.isExpanded && (
                    <ThreadView
                      messages={thread.messages}
                      status={thread.status}
                      onCancel={onCancel}
                      runId={botMessage.run_id}
                    />
                  )}
                </div>
              </div>
              <div className="p-1.5 rounded bg-light text-primary">
                <Bot size={24} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
