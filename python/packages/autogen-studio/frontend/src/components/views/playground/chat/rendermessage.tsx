import React, { useState, memo } from "react";
import {
  User,
  Bot,
  Maximize2,
  Minimize2,
  DraftingCompass,
  Brain,
} from "lucide-react";
import {
  AgentMessageConfig,
  FunctionCall,
  FunctionExecutionResult,
  ImageContent,
} from "../../../types/datamodel";
import { ClickableImage, TruncatableText } from "../../atoms";
import LLMLogRenderer from "./logrenderer";

const TEXT_THRESHOLD = 400;
const JSON_THRESHOLD = 800;

// Helper function to get image source from either format
const getImageSource = (item: ImageContent): string => {
  if (item.url) {
    return item.url;
  }
  if (item.data) {
    // Assume PNG if no type specified - we can enhance this later if needed
    return `data:image/png;base64,${item.data}`;
  }
  // Fallback placeholder if neither url nor data is present
  return "/api/placeholder/400/320";
};

const RenderMultiModal: React.FC<{ content: (string | ImageContent)[] }> = ({
  content,
}) => (
  <div className="space-y-2">
    {content.map((item, index) =>
      typeof item === "string" ? (
        <TruncatableText key={index} content={item} className="break-all" />
      ) : (
        <ClickableImage
          key={index}
          src={getImageSource(item)}
          alt={item.alt || "Image"}
          className="w-full h-auto rounded border border-secondary"
        />
      )
    )}
  </div>
);
const RenderToolCall: React.FC<{ content: FunctionCall[] }> = ({ content }) => (
  <div className="space-y-2">
    {content.map((call) => (
      <div
        key={call.id}
        className="relative pl-3 border border-secondary rounded p-2"
      >
        <div className="absolute top-0 -left-0.5 w-1 bg-secondary h-full rounded"></div>
        <div className="font-medium">
          <DraftingCompass className="w-4 h-4 text-accent inline-block mr-1.5 -mt-0.5" />{" "}
          Calling {call.name} tool with arguments
        </div>
        <TruncatableText
          content={JSON.stringify(JSON.parse(call.arguments), null, 2)}
          isJson={true}
          className="text-sm mt-1 bg-secondary p-2 rounded"
        />
      </div>
    ))}
  </div>
);

const RenderToolResult: React.FC<{ content: FunctionExecutionResult[] }> = ({
  content,
}) => (
  <div className="space-y-2">
    {content.map((result) => (
      <div
        key={result.call_id}
        className="rounded p-2 pl-3 relative border border-secondary"
      >
        <div className="absolute top-0 -left-0.5 w-1 bg-secondary h-full rounded"></div>
        <div className="font-medium">
          <DraftingCompass className="w-4 text-accent h-4 inline-block mr-1.5 -mt-0.5" />{" "}
          Tool Result
        </div>
        <TruncatableText
          content={result.content}
          className="text-sm mt-1 bg-secondary p-2 border border-secondary rounded scroll overflow-x-scroll"
        />
      </div>
    ))}
  </div>
);

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
        (typeof item === "object" &&
          item !== null &&
          ("url" in item || "data" in item))
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

export const RenderMessage: React.FC<MessageProps> = ({
  message,
  isLast = false,
  className = "",
}) => {
  if (!message) return null;
  const isUser = messageUtils.isUser(message.source);
  const content = message.content;
  const isLLMEventMessage = message.source === "llm_call_event";

  return (
    <div
      className={`relative group ${!isLast ? "mb-2" : ""} ${className} ${
        isLLMEventMessage ? "border-accent" : ""
      }`}
    >
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
          {isUser ? (
            <User size={14} />
          ) : message.source == "llm_call_event" ? (
            <Brain size={14} />
          ) : (
            <Bot size={14} />
          )}
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
            ) : message.source === "llm_call_event" ? (
              <LLMLogRenderer content={String(content)} />
            ) : (
              <TruncatableText
                content={String(content)}
                className="break-all"
              />
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
