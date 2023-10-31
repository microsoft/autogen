import {
  ArrowPathIcon,
  Cog6ToothIcon,
  DocumentChartBarIcon,
  ExclamationTriangleIcon,
  PaperAirplaneIcon,
  PuzzlePieceIcon,
  TrashIcon,
  UserIcon,
} from "@heroicons/react/24/outline";
import { Button, Dropdown, MenuProps, Space, message } from "antd";
import * as React from "react";
import remarkGfm from "remark-gfm";
import ReactMarkdown from "react-markdown";
import { atomDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  IChatMessage,
  IContextItem,
  IGenConfig,
  IMessage,
  IStatus,
} from "../../../types";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { fetchJSON } from "../../../utils";
import { appContext } from "../../../../hooks/provider";
import Icon from "../../../icons";
import { parse } from "path";

const ChatBox = ({
  context,
  config,
  setMetadata,
  initMessages,
  skillup,
}: {
  context: IContextItem | null;
  config: any;
  setMetadata: any;
  initMessages: any[];
  skillup: any;
}) => {
  const queryInputRef = React.useRef<HTMLInputElement>(null);
  const messageBoxInputRef = React.useRef<HTMLDivElement>(null);
  const { user } = React.useContext(appContext);

  const serverUrl = process.env.GATSBY_API_URL;
  const deleteMsgUrl = `${serverUrl}/messages/delete`;

  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });
  const [messages, setMessages] = React.useState<IChatMessage[]>([]);

  let pageHeight, chatMaxHeight;
  if (typeof window !== "undefined") {
    pageHeight = window.innerHeight;
    chatMaxHeight = pageHeight - 300 + "px";
  }

  const parseMessages = (messages: any) => {
    return messages.map((message: any) => {
      let meta;
      try {
        meta = JSON.parse(message.metadata);
      } catch (e) {
        meta = message.metadata;
      }
      const msg: IChatMessage = {
        text: message.content,
        sender: message.role === "user" ? "user" : "bot",
        metadata: meta,
        msgId: message.msgId,
      };
      return msg;
    });
  };

  React.useEffect(() => {
    // console.log("initMessages changed", initMessages);
    const initMsgs: IChatMessage[] = parseMessages(initMessages);
    setMessages(initMsgs);
  }, [initMessages]);

  function processString(inputString: string): string {
    inputString = inputString.replace(/\n/g, "  \n");
    const markdownPattern = /```markdown\s+([\s\S]*?)\s+```/g;
    return inputString?.replace(markdownPattern, (match, content) => content);
  }

  const deleteMessage = (messageId: number) => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ userId: user?.email, msgId: messageId }),
    };

    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        setMessages(parseMessages(data.data));

        console.log("updated profile", data);
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
    fetchJSON(deleteMsgUrl, payLoad, onSuccess, onError);
  };

  const examplePrompts = [
    {
      title: "Stock Price",
      prompt:
        "Plot a chart of NVDA and TESLA stock price YTD. Save the result to a file named nvda_tesla.png",
    },
    {
      title: "Sine Wave",
      prompt:
        "Write a python script to plot a sine wave and save it to disc as a png file sine_wave.png",
    },
    {
      title: "Markdown",
      prompt:
        "List out the top 5 rivers in africa and their length and return that as a markdown table. Do not try to write any code, just write the table",
    },
    // {
    //   title: "Haiku",
    //   prompt:
    //     "Write me haiku about flowers in markdown format. do not try to write any code, just write the haiku",
    // },
    // {
    //   title: "ASCII",
    //   prompt:
    //     "Write a python script to print out a cat in ASCII art. Save the output to a file named cat.txt",
    // },
    {
      title: "@execute",
      prompt: "@execute",
    },
    {
      title: "@memorize",
      prompt: "@memorize",
    },
  ];

  const promptButtons = examplePrompts.map((prompt, i) => {
    return (
      <Button
        key={"prompt" + i}
        type="primary"
        className=""
        onClick={() => {
          getCompletion(prompt.prompt);
        }}
      >
        {" "}
        {prompt.title}{" "}
      </Button>
    );
  });

  const checkIsSkill = (message: string) => {
    // check if message contains lowercase of 'Learned a new skill'
    if (message.toLowerCase().includes("learned a new skill")) {
      skillup.set(new Date().toLocaleTimeString());
      console.log("learned a new skill .. updating UI ");
    }
  };

  const messageListView = messages.map((message: IChatMessage, i: number) => {
    const isUser = message.sender === "user";
    const css = isUser ? "bg-accent text-white  " : "bg-light";
    // console.log("message", message);
    let hasMeta = false;
    if (message.metadata) {
      hasMeta =
        message.metadata.code !== null ||
        message.metadata.images?.length > 0 ||
        message.metadata.files?.length > 0 ||
        message.metadata.scripts?.length > 0;
    }

    let items: MenuProps["items"] = [];

    if (isUser) {
      items.push({
        label: (
          <div
            onClick={() => {
              console.log("retrying");
              getCompletion(message.text);
            }}
          >
            <ArrowPathIcon
              role={"button"}
              title={"Retry"}
              className="h-4 w-4 mr-1 inline-block"
            />
            Retry
          </div>
        ),
        key: "retrymessage",
      });
    }

    if (hasMeta) {
      items.push({
        label: (
          <div
            onClick={() => {
              setMetadata(message.metadata);
            }}
          >
            <DocumentChartBarIcon
              title={"View Metadata"}
              className="h-4 w-4 mr-1 inline-block"
            />
            View Metadata
          </div>
        ),
        key: "metadata",
      });
    }

    if (messages.length - 1 === i) {
      items.push({
        type: "divider",
      });

      items.push({
        label: (
          <div
            onClick={() => {
              console.log("deleting", message);
              deleteMessage(message.msgId);
            }}
          >
            <TrashIcon
              title={"Delete message"}
              className="h-4 w-4 mr-1 inline-block"
            />
            Delete Message
          </div>
        ),
        key: "deletemessage",
      });
    }

    const menu = (
      <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
        <div
          role="button"
          className="float-right ml-2 duration-100 hover:bg-secondary font-semibold px-2 pb-1  rounded"
        >
          <span className="block -mt-2  "> ...</span>
        </div>
      </Dropdown>
    );

    return (
      <div
        className={`align-right ${isUser ? "text-right" : ""}  mb-2 `}
        key={"message" + i}
      >
        {" "}
        <div className={`  ${isUser ? "" : " w-full"} inline-flex gap-2`}>
          <div className="">
            {" "}
            {isUser && <UserIcon className="inline-block h-6 " />}
            {!isUser && (
              <span className="inline-block  text-accent  bg-primary pb-2 ml-1">
                <Icon icon="app" size={8} />
              </span>
            )}
          </div>
          <div
            // style={{ minWidth: "70%" }}
            className={`inline-block ${
              isUser ? "" : " w-full "
            } p-2 rounded  ${css}`}
          >
            {" "}
            {items.length > 0 && menu}
            {isUser && (
              <>
                <div className="inline-block">
                  {message.text}
                  <ArrowPathIcon
                    role={"button"}
                    title={"Retry"}
                    className="h-4 w-4 hidden ml-1 inline-block"
                    onClick={() => {
                      getCompletion(message.text);
                    }}
                  />
                </div>
              </>
            )}
            {!isUser && (
              <div
                className={`   w-full chatbox prose dark:prose-invert text-primary rounded p-2 `}
              >
                <ReactMarkdown
                  children={processString(message.text)}
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      let match = /language-(\w+)/.exec(className || "");
                      match = match ? match : "text";
                      return !inline && match ? (
                        <SyntaxHighlighter
                          {...props}
                          children={String(children).replace(/\n$/, "")}
                          style={atomDark}
                          language={match[1]}
                          className="rounded"
                          PreTag="div"
                          wrapLongLines={true}
                        />
                      ) : (
                        <code {...props} className={className}>
                          {children}
                        </code>
                      );
                    },
                  }}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  });

  React.useEffect(() => {
    // console.log("messages updated, scrolling");
    scrollChatBox();
  }, [messages]);

  // clear text box if loading has just changed to false and there is no error
  React.useEffect(() => {
    if (loading === false && queryInputRef.current) {
      if (queryInputRef.current) {
        // console.log("loading changed", loading, error);
        if (error === null || (error && error.status === false)) {
          queryInputRef.current.value = "";
        }
      }
    }
  }, [loading]);

  // scroll to queryInputRef on load
  React.useEffect(() => {
    // console.log("scrolling to query input");
    // if (queryInputRef.current) {
    //   queryInputRef.current.scrollIntoView({
    //     behavior: "smooth",
    //     block: "center",
    //   });
    // }
  }, []);

  const chatHistory = (messages: IChatMessage[]) => {
    let history = "";
    messages.forEach((message) => {
      history += message.text + "\n"; // message.sender + ": " + message.text + "\n";
    });
    return history;
  };

  const scrollChatBox = () => {
    messageBoxInputRef.current?.scroll({
      top: messageBoxInputRef.current.scrollHeight,
      behavior: "smooth",
    });
  };

  const getCompletion = (query: string) => {
    setError(null);
    let messageHolder = Object.assign([], messages);
    let history = chatHistory(messages);

    const userMessage: IChatMessage = {
      text: query,
      sender: "user",
    };
    messageHolder.push(userMessage);
    setMessages(messageHolder);

    const payload: IMessage = {
      role: "user",
      content: query,
      userId: user?.email || "",
      timestamp: new Date().toISOString(),
      rootMsgId: 0,
      msgId: 0,
      personalize: config.get.personalize,
      use_cache: config.get.use_cache,
      ra: config.get.ra,
    };

    console.log("payload", payload);

    const textUrl = `${serverUrl}/messages`;
    const postData = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    };
    setLoading(true);
    fetch(textUrl, postData)
      .then((res) => {
        setLoading(false);
        if (res.status === 200) {
          res.json().then((data) => {
            if (data && data.status) {
              console.log("******* response received ", data);
              const botMesage: IChatMessage = {
                text: data.message,
                sender: "bot",
                metadata: data.metadata,
                msgId: data.msgId,
              };
              checkIsSkill(data.message);
              if (data.metadata) {
                setMetadata(data.metadata);
              }
              messageHolder.push(botMesage);
              messageHolder = Object.assign([], messageHolder);
              setMessages(messageHolder);
            } else {
              console.log("error", data);
              // setError(data);
              message.error(data.message);
            }
          });
        } else {
          message.error("Connection error. Ensure server is up and running.");
        }
      })
      .catch((err) => {
        setLoading(false);
        message.error("Connection error. Ensure server is up and running.");
      });
  };

  return (
    <div className="text-primary   relative  h-full rounded  ">
      <div
        ref={messageBoxInputRef}
        className="flex h-max    flex-col rounded  scroll pr-2 overflow-auto  "
        style={{ minHeight: "300px", maxHeight: chatMaxHeight }}
      >
        <div className="flex-1  boder mt-4"></div>
        <div className="ml-2"> {messageListView}</div>
        <div className="ml-2 h-6   mb-4 mt-2   ">
          {loading && (
            <div className="inline-flex gap-2">
              <span className="  rounded-full bg-accent h-2 w-2  inline-block"></span>
              <span className="animate-bounce rounded-full bg-accent h-3 w-3  inline-block"></span>
              <span className=" rounded-full bg-accent h-2 w-2  inline-block"></span>
            </div>
          )}
        </div>
      </div>
      <div className="mt-2 p-2 absolute   bg-primary  bottom-0 w-full">
        <div
          className={`mt-2   rounded p-2 shadow-lg flex mb-1  gap-2 ${
            loading ? " opacity-50 pointer-events-none" : ""
          }`}
        >
          {/* <input className="flex-1 p-2 ring-2" /> */}
          <form
            autoComplete="on"
            className="flex-1 "
            onSubmit={(e) => {
              e.preventDefault();
              // if (queryInputRef.current && !loading) {
              //   getCompletion(queryInputRef.current?.value);
              // }
            }}
          >
            <input
              id="queryInput"
              name="queryInput"
              autoComplete="on"
              onKeyDown={(e) => {
                if (e.key === "Enter" && queryInputRef.current && !loading) {
                  getCompletion(queryInputRef.current?.value);
                }
              }}
              ref={queryInputRef}
              className="w-full text-gray-600 bg-white p-2 ring-2 rounded-sm"
            />
          </form>
          <div
            role={"button"}
            onClick={() => {
              if (queryInputRef.current && !loading) {
                getCompletion(queryInputRef.current?.value);
              }
            }}
            className="bg-accent hover:brightness-75 transition duration-300 rounded pt-2 px-5 "
          >
            {" "}
            {!loading && (
              <div className="inline-block   ">
                <PaperAirplaneIcon className="h-6 text-white   inline-block" />{" "}
              </div>
            )}
            {loading && (
              <div className="inline-block   ">
                <Cog6ToothIcon className="relative -pb-2 text-white animate-spin  inline-flex rounded-full h-6 w-6" />
              </div>
            )}
          </div>
        </div>{" "}
        <div>
          <div className="mt-2 text-xs text-secondary">
            Blank slate? Try one of the example prompts below{" "}
          </div>
          <div
            className={`mt-2 inline-flex gap-2 flex-wrap  ${
              loading ? "brightness-75 pointer-events-none" : ""
            }`}
          >
            {promptButtons}
          </div>
        </div>
        {error && !error.status && (
          <div className="p-2 border rounded mt-4 text-orange-500 text-sm">
            {" "}
            <ExclamationTriangleIcon className="h-5 text-orange-500 inline-block mr-2" />{" "}
            {error.message}
          </div>
        )}
      </div>
    </div>
  );
};
export default ChatBox;
