import {
  ChevronDownIcon,
  ChevronUpIcon,
  Cog8ToothIcon,
  XMarkIcon,
  ClipboardIcon,
  PlusIcon,
  ArrowPathIcon,
  ArrowDownRightIcon,
} from "@heroicons/react/24/outline";
import React, { ReactNode, useEffect, useRef, useState } from "react";
import Icon from "./icons";
import { Button, Input, Modal, Select, Slider, Tooltip, message } from "antd";
import remarkGfm from "remark-gfm";
import ReactMarkdown from "react-markdown";
import { atomDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { fetchJSON, getServerUrl, truncateText } from "./utils";
import {
  IAgentFlowSpec,
  IFlowConfig,
  IModelConfig,
  ISkill,
  IStatus,
} from "./types";
import { ResizableBox } from "react-resizable";
import debounce from "lodash.debounce";
import TextArea from "antd/es/input/TextArea";
import { appContext } from "../hooks/provider";

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
    <div
      onClick={onClick}
      role={"button"}
      className={`${border} border-2 bg-secondary  group ${className} rounded ${cursor} transition duration-300`}
    >
      <div className="mt- text-sm text-secondary  break-words">
        {title && (
          <div className="text-accent rounded font-semibold  text-xs pb-1">
            {title}
          </div>
        )}
        <div>{subtitle}</div>
        {children}
      </div>
    </div>
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
        <div className={`${className} bg-light  rounded rounded-t-none`}>
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
      <div className="rounded bg-secondary mt-4 p-3">
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
  className = " bg-primary ",
}: any) => {
  return (
    <div className={`rounded mt-4  border-secondary   ${className}`}>
      <div className="mt-4 p-2 rounded border relative">
        <div className={`absolute  -top-5  p-2 inline-block ${className}`}>
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
            className="absolute inset-0 bg-secondary flex"
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
}: {
  title: string;
  description: string;
  value: string | number;
  control: any;
  className?: string;
}) => {
  return (
    <div className={`${className}`}>
      <div>
        <span className="text-primary inline-block">{title} </span>
        <span className="text-xs ml-1 text-accent -mt-2 inline-block">
          {truncateText(value + "", 20)}
        </span>
      </div>
      <div className="text-secondary text-xs"> {description} </div>
      {control}

      <div className="border-b border-dashed mt-2 mx-2"></div>
    </div>
  );
};

export const ModelSelector = ({
  configs,
  setConfigs,
  className,
}: {
  configs: IModelConfig[];
  setConfigs: (configs: IModelConfig[]) => void;
  className?: string;
}) => {
  // const [configs, setConfigs] = useState<IModelConfig[]>(modelConfigs);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [newModelConfig, setNewModelConfig] = useState<IModelConfig | null>(
    null
  );
  const [editIndex, setEditIndex] = useState<number | null>(null);

  const sanitizeModelConfig = (config: IModelConfig) => {
    const sanitizedConfig: IModelConfig = { model: config.model };
    if (config.api_key) sanitizedConfig.api_key = config.api_key;
    if (config.base_url) sanitizedConfig.base_url = config.base_url;
    if (config.api_type) sanitizedConfig.api_type = config.api_type;
    return sanitizedConfig;
  };

  const handleRemoveConfig = (index: number) => {
    const updatedConfigs = configs.filter((_, i) => i !== index);
    setConfigs(updatedConfigs);
  };

  const showModal = (config: IModelConfig | null, index: number | null) => {
    setNewModelConfig(config);
    setEditIndex(index);
    setIsModalVisible(true);
  };

  const handleOk = () => {
    if (newModelConfig?.model.trim()) {
      const sanitizedConfig = sanitizeModelConfig(newModelConfig);

      if (editIndex !== null) {
        // Edit existing model
        const updatedConfigs = [...configs];
        updatedConfigs[editIndex] = sanitizedConfig;
        setConfigs(updatedConfigs);
      } else {
        // Add new model
        setConfigs([...configs, sanitizedConfig]);
      }
      setIsModalVisible(false);
      setNewModelConfig(null);
      setEditIndex(null);
    } else {
      // Handle case where 'model' field is empty
      // Could provide user feedback here (e.g., input validation error)
      message.error("Model name cannot be empty");
    }
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    setNewModelConfig(null);
    setEditIndex(null);
  };

  const updateNewModelConfig = (field: keyof IModelConfig, value: string) => {
    setNewModelConfig((prevState) =>
      prevState ? { ...prevState, [field]: value } : null
    );
  };

  const modelButtons = configs.map((config, i) => {
    const tooltipText = `${config.model} \n ${config.base_url || ""} \n ${
      config.api_type || ""
    }`;
    return (
      <div
        key={"modelrow_" + i}
        className="mr-1 mb-1 p-1 px-2 rounded border"
        onClick={() => showModal(config, i)}
      >
        <div className="inline-flex">
          {" "}
          <Tooltip title={tooltipText}>
            <div>{config.model}</div>{" "}
          </Tooltip>
          <div
            role="button"
            onClick={(e) => {
              e.stopPropagation(); // Prevent opening the modal to edit
              handleRemoveConfig(i);
            }}
            className="ml-1 text-primary hover:text-accent duration-300"
          >
            <XMarkIcon className="w-4 h-4 inline-block" />
          </div>
        </div>
      </div>
    );
  });

  return (
    <div className={`${className}`}>
      <div className="flex flex-wrap">
        {modelButtons}
        <div
          className="inline-flex mr-1 mb-1 p-1 px-2 rounded border hover:border-accent duration-300 hover:text-accent"
          role="button"
          onClick={() =>
            showModal(
              { model: "", api_key: "", base_url: "", api_type: "" },
              null
            )
          }
        >
          add <PlusIcon className="w-4 h-4 inline-block mt-1" />
        </div>
      </div>
      <Modal
        title={`${editIndex !== null ? "Edit" : "Add"} Model Configuration`}
        open={isModalVisible}
        onOk={handleOk}
        onCancel={handleCancel}
        footer={[
          <Button key="back" onClick={handleCancel}>
            Cancel
          </Button>,
          <Button key="submit" type="primary" onClick={handleOk}>
            {editIndex !== null ? "Save Changes" : "Add Model"}
          </Button>,
        ]}
      >
        <div className="text-sm my-2">Enter parameters for your model.</div>
        <Input
          placeholder="Model Name"
          value={newModelConfig?.model}
          onChange={(e) => updateNewModelConfig("model", e.target.value)}
        />
        <Input.Password
          className="mt-2"
          placeholder="API Key"
          value={newModelConfig?.api_key}
          onChange={(e) => updateNewModelConfig("api_key", e.target.value)}
        />
        <Input
          className="mt-2"
          placeholder="Base URL"
          value={newModelConfig?.base_url}
          onChange={(e) => updateNewModelConfig("base_url", e.target.value)}
        />
        <Input
          className="mt-2"
          placeholder="Model Type (optional)"
          value={newModelConfig?.api_type}
          onChange={(e) => updateNewModelConfig("api_type", e.target.value)}
        />

        <Input
          className="mt-2"
          placeholder="API Version (optional)"
          value={newModelConfig?.api_version}
          onChange={(e) => updateNewModelConfig("api_version", e.target.value)}
        />
      </Modal>
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
    <div>
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
        className={`w-full rounded ${
          isLoading ? "opacity-0" : "opacity-100"
        } ${className}`}
        onLoad={() => setIsLoading(false)}
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
          height="450px"
        >
          <p>PDF cannot be displayed.</p>
        </object>
      )}
    </div>
  );
};

export const AgentFlowSpecView = ({
  title = "Agent Specification",
  flowSpec,
  setFlowSpec,
}: {
  title: string;
  flowSpec: IAgentFlowSpec;
  setFlowSpec: (newFlowSpec: IAgentFlowSpec) => void;
  editMode?: boolean;
}) => {
  // Local state for the FlowView component
  const [localFlowSpec, setLocalFlowSpec] =
    React.useState<IAgentFlowSpec>(flowSpec);

  // Event handlers for updating local state and propagating changes

  const onControlChange = (value: any, key: string) => {
    const updatedFlowSpec = {
      ...localFlowSpec,
      config: { ...localFlowSpec.config, [key]: value },
    };
    setLocalFlowSpec(updatedFlowSpec);
    setFlowSpec(updatedFlowSpec);
  };

  const onDebouncedControlChange = React.useCallback(
    debounce((value: any, key: string) => {
      onControlChange(value, key);
    }, 3000),
    [onControlChange]
  );

  const llm_config = localFlowSpec.config.llm_config || { config_list: [] };

  return (
    <>
      <div className="text-accent">{title}</div>
      <GroupView title={flowSpec.config.name} className="mb-4">
        <ControlRowView
          title="Agent Name"
          className="mt-4"
          description="Name of the agent"
          value={flowSpec.config.name}
          control={
            <Input
              className="mt-2"
              placeholder="Agent Name"
              value={flowSpec.config.name}
              onChange={(e) => {
                onControlChange(e.target.value, "name");
              }}
            />
          }
        />

        <ControlRowView
          title="Agent Description"
          className="mt-4"
          description="Description of the agent"
          value={flowSpec.description || ""}
          control={
            <Input
              className="mt-2"
              placeholder="Agent Description"
              value={flowSpec.description}
              onChange={(e) => {
                const updatedFlowSpec = {
                  ...localFlowSpec,
                  description: e.target.value,
                };
                setLocalFlowSpec(updatedFlowSpec);
                setFlowSpec(updatedFlowSpec);
              }}
            />
          }
        />

        <ControlRowView
          title="Max Consecutive Auto Reply"
          className="mt-4"
          description="Max consecutive auto reply messages before termination."
          value={flowSpec.config.max_consecutive_auto_reply}
          control={
            <Slider
              min={2}
              max={30}
              defaultValue={flowSpec.config.max_consecutive_auto_reply}
              step={1}
              onAfterChange={(value: any) => {
                onControlChange(value, "max_consecutive_auto_reply");
              }}
            />
          }
        />

        <ControlRowView
          title="Human Input Mode"
          description="Defines when to request human input"
          value={flowSpec.config.human_input_mode}
          control={
            <Select
              className="mt-2 w-full"
              defaultValue={flowSpec.config.human_input_mode}
              onChange={(value: any) => {
                onControlChange(value, "human_input_mode");
              }}
              options={
                [
                  { label: "NEVER", value: "NEVER" },
                  { label: "TERMINATE", value: "TERMINATE" },
                  { label: "ALWAYS", value: "ALWAYS" },
                ] as any
              }
            />
          }
        />

        {llm_config && (
          <ControlRowView
            title="System Message"
            className="mt-4"
            description="Free text to control agent behavior"
            value={flowSpec.config.system_message}
            control={
              <TextArea
                className="mt-2 w-full"
                value={flowSpec.config.system_message}
                rows={3}
                onChange={(e) => {
                  onDebouncedControlChange(e.target.value, "system_message");
                }}
              />
            }
          />
        )}

        {llm_config && (
          <ControlRowView
            title="Model"
            className="mt-4"
            description="Defines which models are used for the agent."
            value={llm_config?.config_list?.[0]?.model}
            control={
              <ModelSelector
                className="mt-2 w-full"
                configs={llm_config.config_list || []}
                setConfigs={(config_list: IModelConfig[]) => {
                  const llm_config = {
                    ...flowSpec.config.llm_config,
                    config_list,
                  };
                  onControlChange(llm_config, "llm_config");
                }}
              />
            }
          />
        )}

        {
          <ControlRowView
            title="Skills"
            className="mt-4"
            description="Defines skills available to the agent."
            value={(flowSpec.skills && flowSpec.skills[0]?.title) || ""}
            control={
              <SkillSelector
                className="mt-2 w-full"
                skills={flowSpec.skills || []}
                setSkills={(skills: ISkill[]) => {
                  const updatedFlowSpec = {
                    ...localFlowSpec,
                    skills,
                  };
                  setLocalFlowSpec(updatedFlowSpec);
                  setFlowSpec(updatedFlowSpec);
                }}
              />
            }
          />
        }
      </GroupView>
    </>
  );
};

interface SkillSelectorProps {
  skills: ISkill[];
  setSkills: (skills: ISkill[]) => void;
  className?: string;
}

export const SkillSelector: React.FC<SkillSelectorProps> = ({
  skills,
  setSkills,
  className,
}) => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [showSkillModal, setShowSkillModal] = React.useState(false);
  const [newSkill, setNewSkill] = useState<ISkill | null>(null);

  const [localSkills, setLocalSkills] = useState<ISkill[]>(skills);
  const [selectedSkill, setSelectedSkill] = useState<ISkill | null>(null);

  const handleRemoveSkill = (index: number) => {
    const updatedSkills = localSkills.filter((_, i) => i !== index);
    setLocalSkills(updatedSkills);
    setSkills(updatedSkills);
  };

  const handleAddSkill = () => {
    if (newSkill) {
      const updatedSkills = [...localSkills, newSkill];
      setLocalSkills(updatedSkills);
      setSkills(updatedSkills);
      setNewSkill(null);
    }
  };

  useEffect(() => {
    if (selectedSkill) {
      setShowSkillModal(true);
    }
  }, [selectedSkill]);

  return (
    <>
      <Modal
        title={selectedSkill?.title}
        width={800}
        open={showSkillModal}
        onOk={() => {
          setShowSkillModal(false);
          setSelectedSkill(null);
        }}
        onCancel={() => {
          setShowSkillModal(false);
          setSelectedSkill(null);
        }}
      >
        {selectedSkill && (
          <div>
            <div className="mb-2">{selectedSkill.file_name}</div>
            <CodeBlock code={selectedSkill?.content} language="python" />
          </div>
        )}
      </Modal>

      <div className={`${className} flex flex-wrap gap-2 `}>
        {localSkills.map((skill, index) => (
          <div
            key={"skillitemrow" + index}
            className=" mb-1 p-1 px-2 rounded border"
          >
            <span
              role="button"
              onClick={() => {
                setSelectedSkill(skill);
              }}
              className=" inline-block "
            >
              {skill.title}
            </span>
            <XMarkIcon
              role="button"
              onClick={() => handleRemoveSkill(index)}
              className="ml-1 text-primary hover:text-accent duration-300 w-4 h-4 inline-block"
            />
          </div>
        ))}

        <div
          className="inline-flex mr-1 mb-1 p-1 px-2 rounded border hover:border-accent duration-300 hover:text-accent"
          role="button"
          onClick={() => {
            setIsModalVisible(true);
          }}
        >
          add <PlusIcon className="w-4 h-4 inline-block mt-1" />
        </div>
      </div>

      <Modal
        title="Add Skill"
        open={isModalVisible}
        onOk={handleAddSkill}
        onCancel={() => setIsModalVisible(false)}
        footer={[
          <Button key="back" onClick={() => setIsModalVisible(false)}>
            Cancel
          </Button>,
          <Button
            key="submit"
            type="primary"
            onClick={() => {
              handleAddSkill();
              setIsModalVisible(false);
            }}
          >
            Add Skill
          </Button>,
        ]}
      >
        <SkillLoader skill={newSkill} setSkill={setNewSkill} />
      </Modal>
    </>
  );
};

export const SkillLoader = ({
  skill,
  setSkill,
}: {
  skill: ISkill | null;
  setSkill: (skill: ISkill | null) => void;
}) => {
  const [skills, setSkills] = useState<ISkill[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });
  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);
  const listSkillsUrl = `${serverUrl}/skills?user_id=${user?.email}`;

  const fetchSkills = () => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setSkills(data.data);
        if (data.data.length > 0) {
          setSkill(data.data[0]);
        }
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(listSkillsUrl, payLoad, onSuccess, onError);
  };

  useEffect(() => {
    fetchSkills();
  }, []);

  const skillOptions = skills.map((skill: ISkill, index: number) => ({
    label: skill.title,
    value: index,
  }));
  return (
    <div className="relative">
      <LoadingOverlay loading={loading} />
      <ControlRowView
        title="Skills"
        description="Select an available skill"
        value={skill?.title || skills[0]?.title}
        control={
          <>
            {skills && (
              <>
                <Select
                  className="mt-2 w-full"
                  defaultValue={skill?.title || skills[0]?.title}
                  value={skill?.title || skills[0]?.title}
                  onChange={(value: any) => {
                    setSkill(skills[value]);
                  }}
                  options={skillOptions}
                />
                {(skill || skills[0]) && (
                  <CodeBlock
                    className="mt-4"
                    code={skill?.content || skills[0]?.content || ""}
                    language="python"
                  />
                )}
              </>
            )}
          </>
        }
      />
    </div>
  );
};

export const FlowConfigViewer = ({
  flowConfig,
  setFlowConfig,
}: {
  flowConfig: IFlowConfig;
  setFlowConfig: (newFlowConfig: IFlowConfig) => void;
}) => {
  // Local state for sender and receiver FlowSpecs
  const [senderFlowSpec, setSenderFlowSpec] = React.useState<IAgentFlowSpec>(
    flowConfig.sender
  );

  const [localFlowConfig, setLocalFlowConfig] =
    React.useState<IFlowConfig>(flowConfig);

  const [receiverFlowSpec, setReceiverFlowSpec] =
    React.useState<IAgentFlowSpec>(flowConfig.receiver);

  // Update the local state and propagate changes to the parent component
  const updateSenderFlowSpec = (newFlowSpec: IAgentFlowSpec) => {
    setSenderFlowSpec(newFlowSpec);
    setFlowConfig({ ...flowConfig, sender: newFlowSpec });
  };

  const updateReceiverFlowSpec = (newFlowSpec: IAgentFlowSpec) => {
    setReceiverFlowSpec(newFlowSpec);
    setFlowConfig({ ...flowConfig, receiver: newFlowSpec });
  };

  const updateFlowConfigName = (newName: string) => {
    const updatedFlowConfig = { ...localFlowConfig, name: newName };
    setLocalFlowConfig(updatedFlowConfig);
    setFlowConfig(updatedFlowConfig);
  };

  // React.useEffect(() => {
  //   setLocalFlowConfig(flowConfig);
  // }, [flowConfig]);

  return (
    <>
      {/* <div className="mb-2">{flowConfig.name}</div> */}
      <ControlRowView
        title="Workflow Name"
        className="mt-4 mb-2"
        description="Name of the workflow"
        value={localFlowConfig.name}
        control={
          <Input
            className="mt-2 w-full"
            value={localFlowConfig.name}
            onChange={(e) => updateFlowConfigName(e.target.value)}
          />
        }
      />

      <ControlRowView
        title="Workflow Description"
        className="mt-4 mb-2"
        description="Description of the workflow"
        value={localFlowConfig.description}
        control={
          <Input
            className="mt-2 w-full"
            value={localFlowConfig.description}
            onChange={(e) => {
              const updatedConfig = {
                ...localFlowConfig,
                description: e.target.value,
              };
              setLocalFlowConfig(updatedConfig);
              setFlowConfig(updatedConfig);
            }}
          />
        }
      />

      <ControlRowView
        title="Summary Method"
        description="Defines the method to summarize the conversation"
        value={localFlowConfig.summary_method || "last"}
        control={
          <Select
            className="mt-2 w-full"
            defaultValue={localFlowConfig.summary_method || "last"}
            onChange={(value: any) => {
              const updatedConfig = {
                ...localFlowConfig,
                summary_method: value,
              };
              setLocalFlowConfig(updatedConfig);
              setFlowConfig(updatedConfig);
            }}
            options={
              [
                { label: "last", value: "last" },
                { label: "none", value: "none" },
                { label: "llm", value: "llm" },
              ] as any
            }
          />
        }
      />
      <div className="flex gap-3 ">
        <div className="w-1/2">
          <div className="">
            <AgentFlowSpecView
              title="Sender"
              flowSpec={senderFlowSpec}
              setFlowSpec={updateSenderFlowSpec}
            />
          </div>
        </div>
        <div className="w-1/2">
          <AgentFlowSpecView
            title="Receiver"
            flowSpec={receiverFlowSpec}
            setFlowSpec={updateReceiverFlowSpec}
          />
        </div>
      </div>
    </>
  );
};
