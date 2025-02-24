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
  disabled?: boolean;
}

export default function ChatInput({
  onSubmit,
  loading,
  error,
  disabled = false,
}: ChatInputProps) {
  const textAreaRef = React.useRef<HTMLTextAreaElement>(null);
  const [previousLoading, setPreviousLoading] = React.useState(loading);
  const [text, setText] = React.useState("");

  const textAreaDefaultHeight = "64px";
  const isInputDisabled = disabled || loading;

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
    if (textAreaRef.current?.value && !isInputDisabled) {
      const query = textAreaRef.current.value;
      onSubmit(query);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="mt-2 w-full">
      <div
        className={`mt-2 rounded shadow-sm flex mb-1 ${
          isInputDisabled ? "opacity-50" : ""
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
            className={`flex items-center w-full resize-none text-gray-600 rounded border border-accent bg-white p-2 pl-5 pr-16 ${
              isInputDisabled ? "cursor-not-allowed" : ""
            }`}
            style={{
              maxHeight: "120px",
              overflowY: "auto",
              minHeight: "50px",
            }}
            placeholder="Type your message here..."
            disabled={isInputDisabled}
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isInputDisabled}
            className={`absolute right-3 bottom-2 bg-accent transition duration-300 rounded flex justify-center items-center w-11 h-9 ${
              isInputDisabled ? "cursor-not-allowed" : "hover:brightness-75"
            }`}
          >
            {loading ? (
              <Cog6ToothIcon className="text-white animate-spin rounded-full h-6 w-6" />
            ) : (
              <PaperAirplaneIcon className="h-6 w-6 text-white" />
            )}
          </button>
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
