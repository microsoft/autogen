import React from "react";
import { StopCircle } from "lucide-react";
import { ThreadState } from "./types";
import { AgentMessageConfig } from "../../../types/datamodel";
import { RenderMessage } from "./rendermessage";

interface ThreadViewProps {
  thread: ThreadState;
  isStreaming: boolean;
  runId: string;
  onCancel: (runId: string) => void;
  threadContainerRef: (el: HTMLDivElement | null) => void;
}

const ThreadView: React.FC<ThreadViewProps> = ({
  thread,
  isStreaming,
  runId,
  onCancel,
  threadContainerRef,
}) => {
  return (
    <div className="mt-2 border border-secondary rounded bg-primary">
      {/* Status bar - fixed at top */}
      <div className="sticky top-0 z-10 flex bg-primary rounded-t items-center justify-between p-3 border-b border-secondary bg-secondary/10">
        <div className="text-sm text-primary">
          {isStreaming ? (
            "Agents discussing..."
          ) : (
            <>
              <span className="font-semibold mr-2">Stop Reason</span>
              {thread.reason}
            </>
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

      {/* Thread messages and flow visualization in tabs */}
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
        </div>
      </div>
    </div>
  );
};

export default ThreadView;
