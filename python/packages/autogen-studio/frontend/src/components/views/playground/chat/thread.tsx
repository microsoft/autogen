import React, { useEffect, useRef } from "react";
import {
  CheckCircle,
  AlertCircle,
  Loader2,
  User,
  Bot,
  StopCircle,
} from "lucide-react";
import { Tooltip } from "antd";
import { MessageConfig } from "../../../types/datamodel";
import { ThreadState } from "./types";

interface ThreadViewProps {
  messages: MessageConfig[];
  status: ThreadState["status"];
  reason?: string; // Add reason
  onCancel: (runId: string) => void;
  runId: string;
}

interface StatusBannerProps {
  status: ThreadState["status"];
  reason?: string; // Add reason prop
  onCancel: (runId: string) => void;
  runId: string;
}

const StatusBanner = ({
  status,
  reason,
  onCancel,
  runId,
}: StatusBannerProps) => {
  // Define variants FIRST
  const variants = {
    streaming: {
      wrapper: "bg-secondary border border-secondary",
      text: "text-primary",
      icon: "text-accent",
    },
    complete: {
      wrapper: "bg-secondary p-2",
      text: "text-accent",
      icon: " ",
    },
    error: {
      wrapper: "bg-secondary border border-secondary",
      text: "text-primary",
      icon: "text-red-500",
    },
    cancelled: {
      wrapper: "bg-secondary border border-secondary",
      text: "text-red-500",
      icon: "text-red-500",
    },
  } as const;

  const content = {
    streaming: {
      icon: <Loader2 className="animate-spin" size={16} />,
      text: "Processing",
      showStop: true,
    },
    complete: {
      icon: <CheckCircle size={16} />,
      text: reason || "Completed",
      showStop: false,
    },
    error: {
      icon: <AlertCircle size={16} />,
      text: reason || "Error occurred",
      showStop: false,
    },
    cancelled: {
      icon: <StopCircle size={16} />,
      text: reason || "Cancelled",
      showStop: false,
    },
  } as const;

  // THEN check valid status and use variants
  const validStatus = status && status in variants ? status : "error";
  const currentVariant = variants[validStatus];
  const currentContent = content[validStatus];

  // Rest of component remains the same...
  return (
    <div
      className={`flex items-center mt-2 justify-between p-2 rounded transition-all duration-200 ${currentVariant.wrapper}`}
    >
      <div className={`flex items-center gap-2 ${currentVariant.text}`}>
        <span className={currentVariant.icon}>{currentContent.icon}</span>
        <span className="text-sm font-medium">{currentContent.text}</span>
        {currentContent.showStop && (
          <Tooltip title="Stop processing" placement="right">
            <button
              onClick={() => onCancel(runId)}
              className="ml-2 flex items-center gap-1 px-2 py-1 rounded bg-red-500 hover:bg-red-600 text-white text-xs font-medium transition-colors duration-200"
            >
              <StopCircle size={12} />
              <span>Stop</span>
            </button>
          </Tooltip>
        )}
      </div>
    </div>
  );
};

const Message = ({ msg, isLast }: { msg: MessageConfig; isLast: boolean }) => {
  const isUser = msg.source === "user";

  return (
    <div className={`relative group ${!isLast ? "mb-2" : ""}`}>
      <div
        className={`
        flex items-start gap-2 p-2 rounded
        ${isUser ? "bg-secondary" : "bg-tertiary"}
        border border-secondary
        transition-all duration-200
      `}
      >
        <div
          className={`
          p-1.5 rounded bg-light 
          ${isUser ? " text-accent" : "text-primary"}
        `}
        >
          {isUser ? <User size={14} /> : <Bot size={14} />}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-primary">
              {msg.source}
            </span>
          </div>

          <div className="text-sm text-secondary whitespace-pre-wrap">
            {msg.content || ""}
          </div>

          {msg.models_usage && (
            <div className="text-xs text-secondary mt-1">
              Tokens:{" "}
              {(msg.models_usage.prompt_tokens || 0) +
                (msg.models_usage.completion_tokens || 0)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const ThreadView: React.FC<ThreadViewProps> = ({
  messages = [],
  status,
  reason,
  onCancel,
  runId,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current && status === "streaming") {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, status]);

  // const displayMessages = messages.filter(
  //   (msg): msg is MessageConfig =>
  //     msg && typeof msg.content === "string" && msg.content !== "TERMINATE"
  // );
  const displayMessages = messages;

  return (
    <div>
      <div className="space-y-2">
        <StatusBanner
          status={status}
          reason={reason}
          onCancel={onCancel}
          runId={runId}
        />

        <div
          ref={scrollRef}
          style={{ maxHeight: "300px" }}
          className="overflow-y-scroll scroll p-2 space-y-2 bg-primary rounded border border-secondary"
        >
          {displayMessages.map((msg, idx) => (
            <Message
              key={idx}
              msg={msg}
              isLast={idx === displayMessages.length - 1}
            />
          ))}

          {displayMessages.length === 0 && status !== "streaming" && (
            <div className="text-sm text-secondary text-center p-2">
              No messages to display
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ThreadView;
