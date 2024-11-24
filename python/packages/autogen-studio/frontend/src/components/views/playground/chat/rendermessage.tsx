import React from "react";
import { User, Bot } from "lucide-react";
import {
  AgentMessageConfig,
  FunctionCall,
  FunctionExecutionResult,
  ImageContent,
} from "../../../types/datamodel";

export const messageUtils = {
  isToolCallContent(content: unknown): content is FunctionCall[] {
    if (!Array.isArray(content)) return false;
    return content.every(
      (item) =>
        typeof item === "object" &&
        item !== null &&
        "id" in item &&
        "arguments" in item &&
        "name" in item
    );
  },

  isMultiModalContent(content: unknown): content is (string | ImageContent)[] {
    if (!Array.isArray(content)) return false;
    return content.every(
      (item) =>
        typeof item === "string" ||
        (typeof item === "object" && item !== null && "url" in item)
    );
  },

  isFunctionExecutionResult(
    content: unknown
  ): content is FunctionExecutionResult[] {
    if (!Array.isArray(content)) return false;
    return content.every(
      (item) =>
        typeof item === "object" &&
        item !== null &&
        "call_id" in item &&
        "content" in item
    );
  },

  isUser(source: string): boolean {
    return source === "user";
  },
};

interface MessageProps {
  message: AgentMessageConfig;
  isLast?: boolean;
  className?: string;
}

const RenderToolCall: React.FC<{ content: FunctionCall[] }> = ({ content }) => (
  <div className="space-y-2">
    {content.map((call) => (
      <div key={call.id} className="border rounded p-2">
        <div className="font-medium">Function: {call.name}</div>
        <pre className="text-sm mt-1 bg-secondary p-2 rounded">
          {JSON.stringify(JSON.parse(call.arguments), null, 2)}
        </pre>
      </div>
    ))}
  </div>
);

const RenderMultiModal: React.FC<{ content: (string | ImageContent)[] }> = ({
  content,
}) => (
  <div className="space-y-2">
    {content.map((item, index) =>
      typeof item === "string" ? (
        <p key={index}>{item}</p>
      ) : (
        <img
          key={index}
          src={item.url}
          alt={item.alt || ""}
          className="max-w-full h-auto"
        />
      )
    )}
  </div>
);

const RenderToolResult: React.FC<{ content: FunctionExecutionResult[] }> = ({
  content,
}) => (
  <div className="space-y-2">
    {content.map((result) => (
      <div key={result.call_id} className="  rounded p-2">
        <div className="font-medium">Result ID: {result.call_id}</div>
        <pre className="text-sm mt-1 bg-secondary p-2 border rounded">
          {result.content}
        </pre>
      </div>
    ))}
  </div>
);

export const RenderMessage: React.FC<MessageProps> = ({
  message,
  isLast = false,
  className = "",
}) => {
  const isUser = messageUtils.isUser(message.source);
  const content = message.content;

  return (
    <div className={`relative group ${!isLast ? "mb-2" : ""} ${className}`}>
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
          ${isUser ? "text-accent" : "text-primary"}
        `}
        >
          {isUser ? <User size={14} /> : <Bot size={14} />}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-primary">
              {message.source}
            </span>
          </div>

          <div className="text-sm text-secondary">
            {messageUtils.isToolCallContent(content) ? (
              <RenderToolCall content={content} />
            ) : messageUtils.isMultiModalContent(content) ? (
              <RenderMultiModal content={content} />
            ) : messageUtils.isFunctionExecutionResult(content) ? (
              <RenderToolResult content={content} />
            ) : (
              <div className="whitespace-pre-wrap">{content}</div>
            )}
          </div>

          {message.models_usage && (
            <div className="text-xs text-secondary mt-1">
              Tokens:{" "}
              {(message.models_usage.prompt_tokens || 0) +
                (message.models_usage.completion_tokens || 0)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
