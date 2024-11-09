import Markdown from "react-markdown";
import React from "react";

interface MarkdownViewProps {
  children: string;
  className?: string;
}

export const MarkdownView: React.FC<MarkdownViewProps> = ({
  children,
  className = "",
}) => {
  return (
    <div
      className={`text-sm w-full prose dark:prose-invert text-primary rounded p-2 ${className}`}
    >
      <Markdown>{children}</Markdown>
    </div>
  );
};
