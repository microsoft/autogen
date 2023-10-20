import { ClipboardIcon } from "@heroicons/react/24/outline";
import { message } from "antd";
import React from "react";
import SyntaxHighlighter from "react-syntax-highlighter";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";

// import "./codeblock.css";

interface ICodeProps {
  code: string;
  language: string;
  title?: string;
  showLineNumbers?: boolean;
  className?: string | undefined;
  wrapLines?: boolean;
  maxWidth?: string;
  maxHeight?: string;
  minHeight?: string;
}

export const CodeBlock = ({
  code,
  language = "python",
  showLineNumbers = false,
  className = " ",
  wrapLines = false,
  maxHeight = "400px",
  minHeight = "auto",
}: ICodeProps) => {
  const codeString = code;

  const [showCopied, setShowCopied] = React.useState(false);
  return (
    <div className="relative">
      <div className="  rounded absolute right-5 top-4 z-10 ">
        <div className="relative border border-transparent w-full h-full">
          <div
            style={{ zIndex: -1 }}
            className="w-full absolute top-0 h-full bg-gray-900 hover:bg-opacity-0 duration-300 bg-opacity-50 rounded"
          ></div>
          <div className="   ">
            {showCopied && (
              <div className="inline-block px-2 pl-3 text-white">
                {" "}
                🎉 Copied!{" "}
              </div>
            )}
            <ClipboardIcon
              role={"button"}
              onClick={() => {
                navigator.clipboard.writeText(codeString);
                // message.success("Code copied to clipboard");
                setShowCopied(true);
                setTimeout(() => {
                  setShowCopied(false);
                }, 6000);
              }}
              className="m-2  inline-block duration-300 text-white hover:text-accent w-5 h-5"
            />
          </div>
        </div>
      </div>
      <div
        id="codeDivBox"
        className={`rounded w-full overflow-auto overflow-y-scroll   scroll ${className}`}
        style={{ maxHeight: maxHeight, minHeight: minHeight }}
      >
        <SyntaxHighlighter
          id="codeDiv"
          className="rounded-sm h-full break-all"
          language={language}
          showLineNumbers={showLineNumbers}
          style={atomOneDark}
          wrapLines={wrapLines}
          wrapLongLines={wrapLines}
        >
          {codeString}
        </SyntaxHighlighter>
      </div>
    </div>
  );
};
