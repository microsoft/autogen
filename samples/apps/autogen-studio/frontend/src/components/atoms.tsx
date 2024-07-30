import {
  ChevronDownIcon,
  ChevronUpIcon,
  Cog8ToothIcon,
  XMarkIcon,
  ClipboardIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import React, { ReactNode, useEffect, useRef, useState } from "react";
import Icon from "./icons";
import { Modal, Table, Tooltip, theme } from "antd";
import Editor from "@monaco-editor/react";
import Papa from "papaparse";
import remarkGfm from "remark-gfm";
import ReactMarkdown from "react-markdown";
import { atomDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { truncateText } from "./utils";

const { useToken } = theme;
interface CodeProps {
  node?: any;
  inline?: any;
  className?: any;
  children?: React.ReactNode;
}

interface IProps {
  children?: ReactNode;
  title?: string | ReactNode;
  subtitle?: string | ReactNode;
  count?: number;
  active?: boolean;
  cursor?: string;
  icon?: ReactNode;
  padding?: string;
  className?: string;
  open?: boolean;
  hoverable?: boolean;
  onClick?: () => void;
  loading?: boolean;
}

export const SectionHeader = ({
  children,
  title,
  subtitle,
  count,
  icon,
}: IProps) => {
  return (
    <div className="mb-4">
      <h1 className="text-primary text-2xl">
        {/* {count !== null && <span className="text-accent mr-1">{count}</span>} */}
        {icon && <>{icon}</>}
        {title}
        {count !== null && (
          <span className="text-accent mr-1 ml-2 text-xs">{count}</span>
        )}
      </h1>
      {subtitle && <span className="inline-block">{subtitle}</span>}
      {children}
    </div>
  );
};

export const IconButton = ({
  onClick,
  icon,
  className,
  active = false,
}: IProps) => {
  return (
    <span
      role={"button"}
      onClick={onClick}
      className={`inline-block mr-2 hover:text-accent transition duration-300 ${className} ${
        active ? "border-accent border rounded text-accent" : ""
      }`}
    >
      {icon}
    </span>
  );
};

export const LaunchButton = ({
  children,
  onClick,
  className = "p-3 px-5 ",
}: any) => {
  return (
    <button
      role={"button"}
      className={` focus:ring ring-accent  ring-l-none  rounded  cursor-pointer hover:brightness-110 bg-accent transition duration-500    text-white ${className} `}
      onClick={onClick}
    >
      {children}
    </button>
  );
};

export const SecondaryButton = ({ children, onClick, className }: any) => {
  return (
    <button
      role={"button"}
      className={` ${className}   focus:ring ring-accent  p-2 px-5 rounded  cursor-pointer hover:brightness-90 bg-secondary transition duration-500    text-primary`}
      onClick={onClick}
    >
      {children}
    </button>
  );
};

export const Card = ({
  children,
  title,
  subtitle,
  hoverable = true,
  active,
  cursor = "cursor-pointer",
  className = "p-3",
  onClick,
}: IProps) => {
  let border = active
    ? "border-accent"
    : "border-secondary hover:border-accent ";
  border = hoverable ? border : "border-secondary";

  return (
    <button
      tabIndex={0}
      onClick={onClick}
      role={"button"}
      className={`${border} border-2 bg-secondary  group ${className} w-full text-left rounded ${cursor} transition duration-300`}
    >
      <div className="mt- text-sm text-secondary  h-full break-words">
        {title && (
          <div className="text-accent rounded font-semibold  text-xs pb-1">
            {title}
          </div>
        )}
        <div>{subtitle}</div>
        {children}
      </div>
    </button>
  );
};

export const CollapseBox = ({
  title,
  subtitle,
  children,
  className = " p-3",
  open = false,
}: IProps) => {
  const [isOpen, setIsOpen] = React.useState<boolean>(open);
  const chevronClass = "h-4 cursor-pointer inline-block mr-1";
  return (
    <div
      onMouseDown={(e) => {
        if (e.detail > 1) {
          e.preventDefault();
        }
      }}
      className="bordper border-secondary rounded"
    >
      <div
        onClick={() => {
          setIsOpen(!isOpen);
        }}
        className={`cursor-pointer bg-secondary p-2 rounded ${
          isOpen ? "rounded-b-none " : " "
        }"}`}
      >
        {isOpen && <ChevronUpIcon className={chevronClass} />}
        {!isOpen && <ChevronDownIcon className={chevronClass} />}

        <span className=" inline-block -mt-2 mb-2 text-xs">
          {" "}
          {/* {isOpen ? "hide" : "show"} section |  */}
          {title}
        </span>
      </div>

      {isOpen && (
        <div className={`${className} bg-tertiary  rounded rounded-t-none`}>
          {children}
        </div>
      )}
    </div>
  );
};

export const HighLight = ({ children }: IProps) => {
  return <span className="border-b border-accent">{children}</span>;
};

export const LoadBox = ({
  subtitle,
  className = "my-2 text-accent ",
}: IProps) => {
  return (
    <div className={`${className} `}>
      {" "}
      <span className="mr-2 ">
        {" "}
        <Icon size={5} icon="loading" />
      </span>{" "}
      {subtitle}
    </div>
  );
};

export const LoadingBar = ({ children }: IProps) => {
  return (
    <>
      <div className="rounded bg-secondary  p-3">
        <span className="inline-block h-6 w-6 relative mr-2">
          <Cog8ToothIcon className="animate-ping text-accent absolute inline-flex h-full w-full rounded-ful  opacity-75" />
          <Cog8ToothIcon className="relative text-accent animate-spin  inline-flex rounded-full h-6 w-6" />
        </span>
        {children}
      </div>
      <div className="relative">
        <div className="loadbar rounded-b"></div>
      </div>
    </>
  );
};

export const MessageBox = ({ title, children, className }: IProps) => {
  const messageBox = useRef<HTMLDivElement>(null);

  const closeMessage = () => {
    if (messageBox.current) {
      messageBox.current.remove();
    }
  };

  return (
    <div
      ref={messageBox}
      className={`${className} p-3  rounded  bg-secondary transition duration-1000 ease-in-out  overflow-hidden`}
    >
      {" "}
      <div className="flex gap-2 mb-2">
        <div className="flex-1">
          {/* <span className="mr-2 text-accent">
            <InformationCircleIcon className="h-6 w-6 inline-block" />
          </span>{" "} */}
          <span className="font-semibold text-primary text-base">{title}</span>
        </div>
        <div>
          <span
            onClick={() => {
              closeMessage();
            }}
            className=" border border-secondary bg-secondary brightness-125 hover:brightness-100 cursor-pointer transition duration-200   inline-block px-1 pb-1 rounded text-primary"
          >
            <XMarkIcon className="h-4 w-4 inline-block" />
          </span>
        </div>
      </div>
      {children}
    </div>
  );
};

export const GroupView = ({
  children,
  title,
  className = "text-primary bg-primary ",
}: any) => {
  return (
    <div className={`rounded mt-4  border-secondary   ${className}`}>
      <div className="mt-4 p-2 rounded border relative">
        <div className={`absolute  -top-3 inline-block ${className}`}>
          {title}
        </div>
        <div className="mt-2"> {children}</div>
      </div>
    </div>
  );
};

export const ExpandView = ({
  children,
  icon = null,
  className = "",
  title = "Detail View",
}: any) => {
  const [isOpen, setIsOpen] = React.useState(false);
  let windowAspect = 1;
  if (typeof window !== "undefined") {
    windowAspect = window.innerWidth / window.innerHeight;
  }
  const minImageWidth = 400;
  return (
    <div
      style={{
        minHeight: "100px",
      }}
      className={`h-full    rounded mb-6  border-secondary ${className}`}
    >
      <div
        role="button"
        onClick={() => {
          setIsOpen(true);
        }}
        className="text-xs mb-2 h-full w-full break-words"
      >
        {icon ? icon : children}
      </div>
      {isOpen && (
        <Modal
          title={title}
          width={800}
          open={isOpen}
          onCancel={() => setIsOpen(false)}
          footer={null}
        >
          {/* <ResizableBox
            // handle={<span className="text-accent">resize</span>}
            lockAspectRatio={false}
            handle={
              <div className="absolute right-0 bottom-0 cursor-se-resize  font-semibold boprder p-3 bg-secondary">
                <ArrowDownRightIcon className="h-4 w-4 inline-block" />
              </div>
            }
            width={800}
            height={minImageWidth * windowAspect}
            minConstraints={[minImageWidth, minImageWidth * windowAspect]}
            maxConstraints={[900, 900 * windowAspect]}
            className="overflow-auto w-full rounded select-none "
          > */}
          {children}
          {/* </ResizableBox> */}
        </Modal>
      )}
    </div>
  );
};

export const LoadingOverlay = ({ children, loading }: IProps) => {
  return (
    <>
      {loading && (
        <>
          <div
            className="absolute inset-0 bg-secondary flex  pointer-events-none"
            style={{ opacity: 0.5 }}
          >
            {/* Overlay background */}
          </div>
          <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ pointerEvents: "none" }}
          >
            {/* Center BounceLoader without inheriting the opacity */}
            <BounceLoader />
          </div>
        </>
      )}
      <div className="relative">{children}</div>
    </>
  );
};

export const MarkdownView = ({
  data,
  className = "",
  showCode = true,
}: {
  data: string;
  className?: string;
  showCode?: boolean;
}) => {
  function processString(inputString: string): string {
    inputString = inputString.replace(/\n/g, "  \n");
    const markdownPattern = /```markdown\s+([\s\S]*?)\s+```/g;
    return inputString?.replace(markdownPattern, (match, content) => content);
  }
  const [showCopied, setShowCopied] = React.useState(false);

  const CodeView = ({ props, children, language }: any) => {
    const [codeVisible, setCodeVisible] = React.useState(showCode);
    return (
      <div>
        <div className=" flex  ">
          <div
            role="button"
            onClick={() => {
              setCodeVisible(!codeVisible);
            }}
            className="  flex-1 mr-4  "
          >
            {!codeVisible && (
              <div className=" text-white hover:text-accent duration-300">
                <ChevronDownIcon className="inline-block  w-5 h-5" />
                <span className="text-xs"> show</span>
              </div>
            )}

            {codeVisible && (
              <div className=" text-white hover:text-accent duration-300">
                {" "}
                <ChevronUpIcon className="inline-block  w-5 h-5" />
                <span className="text-xs"> hide</span>
              </div>
            )}
          </div>
          {/* <div className="flex-1"></div> */}
          <div>
            {showCopied && (
              <div className="inline-block text-sm       text-white">
                {" "}
                🎉 Copied!{" "}
              </div>
            )}
            <ClipboardIcon
              role={"button"}
              onClick={() => {
                navigator.clipboard.writeText(data);
                // message.success("Code copied to clipboard");
                setShowCopied(true);
                setTimeout(() => {
                  setShowCopied(false);
                }, 3000);
              }}
              className=" inline-block duration-300 text-white hover:text-accent w-5 h-5"
            />
          </div>
        </div>
        {codeVisible && (
          <SyntaxHighlighter
            {...props}
            style={atomDark}
            language={language}
            className="rounded w-full"
            PreTag="div"
            wrapLongLines={true}
          >
            {String(children).replace(/\n$/, "")}
          </SyntaxHighlighter>
        )}
      </div>
    );
  };

  return (
    <div
      className={` w-full   chatbox prose dark:prose-invert text-primary rounded   ${className}`}
    >
      <ReactMarkdown
        className="   w-full"
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }: CodeProps) {
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : "text";
            return !inline && match ? (
              <CodeView props={props} children={children} language={language} />
            ) : (
              <code {...props} className={className}>
                {children}
              </code>
            );
          },
        }}
      >
        {processString(data)}
      </ReactMarkdown>
    </div>
  );
};

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
          style={atomDark}
          wrapLines={wrapLines}
          wrapLongLines={wrapLines}
        >
          {codeString}
        </SyntaxHighlighter>
      </div>
    </div>
  );
};

// Controls Row
export const ControlRowView = ({
  title,
  description,
  value,
  control,
  className,
  truncateLength = 20,
}: {
  title: string;
  description: string;
  value: string | number | boolean;
  control: any;
  className?: string;
  truncateLength?: number;
}) => {
  return (
    <div className={`${className}`}>
      <div>
        <span className="text-primary inline-block">{title} </span>
        <span className="text-xs ml-1 text-accent -mt-2 inline-block">
          {truncateText(value + "", truncateLength)}
        </span>{" "}
        <Tooltip title={description}>
          <InformationCircleIcon className="text-gray-400 inline-block w-4 h-4" />
        </Tooltip>
      </div>
      {control}
      <div className="bordper-b  border-secondary border-dashed pb-2 mxp-2"></div>
    </div>
  );
};

export const BounceLoader = ({
  className,
  title = "",
}: {
  className?: string;
  title?: string;
}) => {
  return (
    <div className="inline-block">
      <div className="inline-flex gap-2">
        <span className="  rounded-full bg-accent h-2 w-2  inline-block"></span>
        <span className="animate-bounce rounded-full bg-accent h-3 w-3  inline-block"></span>
        <span className=" rounded-full bg-accent h-2 w-2  inline-block"></span>
      </div>
      <span className="  text-sm">{title}</span>
    </div>
  );
};

export const ImageLoader = ({
  src,
  className = "",
}: {
  src: string;
  className?: string;
}) => {
  const [isLoading, setIsLoading] = useState(true);

  return (
    <div className="w-full rounded relative">
      {isLoading && (
        <div className="absolute h-24 inset-0 flex items-center justify-center">
          <BounceLoader title=" loading .." />{" "}
        </div>
      )}
      <img
        alt="Dynamic content"
        src={src}
        className={`w-full  rounded ${
          isLoading ? "opacity-0" : "opacity-100"
        } ${className}`}
        onLoad={() => setIsLoading(false)}
      />
    </div>
  );
};

type DataRow = { [key: string]: any };
export const CsvLoader = ({
  csvUrl,
  className,
}: {
  csvUrl: string;
  className?: string;
}) => {
  const [data, setData] = useState<DataRow[]>([]);
  const [columns, setColumns] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [pageSize, setPageSize] = useState<number>(50);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(csvUrl);
        const csvString = await response.text();
        const parsedData = Papa.parse(csvString, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
        });
        setData(parsedData.data as DataRow[]);

        // Use the keys of the first object for column headers
        const firstRow = parsedData.data[0] as DataRow; // Type assertion
        const columnHeaders: any[] = Object.keys(firstRow).map((key) => {
          const val = {
            title: key.charAt(0).toUpperCase() + key.slice(1), // Capitalize the key for the title
            dataIndex: key,
            key: key,
          };
          if (typeof firstRow[key] === "number") {
            return {
              ...val,
              sorter: (a: DataRow, b: DataRow) => a[key] - b[key],
            };
          }
          return val;
        });
        setColumns(columnHeaders);
        setIsLoading(false);
      } catch (error) {
        console.error("Error fetching CSV data:", error);
        setIsLoading(false);
      }
    };

    fetchData();
  }, [csvUrl]);

  // calculate x scroll, based on number of columns
  const scrollX = columns.length * 150;

  return (
    <div className={`CsvLoader ${className}`}>
      <Table
        dataSource={data}
        columns={columns}
        loading={isLoading}
        pagination={{ pageSize: pageSize }}
        scroll={{ y: 450, x: scrollX }}
        onChange={(pagination) => {
          setPageSize(pagination.pageSize || 50);
        }}
      />
    </div>
  );
};

export const CodeLoader = ({
  url,
  className,
}: {
  url: string;
  className?: string;
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [code, setCode] = useState<string | null>(null);

  React.useEffect(() => {
    fetch(url)
      .then((response) => response.text())
      .then((data) => {
        setCode(data);
        setIsLoading(false);
      });
  }, [url]);

  return (
    <div className={`w-full rounded relative ${className}`}>
      {isLoading && (
        <div className="absolute h-24 inset-0 flex items-center justify-center">
          <BounceLoader />
        </div>
      )}

      {!isLoading && <CodeBlock code={code || ""} language={"python"} />}
    </div>
  );
};

export const PdfViewer = ({ url }: { url: string }) => {
  const [loading, setLoading] = useState<boolean>(true);

  React.useEffect(() => {
    // Assuming the URL is directly usable as the source for the <object> tag
    setLoading(false);
    // Note: No need to handle the creation and cleanup of a blob URL or converting file content as it's not provided anymore.
  }, [url]);

  // Render the PDF viewer
  return (
    <div className="h-full">
      {loading && <p>Loading PDF...</p>}
      {!loading && (
        <object
          className="w-full rounded"
          data={url}
          type="application/pdf"
          width="100%"
          style={{ height: "calc(90vh - 200px)" }}
        >
          <p>PDF cannot be displayed.</p>
        </object>
      )}
    </div>
  );
};

export const MonacoEditor = ({
  value,
  editorRef,
  language,
  onChange,
  minimap = true,
}: {
  value: string;
  onChange?: (value: string) => void;
  editorRef: any;
  language: string;
  minimap?: boolean;
}) => {
  const [isEditorReady, setIsEditorReady] = useState(false);
  const onEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor;
    setIsEditorReady(true);
  };
  return (
    <div className="h-full rounded">
      <Editor
        height="100%"
        className="h-full rounded"
        defaultLanguage={language}
        defaultValue={value}
        value={value}
        onChange={(value: string | undefined) => {
          if (onChange && value) {
            onChange(value);
          }
        }}
        onMount={onEditorDidMount}
        theme="vs-dark"
        options={{
          wordWrap: "on",
          wrappingIndent: "indent",
          wrappingStrategy: "advanced",
          minimap: {
            enabled: minimap,
          },
        }}
      />
    </div>
  );
};

export const CardHoverBar = ({
  items,
}: {
  items: {
    title: string;
    icon: any;
    hoverText: string;
    onClick: (e: any) => void;
  }[];
}) => {
  const itemRows = items.map((item, i) => {
    return (
      <div
        key={"cardhoverrow" + i}
        role="button"
        className="text-accent text-xs inline-block hover:bg-primary p-2 rounded"
        onClick={item.onClick}
      >
        <Tooltip title={item.hoverText}>
          <item.icon className=" w-5, h-5 cursor-pointer inline-block" />
        </Tooltip>
      </div>
    );
  });
  return (
    <div
      onMouseEnter={(e) => {
        e.stopPropagation();
      }}
      className=" mt-2 text-right opacity-0 group-hover:opacity-100 "
    >
      {itemRows}
    </div>
  );
};

export const AgentRow = ({ message }: { message: any }) => {
  return (
    <GroupView
      title={
        <div className="rounded p-1 px-2 inline-block text-xs bg-secondary">
          <span className="font-semibold">{message.sender}</span> ( to{" "}
          {message.recipient} )
        </div>
      }
      className="m"
    >
      <MarkdownView data={message.message?.content} className="text-sm" />
    </GroupView>
  );
};
