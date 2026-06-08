import React, { useState } from "react";
import { User, Bot, DraftingCompass, Bug, ChevronDown } from "lucide-react";
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

const RenderMultiModal: React.FC<{
  content: (string | ImageContent)[];
  thumbnail?: boolean;
}> = ({ content, thumbnail = false }) => {
  // Separate text and images
  const texts = content.filter((item) => typeof item === "string") as string[];
  const images = content.filter(
    (item) => typeof item === "object" && item !== null
  ) as ImageContent[];

  // Use the larger of the two for navigation
  const maxLen = Math.max(texts.length, images.length);
  const [current, setCurrent] = useState(0);

  const showPrev = () => setCurrent((c) => Math.max(0, c - 1));
  const showNext = () => setCurrent((c) => Math.min(maxLen - 1, c + 1));

  const currentText = texts[current] ?? texts[0] ?? "";
  const currentImage = images[current] ?? images[0];

  return (
    <div className="flex gap-4 items-stretch relative">
      {/* Text on the left, aligned to top */}
      <div className="flex-1 min-w-0 flex items-start">
        {currentText && (
          <TruncatableText
            content={currentText.slice(0, 500)}
            className="break-all"
          />
        )}
      </div>
      {/* Image on the right */}
      <div className="flex-1 flex justify-center items-center relative">
        {currentImage && (
          <ClickableImage
            src={getImageSource(currentImage)}
            alt={currentImage.alt || "Image"}
            className={`rounded border border-secondary max-h-96 w-auto max-w-full object-contain ${
              thumbnail ? "w-24 h-24" : ""
            }`}
          />
        )}
        {/* Navigation buttons */}
        {maxLen > 1 && (
          <div className="absolute bottom-2 right-2 flex gap-2 z-10">
            <button
              onClick={showPrev}
              disabled={current === 0}
              className="bg-white/80 hover:bg-white text-black rounded-full px-2 py-1 shadow"
              aria-label="Previous"
            >
              ◀
            </button>
            <button
              onClick={showNext}
              disabled={current >= maxLen - 1}
              className="bg-white/80 hover:bg-white text-black rounded-full px-2 py-1 shadow"
              aria-label="Next"
            >
              ▶
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
const RenderToolCall: React.FC<{ content: FunctionCall[] }> = ({ content }) => {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const toggleExpansion = (callId: string) => {
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(callId)) {
        newSet.delete(callId);
      } else {
        newSet.add(callId);
      }
      return newSet;
    });
  };

  return (
    <div className="space-y-1">
      {content.map((call) => {
        const isExpanded = expandedItems.has(call.id);
        return (
          <div
            key={call.id}
            className="border mt-1 border-secondary bg-secondary rounded hover:bg-tertiary transition-colors"
          >
            <button
              onClick={() => toggleExpansion(call.id)}
              className="w-full flex items-center gap-2 p-2 text-left hover:bg-secondary/50 transition-colors"
            >
              <DraftingCompass className="w-4 h-4 text-accent flex-shrink-0" />
              <span className="font-base text-sm">
                Calling {call.name} tool
              </span>
              <div
                className={`ml-auto transition-transform duration-200 ${
                  isExpanded ? "rotate-180" : "rotate-0"
                }`}
              >
                <ChevronDown className="w-4 h-4" />
              </div>
            </button>
            {isExpanded && (
              <div className="border-t border-secondary p-2">
                <TruncatableText
                  content={JSON.stringify(call.arguments, null, 2)}
                  isJson={true}
                  className="text-sm bg-secondary p-2 rounded"
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

const RenderToolResult: React.FC<{ content: FunctionExecutionResult[] }> = ({
  content,
}) => {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const toggleExpansion = (callId: string) => {
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(callId)) {
        newSet.delete(callId);
      } else {
        newSet.add(callId);
      }
      return newSet;
    });
  };

  return (
    <div className="space-y-1">
      {content.map((result) => {
        const isExpanded = expandedItems.has(result.call_id);
        return (
          <div
            key={result.call_id}
            className="border mt-1 border-secondary bg-secondary rounded hover:bg-tertiary transition-colors"
          >
            <button
              onClick={() => toggleExpansion(result.call_id)}
              className="w-full flex items-center gap-2 p-2 text-left hover:bg-secondary/50 transition-colors"
            >
              <DraftingCompass className="w-4 h-4 text-accent flex-shrink-0" />
              <span className="font-medium text-sm">
                Tool result (ID: {result.call_id.slice(-8)})
              </span>
              <div
                className={`ml-auto transition-transform duration-200 ${
                  isExpanded ? "rotate-180" : "rotate-0"
                }`}
              >
                <ChevronDown className="w-4 h-4" />
              </div>
            </button>
            {isExpanded && (
              <div className="border-t border-secondary p-2">
                <TruncatableText
                  content={result.content}
                  className="text-sm bg-secondary p-2 border border-secondary rounded scroll overflow-x-scroll"
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

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

  isNestedMessageContent(content: unknown): content is AgentMessageConfig[] {
    if (!Array.isArray(content)) return false;
    return content.every(
      (item) =>
        typeof item === "object" &&
        item !== null &&
        "source" in item &&
        "content" in item &&
        "type" in item
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

  isMessageArray(
    message: AgentMessageConfig | AgentMessageConfig[]
  ): message is AgentMessageConfig[] {
    return Array.isArray(message);
  },
};

interface MessageProps {
  message: AgentMessageConfig | AgentMessageConfig[];
  isLast?: boolean;
  className?: string;
}

export const RenderNestedMessages: React.FC<{
  content: AgentMessageConfig[];
}> = ({ content }) => (
  <div className="space-y-4">
    {content.map((item, index) => (
      <div
        key={index}
        className={`${
          index > 0 ? "bordper border-secondary rounded   bg-secondary/30" : ""
        }`}
      >
        {typeof item.content === "string" ? (
          <TruncatableText
            content={item.content}
            className={`break-all ${index === 0 ? "text-base" : "text-sm"}`}
          />
        ) : messageUtils.isMultiModalContent(item.content) ? (
          <RenderMultiModal content={item.content} thumbnail />
        ) : (
          <pre className="text-xs whitespace-pre-wrap overflow-x-auto">
            {JSON.stringify(item.content, null, 2)}
          </pre>
        )}
      </div>
    ))}
  </div>
);

export const RenderMessage: React.FC<MessageProps> = ({
  message,
  isLast = false,
  className = "",
}) => {
  if (!message) return null;

  // If message is an array, render the first message or return null
  if (messageUtils.isMessageArray(message)) {
    return message.length > 0 ? (
      <RenderMessage
        message={message[0]}
        isLast={isLast}
        className={className}
      />
    ) : null;
  }

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
            <Bug size={14} />
          ) : (
            <Bot size={14} />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-semibold text-primary truncate flex-1 min-w-0">
              {message.source}
            </span>
            {message.models_usage && (
              <span className="text-xs text-secondary flex-shrink-0">
                Tokens:{" "}
                {(message.models_usage.prompt_tokens || 0) +
                  (message.models_usage.completion_tokens || 0)}
              </span>
            )}
          </div>

          <div className="text-sm text-secondary">
            {messageUtils.isToolCallContent(content) ? (
              <RenderToolCall content={content} />
            ) : messageUtils.isMultiModalContent(content) ? (
              <RenderMultiModal content={content} thumbnail={false} />
            ) : messageUtils.isNestedMessageContent(content) ? (
              <RenderNestedMessages content={content} />
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
        </div>
      </div>
    </div>
  );
};
