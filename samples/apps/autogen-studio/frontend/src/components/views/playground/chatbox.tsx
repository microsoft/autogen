import {
  ArrowPathIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PaperAirplaneIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Button, Dropdown, MenuProps, message } from "antd";
import * as React from "react";
import {
  IChatMessage,
  IChatSession,
  IFlowConfig,
  IMessage,
  IStatus,
} from "../../types";
import { examplePrompts, fetchJSON, getServerUrl, guid } from "../../utils";
import { appContext } from "../../../hooks/provider";
import MetaDataView from "./metadata";
import { BounceLoader, MarkdownView } from "../../atoms";
import { useConfigStore } from "../../../hooks/store";

const ChatBox = ({
  initMessages,
  editable = true,
}: {
  initMessages: IMessage[] | null;
  editable?: boolean;
}) => {
  const session: IChatSession | null = useConfigStore((state) => state.session);
  const textAreaInputRef = React.useRef<HTMLTextAreaElement>(null);
  const messageBoxInputRef = React.useRef<HTMLDivElement>(null);
  const { user } = React.useContext(appContext);

  const serverUrl = getServerUrl();
  const deleteMsgUrl = `${serverUrl}/messages/delete`;

  const [loading, setLoading] = React.useState(false);
  const [text, setText] = React.useState("");
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const messages = useConfigStore((state) => state.messages);
  const setMessages = useConfigStore((state) => state.setMessages);
  const workflowConfig: IFlowConfig | null = useConfigStore(
    (state) => state.workflowConfig
  );

  let pageHeight, chatMaxHeight;
  if (typeof window !== "undefined") {
    pageHeight = window.innerHeight;
    chatMaxHeight = pageHeight - 350 + "px";
  }

  const parseMessages = (messages: any) => {
    return messages?.map((message: any) => {
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

  const messageListView = messages?.map((message: IChatMessage, i: number) => {
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

    // if (messages.length - 1 === i) {
    //   // items.push({
    //   //   type: "divider",
    //   // });

    //   items.push({
    //     label: (
    //       <div
    //         onClick={() => {
    //           console.log("deleting", message);
    //           deleteMessage(message.msg_id);
    //         }}
    //       >
    //         <TrashIcon
    //           title={"Delete message"}
    //           className="h-4 w-4 mr-1 inline-block"
    //         />
    //         Delete Message
    //       </div>
    //     ),
    //     key: "deletemessage",
    //   });
    // }

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
          <div className="font-semibold text-secondary text-sm w-16">{`${
            isUser ? "USER" : "AGENTS"
          }`}</div>
          <div
            // style={{ minWidth: "70%" }}
            className={`inline-block group relative ${
              isUser ? "" : " w-full "
            } p-2 rounded  ${css}`}
          >
            {" "}
            {items.length > 0 && editable && (
              <div className=" group-hover:opacity-100 opacity-0 ">{menu}</div>
            )}
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

  const textAreaDefaultHeight = "50px";
  // clear text box if loading has just changed to false and there is no error
  React.useEffect(() => {
    if (loading === false && textAreaInputRef.current) {
      if (textAreaInputRef.current) {
        if (error === null || (error && error.status === false)) {
          textAreaInputRef.current.value = "";
          textAreaInputRef.current.style.height = textAreaDefaultHeight;
        }
      }
    }
  }, [loading]);

  React.useEffect(() => {
    if (textAreaInputRef.current) {
      textAreaInputRef.current.style.height = textAreaDefaultHeight; // Reset height to shrink if text is deleted
      const scrollHeight = textAreaInputRef.current.scrollHeight;
      textAreaInputRef.current.style.height = `${scrollHeight}px`;
    }
  }, [text]);

  const chatHistory = (messages: IChatMessage[] | null) => {
    let history = "";
    messages?.forEach((message) => {
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
      session_id: session?.id || "",
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
        flow_config: workflowConfig,
      }),
    };
    setLoading(true);
    fetch(textUrl, postData)
      .then((res) => {
        setLoading(false);
        if (res.status === 200) {
          res.json().then((data) => {
            if (data && data.status) {
              const botMesage: IChatMessage = {
                text: data.message,
                sender: "bot",
                metadata: data.metadata,
                msg_id: data.msg_id,
              };
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
      .catch(() => {
        setLoading(false);

        message.error("Connection error. Ensure server is up and running.");
      });
  };

  const handleTextChange = (
    event: React.ChangeEvent<HTMLTextAreaElement>
  ): void => {
    setText(event.target.value);
  };

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>
  ): void => {
    if (event.key === "Enter" && !event.shiftKey) {
      if (textAreaInputRef.current && !loading) {
        event.preventDefault();
        getCompletion(textAreaInputRef.current.value);
      }
    }
  };

  return (
    <div className="text-primary    relative  h-full rounded  ">
      <div
        style={{ zIndex: 100 }}
        className=" absolute right-0  text-secondary -top-8 rounded p-2"
      >
        {" "}
        <div className="text-xs"> {session?.flow_config.name}</div>
      </div>
      <div
        ref={messageBoxInputRef}
        className="flex h-full     flex-col rounded  scroll pr-2 overflow-auto  "
        style={{ minHeight: "300px", maxHeight: chatMaxHeight }}
      >
        <div className="scroll-gradient h-10">
          {" "}
          <span className="  inline-block h-6"></span>{" "}
        </div>
        <div className="flex-1  boder mt-4"></div>
        {!messages && messages !== null && (
          <div className="w-full text-center boder mt-4">
            <div>
              {" "}
              <BounceLoader />
            </div>
            loading messages
          </div>
        )}

        {messages && messages?.length === 0 && (
          <div className="ml-2 text-sm text-secondary ">
            <InformationCircleIcon className="inline-block h-6 mr-2" />
            No messages in the current session. Start a conversation to begin.
          </div>
        )}
        <div className="ml-2"> {messageListView}</div>
        <div className="ml-2 h-6   mb-4 mt-2   ">
          {loading && <BounceLoader />}
        </div>
      </div>
      {editable && (
        <div className="mt-2 p-2 absolute   bg-primary  bottom-0 w-full">
          <div
            className={`rounded p-2 shadow-lg flex mb-1  gap-2 ${
              loading ? " opacity-50 pointer-events-none" : ""
            }`}
          >
            {/* <input className="flex-1 p-2 ring-2" /> */}
            <form
              autoComplete="on"
              className="flex-1 relative"
              onSubmit={(e) => {
                e.preventDefault();
              }}
            >
              <textarea
                id="queryInput"
                name="queryInput"
                autoComplete="on"
                onKeyDown={handleKeyDown}
                onChange={handleTextChange}
                placeholder="Write message here..."
                ref={textAreaInputRef}
                className="flex items-center w-full resize-none text-gray-600 bg-white p-2 ring-2 rounded-sm pl-5 pr-16"
                style={{ maxHeight: "120px", overflowY: "auto" }}
              />
              <div
                role={"button"}
                style={{ width: "45px", height: "35px" }}
                title="Send message"
                onClick={() => {
                  if (textAreaInputRef.current && !loading) {
                    getCompletion(textAreaInputRef.current.value);
                  }
                }}
                className="absolute right-3 bottom-2 bg-accent hover:brightness-75 transition duration-300 rounded cursor-pointer flex justify-center items-center"
              >
                {" "}
                {!loading && (
                  <div className="inline-block  ">
                    <PaperAirplaneIcon className="h-6 w-6 text-white " />{" "}
                  </div>
                )}
                {loading && (
                  <div className="inline-block   ">
                    <Cog6ToothIcon className="text-white animate-spin rounded-full h-6 w-6" />
                  </div>
                )}
              </div>
            </form>
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
      )}
    </div>
  );
};
export default ChatBox;
