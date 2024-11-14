import React from "react";
import { StopCircle, SendHorizontal, Loader2 } from "lucide-react";
import { ThreadState } from "./types";
import { AgentMessageConfig } from "../../../types/datamodel";
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
}

const InputRequestView: React.FC<InputRequestProps> = ({
  prompt,
  onSubmit,
  disabled = false,
}) => {
  const [response, setResponse] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [hasInteracted, setHasInteracted] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    if (!response.trim() || disabled || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmit(response.trim());
      setResponse("");
      setHasInteracted(false); // Reset interaction state after submit
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

  // Auto-focus effect
  React.useEffect(() => {
    if (inputRef.current && !disabled) {
      inputRef.current.focus();
    }
  }, [disabled]);

  return (
    <div className="p-4 bg-accent/10 border border-accent/20 rounded-lg mt-3">
      <div className="text-sm font-medium mb-2 text-primary flex items-center gap-2">
        {prompt}
        {!hasInteracted && (
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-accent"></span>
          </span>
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
          placeholder="Type your response..."
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || isSubmitting || !response.trim()}
          className={`px-4 py-2 rounded bg-accent text-white hover:bg-accent/90 disabled:opacity-50 disabled:hover:bg-accent flex items-center gap-2 transition-all ${
            !hasInteracted && !response.trim() ? "animate-pulse" : ""
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

  const getStatusText = () => {
    if (isStreaming) return "Agents working ";
    if (isAwaitingInput) return "Waiting for your input";
    if (thread.reason)
      return (
        <>
          <span className="font-semibold mr-2">Stop Reason:</span>
          {thread.reason}
        </>
      );
    return null;
  };

  return (
    <div className="mt-2 border border-secondary rounded bg-primary">
      <div className="sticky top-0 z-10 flex bg-primary rounded-t items-center justify-between p-3 border-b border-secondary bg-secondary/10">
        <div className="text-sm text-primary">
          {isStreaming || isAwaitingInput ? (
            <>
              <span className="inline-block mr-2">{getStatusText()}</span>
              <LoadingDots size={8} />
            </>
          ) : (
            getStatusText()
          )}
        </div>
        {isStreaming && (
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
              disabled={!isAwaitingInput}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ThreadView;
