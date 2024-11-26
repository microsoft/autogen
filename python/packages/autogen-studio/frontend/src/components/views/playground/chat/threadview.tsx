import React, { useEffect, useRef } from "react";
import {
  StopCircle,
  SendHorizontal,
  Loader2,
  Clock,
  AlertTriangle,
  MessageSquare,
  CheckCircle,
} from "lucide-react";
import { ThreadState, TIMEOUT_CONFIG } from "./types";
import { RenderMessage } from "./rendermessage";
import LoadingDots from "../../shared/atoms";

interface ThreadViewProps {
  thread: ThreadState;
  isStreaming: boolean;
  runId: string;
  onCancel: (runId: string) => void;
  onInputResponse: (runId: string, response: string) => void;
  threadContainerRef: (el: HTMLDivElement | null) => void;
}

interface InputRequestProps {
  prompt: string;
  onSubmit: (response: string) => void;
  disabled?: boolean;
  onTimeout?: () => void;
}

const InputRequestView: React.FC<InputRequestProps> = ({
  prompt,
  onSubmit,
  disabled = false,
  onTimeout,
}) => {
  const [response, setResponse] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [timeLeft, setTimeLeft] = React.useState(TIMEOUT_CONFIG.DURATION_SEC);
  const [hasInteracted, setHasInteracted] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const timerRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!disabled) {
      timerRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            onTimeout?.();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [disabled, onTimeout]);

  // Auto-focus effect
  React.useEffect(() => {
    if (inputRef.current && !disabled) {
      inputRef.current.focus();
    }
  }, [disabled]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const handleSubmit = async () => {
    if (!response.trim() || disabled || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmit(response.trim());
      setResponse("");
      setHasInteracted(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setResponse(e.target.value);
    if (!hasInteracted) {
      setHasInteracted(true);
    }
  };

  const getTimeoutWarningClass = () => {
    if (timeLeft < TIMEOUT_CONFIG.WARNING_THRESHOLD_SEC) {
      return "text-red-500 font-bold animate-pulse";
    }
    return "text-accent";
  };

  return (
    <div
      className={`p-4 bg-accent/10 border border-accent/20 rounded-lg mt-3 ${
        disabled ? "opacity-50" : ""
      }`}
    >
      <div className="flex justify-between items-center mb-2">
        <div className="text-sm font-medium text-primary flex items-center gap-2">
          {prompt}
          {!hasInteracted && !disabled && (
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-accent"></span>
            </span>
          )}
        </div>
        {!disabled && (
          <div className="flex items-center gap-2 text-sm">
            <Clock size={14} className="text-accent" />
            <span className={getTimeoutWarningClass()}>
              {formatTime(timeLeft)}
            </span>
          </div>
        )}
      </div>
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={response}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          disabled={disabled || isSubmitting}
          className="flex-1 px-3 py-2 rounded bg-background border border-secondary focus:border-accent focus:ring-1 focus:ring-accent outline-none disabled:opacity-50"
          placeholder={
            disabled
              ? "Input timeout - please restart the conversation"
              : "Type your response..."
          }
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || isSubmitting || !response.trim()}
          className={`px-4 py-2 rounded bg-accent text-white hover:bg-accent/90 disabled:opacity-50 disabled:hover:bg-accent flex items-center gap-2 transition-all ${
            !hasInteracted && !disabled && !response.trim()
              ? "animate-pulse"
              : ""
          }`}
        >
          {isSubmitting ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <SendHorizontal size={16} />
          )}
          <span>Submit</span>
        </button>
      </div>
    </div>
  );
};

const ThreadView: React.FC<ThreadViewProps> = ({
  thread,
  isStreaming,
  runId,
  onCancel,
  onInputResponse,
  threadContainerRef,
}) => {
  const isAwaitingInput = thread.status === "awaiting_input";
  const isTimedOut = thread.status === "timeout";

  const getStatusIcon = () => {
    switch (thread.status) {
      case "streaming":
        return <Loader2 size={16} className="animate-spin text-accent" />;
      case "awaiting_input":
        return <MessageSquare size={16} className="text-accent" />;
      case "complete":
        return <CheckCircle size={16} className="text-accent" />;
      case "error":
        return <AlertTriangle size={16} className="text-red-500" />;
      case "timeout":
        return <Clock size={16} className="text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    if (isStreaming) {
      return (
        <>
          <span className="inline-block mr-2">Agents working</span>
          <LoadingDots size={8} />
        </>
      );
    }
    if (isAwaitingInput) return "Waiting for your input";
    if (isTimedOut) return TIMEOUT_CONFIG.DEFAULT_MESSAGE;
    if (thread.reason)
      return (
        <>
          <span className="font-semibold mr-2">Stop Reason:</span>
          {thread.reason}
        </>
      );
    return null;
  };

  const handleTimeout = () => {
    if (thread.inputRequest) {
      onInputResponse(runId, "TIMEOUT");
    }
  };

  return (
    <div className="mt-2 border border-secondary rounded bg-primary">
      <div className="sticky top-0 z-10 flex bg-primary rounded-t items-center justify-between p-3 border-b border-secondary bg-secondary/10">
        <div className="text-sm text-primary flex items-center gap-2">
          {getStatusIcon()}
          {getStatusText()}
        </div>
        {(isStreaming || isAwaitingInput) && (
          <button
            onClick={() => onCancel(runId)}
            className="flex items-center gap-1 px-3 py-1 rounded bg-red-500 hover:bg-red-600 text-white text-xs font-medium transition-colors"
          >
            <StopCircle size={12} />
            <span>Stop</span>
          </button>
        )}
      </div>

      <div
        ref={threadContainerRef}
        className="max-h-[400px] overflow-y-auto scroll"
      >
        <div className="p-3 space-y-3">
          {thread.messages.map((threadMsg, threadIndex) => (
            <div key={`thread-${threadIndex}`}>
              <RenderMessage
                message={threadMsg}
                isLast={threadIndex === thread.messages.length - 1}
              />
            </div>
          ))}

          {thread.inputRequest && (
            <InputRequestView
              prompt={thread.inputRequest.prompt}
              onSubmit={(response) => onInputResponse(runId, response)}
              disabled={!isAwaitingInput || isTimedOut}
              onTimeout={handleTimeout}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ThreadView;
