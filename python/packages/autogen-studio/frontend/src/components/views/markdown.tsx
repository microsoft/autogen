import React, { ReactNode } from "react";
import Markdown from "react-markdown";

interface MarkdownViewProps {
  content: string;
  className?: string;
}

export const MarkdownView: React.FC<MarkdownViewProps> = ({
  content,
  className = "",
}) => {
  return (
    <div className={`text-sm w-full text-primary rounded   ${className}`}>
      <Markdown>{content}</Markdown>
    </div>
  );
};
