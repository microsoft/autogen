"use client";

import {
  PaperAirplaneIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import * as React from "react";
import { IStatus } from "../../../types/app";

interface ChatInputProps {
  onSubmit: (text: string) => void;
  loading: boolean;
  error: IStatus | null;
}
export default function ChatInput({
  onSubmit,
  loading,
  error,
}: ChatInputProps) {
  const textAreaRef = React.useRef<HTMLTextAreaElement>(null);
  const [previousLoading, setPreviousLoading] = React.useState(loading);
  const [text, setText] = React.useState("");

  const textAreaDefaultHeight = "64px";

  // Handle textarea auto-resize
  React.useEffect(() => {
    if (textAreaRef.current) {
      textAreaRef.current.style.height = textAreaDefaultHeight;
      const scrollHeight = textAreaRef.current.scrollHeight;
      textAreaRef.current.style.height = `${scrollHeight}px`;
    }
  }, [text]);

  // Clear input when loading changes from true to false (meaning the response is complete)
  React.useEffect(() => {
    if (previousLoading && !loading && !error) {
      resetInput();
    }
    setPreviousLoading(loading);
  }, [loading, error, previousLoading]);

  const resetInput = () => {
    if (textAreaRef.current) {
      textAreaRef.current.value = "";
      textAreaRef.current.style.height = textAreaDefaultHeight;
      setText("");
    }
  };

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(event.target.value);
  };

  const handleSubmit = () => {
    if (textAreaRef.current?.value && !loading) {
      const query = textAreaRef.current.value;
      onSubmit(query);
      // Don't reset immediately - wait for response to complete
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="mt-2   w-full">
      <div
        className={`mt-2 rounded  shadow-sm flex mb-1 ${
          loading ? "opacity-50 pointer-events-none" : ""
        }`}
      >
        <form
          className="flex-1 relative"
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
        >
          <textarea
            id="queryInput"
            name="queryInput"
            ref={textAreaRef}
            defaultValue={"what is the height of the eiffel tower"}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            className="flex items-center w-full resize-none text-gray-600 rounded  border border-accent bg-white p-2 pl-5 pr-16"
            style={{
              maxHeight: "120px",
              overflowY: "auto",
              minHeight: "50px",
            }}
            placeholder="Type your message here..."
            disabled={loading}
          />
          <div
            role="button"
            onClick={handleSubmit}
            style={{ width: "45px", height: "35px" }}
            className="absolute right-3 bottom-2 bg-accent hover:brightness-75 transition duration-300 rounded cursor-pointer flex justify-center items-center"
          >
            {!loading ? (
              <div className="inline-block">
                <PaperAirplaneIcon className="h-6 w-6 text-white" />
              </div>
            ) : (
              <div className="inline-block">
                <Cog6ToothIcon className="text-white animate-spin rounded-full h-6 w-6" />
              </div>
            )}
          </div>
        </form>
      </div>

      {error && !error.status && (
        <div className="p-2 border rounded mt-4 text-orange-500 text-sm">
          <ExclamationTriangleIcon className="h-5 text-orange-500 inline-block mr-2" />
          {error.message}
        </div>
      )}
    </div>
  );
}
