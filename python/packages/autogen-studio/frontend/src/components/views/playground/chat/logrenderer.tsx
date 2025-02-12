import React, { useMemo, useState } from "react";
import { Terminal, Maximize2, X } from "lucide-react";
import { TruncatableText } from "../../atoms";
import { Tooltip } from "antd";

interface LLMLogEvent {
  type: "LLMCall";
  messages: {
    content: string;
    role: string;
    name?: string;
  }[];
  response: {
    id: string;
    choices: {
      message: {
        content: string;
        role: string;
      };
    }[];
    usage: {
      completion_tokens: number;
      prompt_tokens: number;
      total_tokens: number;
    };
    model: string;
  };
  prompt_tokens: number;
  completion_tokens: number;
  agent_id: string;
}

interface LLMLogRendererProps {
  content: string;
}

const formatTokens = (tokens: number) => {
  return tokens >= 1000 ? `${(tokens / 1000).toFixed(1)}k` : tokens;
};

const FullLogView = ({
  event,
  onClose,
}: {
  event: LLMLogEvent;
  onClose: () => void;
}) => (
  <div
    className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center transition-opacity duration-300"
    onClick={onClose}
  >
    <div
      className="relative bg-primary w-full h-full md:w-4/5 md:h-4/5 md:rounded-lg p-8 overflow-auto"
      style={{ opacity: 0.95 }}
      onClick={(e) => e.stopPropagation()}
    >
      <Tooltip title="Close">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full bg-black/50 hover:bg-black/70 text-primary transition-colors"
        >
          <X size={24} />
        </button>
      </Tooltip>

      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-4">
          <Terminal size={20} className="text-accent" />
          <h3 className="text-lg font-medium">LLM Call Details</h3>
          <h4 className="text-sm text-secondary">
            {event.agent_id.split("/")[0]} • {event.response.model} •{" "}
            {formatTokens(event.response.usage.total_tokens)} tokens
          </h4>
        </div>

        <div className="space-y-2">
          <h4 className="text-sm font-medium">Messages</h4>
          {event.messages.map((msg, idx) => (
            <div key={idx} className="p-4 bg-tertiary rounded-lg">
              <div className="flex justify-between mb-2">
                <span className="text-xs font-medium uppercase text-secondary">
                  {msg.role} {msg.name && `(${msg.name})`}
                </span>
              </div>
              <TruncatableText
                content={msg.content}
                textThreshold={1000}
                showFullscreen={false}
              />
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <h4 className="text-sm font-medium">Response</h4>
          <div className="p-4 bg-tertiary rounded-lg">
            <TruncatableText
              content={event.response.choices[0]?.message.content}
              textThreshold={1000}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="p-3 bg-tertiary rounded-lg">
            <div className="text-xs text-secondary mb-1">Model</div>
            <div className="font-medium">{event.response.model}</div>
          </div>
          <div className="p-3 bg-tertiary rounded-lg">
            <div className="text-xs text-secondary mb-1">Prompt Tokens</div>
            <div className="font-medium">
              {event.response.usage.prompt_tokens}
            </div>
          </div>
          <div className="p-3 bg-tertiary rounded-lg">
            <div className="text-xs text-secondary mb-1">Completion Tokens</div>
            <div className="font-medium">
              {event.response.usage.completion_tokens}
            </div>
          </div>
          <div className="p-3 bg-tertiary rounded-lg">
            <div className="text-xs text-secondary mb-1">Total Tokens</div>
            <div className="font-medium">
              {event.response.usage.total_tokens}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
);

const LLMLogRenderer: React.FC<LLMLogRendererProps> = ({ content }) => {
  const [showFullLog, setShowFullLog] = useState(false);

  const parsedContent = useMemo(() => {
    try {
      return JSON.parse(content) as LLMLogEvent;
    } catch (e) {
      console.error("Failed to parse LLM log content:", e);
      return null;
    }
  }, [content]);

  if (!parsedContent) {
    return (
      <div className="flex items-center gap-2 text-red-500 p-2 bg-red-500/10 rounded">
        <Terminal size={16} />
        <span>Invalid log format</span>
      </div>
    );
  }

  const { messages, response, agent_id } = parsedContent;
  const agentName = messages[0]?.name || "Agent";
  const totalTokens = response.usage.total_tokens;
  const shortAgentId = agent_id ? `${agent_id.split("/")[0]}` : "";

  return (
    <>
      <div className="flex items-center gap-2 py-2   bg-secondary/20 rounded-lg text-sm text-secondary hover:text-primary transition-colors group">
        <Terminal size={14} className="text-accent" />
        <span className="flex-1">
          {shortAgentId ? `${shortAgentId}` : ""} • {response.model} •{" "}
          {formatTokens(totalTokens)} tokens
        </span>
        <Tooltip title="View details">
          <button
            onClick={() => setShowFullLog(true)}
            className="p-1 mr-1 hover:bg-secondary rounded-md transition-colors"
          >
            <Maximize2 size={14} className="group-hover:text-accent" />
          </button>
        </Tooltip>
      </div>

      {showFullLog && (
        <FullLogView
          event={parsedContent}
          onClose={() => setShowFullLog(false)}
        />
      )}
    </>
  );
};

export default LLMLogRenderer;
