import {
  ArrowPathIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  PaperAirplaneIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Button, Dropdown, MenuProps, message } from "antd";
import * as React from "react";
import { IChatMessage, IFlowConfig, IMessage, IStatus } from "../../types";
import { fetchJSON, getServerUrl, guid } from "../../utils";
import { appContext } from "../../../hooks/provider";
import MetaDataView from "./metadata";
import { MarkdownView } from "../../atoms";
import { useConfigStore } from "../../../hooks/store";

const ChatBox = ({
  config,
  initMessages,
  skillup,
}: {
  config: any;
  initMessages: any[];
  skillup: any;
}) => {
  const queryInputRef = React.useRef<HTMLInputElement>(null);
  const messageBoxInputRef = React.useRef<HTMLDivElement>(null);
  const { user } = React.useContext(appContext);

  const serverUrl = getServerUrl();
  const deleteMsgUrl = `${serverUrl}/messages/delete`;

  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const messages = useConfigStore((state) => state.messages);
  const setMessages = useConfigStore((state) => state.setMessages);
  const flowConfig: IFlowConfig = useConfigStore((state) => state.flowConfig);

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
        msg_id: message.msg_id,
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

  const deleteMessage = (messageId: string) => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ user_id: user?.email, msg_id: messageId }),
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

    if (messages.length - 1 === i) {
      // items.push({
      //   type: "divider",
      // });

      items.push({
        label: (
          <div
            onClick={() => {
              console.log("deleting", message);
              deleteMessage(message.msg_id);
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
        className={`align-right ${isUser ? "text-righpt" : ""}  mb-2 border-b`}
        key={"message" + i}
      >
        {" "}
        <div className={`  ${isUser ? "" : " w-full"} inline-flex gap-2`}>
          <div className="">
            {" "}
            {/* {isUser && <UserIcon className="inline-block h-6 " />}
            {!isUser && (
              <span className="inline-block  text-accent  bg-primary pb-2 ml-1">
                <Icon icon="app" size={8} />
              </span>
            )} */}
          </div>
          <div className="font-semibold text-secondary text-sm w-14">{`${
            isUser ? "USER" : "AGENT"
          }`}</div>
          <div
            // style={{ minWidth: "70%" }}
            className={`inline-block relative ${
              isUser ? "" : " w-full "
            } p-2 rounded  ${css}`}
          >
            {" "}
            {items.length > 0 && <div className="   ">{menu}</div>}
            {isUser && (
              <>
                <div className="inline-block">{message.text}</div>
              </>
            )}
            {!isUser && (
              <div
                className={` w-full chatbox prose dark:prose-invert text-primary rounded `}
              >
                <MarkdownView
                  className="text-sm"
                  data={message.text}
                  showCode={false}
                />
              </div>
            )}
            {message.metadata && (
              <div className="">
                <MetaDataView metadata={message.metadata} />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  });

  React.useEffect(() => {
    // console.log("messages updated, scrolling");

    setTimeout(() => {
      scrollChatBox();
    }, 200);
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
      msg_id: guid(),
    };
    messageHolder.push(userMessage);
    setMessages(messageHolder);

    const messagePayload: IMessage = {
      role: "user",
      content: query,
      msg_id: userMessage.msg_id,
      user_id: user?.email || "",
      root_msg_id: "0",
    };

    const textUrl = `${serverUrl}/messages`;
    const postData = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: messagePayload,
        flow_config: flowConfig,
      }),
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
                msg_id: data.msg_id,
              };
              checkIsSkill(data.message);
              // if (data.metadata) {
              //   setMetadata(data.metadata);
              // }
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
          res.json().then((data) => {
            console.log("error", data);
            // setError(data);
            message.error(data.message);
          });
          message.error("Connection error. Ensure server is up and running.");
        }
      })
      .catch((err) => {
        setLoading(false);

        message.error("Connection error. Ensure server is up and running.");
      });
  };

  return (
    <div className="text-primary    relative  h-full rounded  ">
      <div
        ref={messageBoxInputRef}
        className="flex h-full     flex-col rounded  scroll pr-2 overflow-auto  "
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
