"use client";

import {
  AcademicCapIcon,
  ArrowPathIcon,
  UserIcon,
} from "@heroicons/react/24/outline";
import { Collapse } from "antd";
import * as React from "react";
import Markdown from "react-markdown";
import { Message } from "../../../types/datamodel";

export interface MessageListProps {
  messages: Message[];
  runLogs: Record<string, Message[]>;
  onRetry: (text: string) => void;
  loading: boolean;
}

export default function MessageList({
  messages,
  runLogs,
  onRetry,
  loading,
}: MessageListProps) {
  const messageBoxRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    scrollToBottom();
  }, [messages, runLogs]);

  const scrollToBottom = () => {
    messageBoxRef.current?.scroll({
      top: messageBoxRef.current.scrollHeight,
      behavior: "smooth",
    });
  };

  const renderLogs = (sessionId: string) => {
    const logs = runLogs[sessionId] || [];
    return logs.map((log: Message, index: number) => {
      const isEven = index % 2 === 0;
      return (
        <div
          key={`log-${sessionId}-${index}`}
          className={`text-sm border rounded p-2 mb-2 ${
            isEven ? "bg-primary" : "bg-secondary"
          }`}
        >
          <div className="flex justify-between items-center text-xs text-gray-500 mb-1">
            <div>
              <span className="font-semibold">{log.type}</span>
              {log.source && (
                <span className="text-accent ml-2">[{log.source}]</span>
              )}
            </div>
            <div>{new Date(log.timestamp).toLocaleTimeString()}</div>
          </div>
          <div className="mt-1">
            <Markdown>{log.content}</Markdown>
          </div>
        </div>
      );
    });
  };

  return (
    <div
      ref={messageBoxRef}
      // style={{ height: "calc(100% - 100px)" }}
      className="flex overflow-auto flex-col rounded scroll pr-2"
    >
      <div className="flex-1   mt-4"></div>
      <div className="ml-2">
        {messages.map((message, i) => {
          const isUser = message.sender === "user";
          const css = isUser ? "bg-accent text-white" : "bg-light";

          return (
            <div
              key={`message-${i}`}
              className={`align-right ${
                isUser ? "text-right" : "mb-2 border-b pb-2"
              }`}
            >
              <div className={`${isUser ? "" : "w-full"} inline-flex gap-2`}>
                <div>
                  {!isUser && (
                    <span className="inline-block text-accent bg-primary pb-2 ml-1">
                      <AcademicCapIcon className="inline-block h-6" />
                    </span>
                  )}
                </div>
                <div
                  className={`inline-block ${
                    isUser ? "" : "w-full"
                  } p-2 rounded`}
                >
                  {isUser ? (
                    <>
                      <div className={`${css} p-2 rounded`}>{message.text}</div>
                      <span
                        role="button"
                        onClick={() => onRetry(message.text)}
                        className="mt-1 text-sm inline-block"
                      >
                        <ArrowPathIcon className="h-4 w-4 mr-1 inline-block" />
                        Retry
                      </span>
                    </>
                  ) : (
                    <>
                      {message.finalResponse && (
                        <div className="mb-4">
                          <Markdown>{message.finalResponse}</Markdown>
                        </div>
                      )}

                      {message.sessionId && runLogs[message.sessionId] && (
                        <Collapse
                          defaultActiveKey={
                            message.status === "processing" ? ["1"] : []
                          }
                          size="small"
                          className="text-xs mt-2"
                          items={[
                            {
                              key: "1",
                              label: (
                                <div>
                                  <span className="pr-2">
                                    {message.status === "processing"
                                      ? "Processing..."
                                      : "View Processing Steps"}
                                  </span>
                                </div>
                              ),
                              children: (
                                <div>{renderLogs(message.sessionId)}</div>
                              ),
                            },
                          ]}
                        />
                      )}
                    </>
                  )}
                </div>
                {isUser && <UserIcon className="inline-block h-6" />}
              </div>
            </div>
          );
        })}
      </div>

      <div className="ml-2 h-6 mb-4 mt-2">
        {loading && (
          <div className="inline-flex gap-2">
            <span className="rounded-full bg-accent h-2 w-2 inline-block"></span>
            <span className="animate-bounce rounded-full bg-accent h-3 w-3 inline-block"></span>
            <span className="rounded-full bg-accent h-2 w-2 inline-block"></span>
          </div>
        )}
      </div>
    </div>
  );
}
