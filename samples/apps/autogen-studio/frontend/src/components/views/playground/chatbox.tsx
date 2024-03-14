import {
  ArrowPathIcon,
  Cog6ToothIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PaperAirplaneIcon,
} from "@heroicons/react/24/outline";
import {
  Button,
  Dropdown,
  MenuProps,
  message as ToastMessage,
  Tooltip,
} from "antd";
import * as React from "react";
import {
  IChatMessage,
  IChatSession,
  IFlowConfig,
  IMessage,
  IStatus,
} from "../../types";
import { examplePrompts, getServerUrl, guid } from "../../utils";
import { appContext } from "../../../hooks/provider";
import MetaDataView from "./metadata";
import {
  AgentRow,
  BounceLoader,
  CollapseBox,
  LoadingBar,
  MarkdownView,
} from "../../atoms";
import { useConfigStore } from "../../../hooks/store";

let socketMsgs: any[] = [];
const ChatBox = ({
  initMessages,
  editable = true,
  connectionId,
}: {
  initMessages: IMessage[] | null;
  editable?: boolean;
  connectionId: string;
}) => {
  const session: IChatSession | null = useConfigStore((state) => state.session);
  const textAreaInputRef = React.useRef<HTMLTextAreaElement>(null);
  const messageBoxInputRef = React.useRef<HTMLDivElement>(null);
  const { user } = React.useContext(appContext);
  const wsClient = React.useRef<WebSocket | null>(null);
  const [wsConnectionStatus, setWsConnectionStatus] =
    React.useState<string>("disconnected");

  const [socketMessages, setSocketMessages] = React.useState<any[]>([]);

  const MAX_RETRIES = 10;
  const RETRY_INTERVAL = 2000;

  const [retries, setRetries] = React.useState(0);

  const serverUrl = getServerUrl();
  const deleteMsgUrl = `${serverUrl}/messages/delete`;

  let websocketUrl = serverUrl.replace("http", "ws") + "/ws/";

  // check if there is a protocol in the serverUrl e.g. /api. if use the page url
  if (!serverUrl.includes("http")) {
    const pageUrl = window.location.href;
    const url = new URL(pageUrl);
    const protocol = url.protocol;
    const host = url.host;
    const baseUrl = protocol + "//" + host + serverUrl;
    websocketUrl = baseUrl.replace("http", "ws") + "/ws/";
  } else {
    websocketUrl = serverUrl.replace("http", "ws") + "/ws/";
  }

  const [loading, setLoading] = React.useState(false);
  const [text, setText] = React.useState("");
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const socketDivRef = React.useRef<HTMLDivElement>(null);

  const messages = useConfigStore((state) => state.messages);
  const setMessages = useConfigStore((state) => state.setMessages);
  const workflowConfig: IFlowConfig | null = useConfigStore(
    (state) => state.workflowConfig
  );

  let pageHeight, chatMaxHeight;
  if (typeof window !== "undefined") {
    pageHeight = window.innerHeight;
    chatMaxHeight = pageHeight - 310 + "px";
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
    socketMsgs = [];
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
      items.push({
        label: (
          <div
            onClick={() => {
              // copy to clipboard
              navigator.clipboard.writeText(message.text);
              ToastMessage.success("Message copied to clipboard");
            }}
          >
            <DocumentDuplicateIcon
              role={"button"}
              title={"Copy"}
              className="h-4 w-4 mr-1 inline-block"
            />
            Copy
          </div>
        ),
        key: "copymessage",
      });
    }

    const menu = (
      <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
        <div
          role="button"
          className="float-right ml-2 duration-100 hover:bg-secondary font-semibold px-2 pb-1  rounded"
        >
          <span className="block -mt-2 text-primary  "> ...</span>
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
          <div className=""></div>
          <div className="font-semibold text-secondary text-sm w-16">{`${
            isUser ? "USER" : "AGENTS"
          }`}</div>
          <div
            className={`inline-block group relative w-full p-2 rounded  ${css}`}
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
      scrollChatBox(messageBoxInputRef);
    }, 500);
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

  const [waitingToReconnect, setWaitingToReconnect] = React.useState<
    boolean | null
  >(null);

  React.useEffect(() => {
    if (waitingToReconnect) {
      return;
    }
    // Only set up the websocket once
    const socketUrl = websocketUrl + connectionId;
    console.log("socketUrl", socketUrl);
    if (!wsClient.current) {
      const client = new WebSocket(socketUrl);
      wsClient.current = client;
      client.onerror = (e) => {
        console.log("ws error", e);
      };

      client.onopen = () => {
        setWsConnectionStatus("connected");
        console.log("ws opened");
      };

      client.onclose = () => {
        if (wsClient.current) {
          // Connection failed
          console.log("ws closed by server");
        } else {
          // Cleanup initiated from app side, can return here, to not attempt a reconnect
          return;
        }

        if (waitingToReconnect) {
          return;
        }

        // Parse event code and log
        setWsConnectionStatus("disconnected");

        setWaitingToReconnect(true);
        setWsConnectionStatus("reconnecting");
        setTimeout(() => {
          setWaitingToReconnect(null);
        }, RETRY_INTERVAL);
      };

      client.onmessage = (message) => {
        const data = JSON.parse(message.data);
        console.log("received message", data);
        if (data && data.type === "agent_message") {
          // indicates an intermediate agent message update
          const newsocketMessages = Object.assign([], socketMessages);
          newsocketMessages.push(data.data);
          setSocketMessages(newsocketMessages);
          socketMsgs.push(data.data);
          setTimeout(() => {
            scrollChatBox(socketDivRef);
            scrollChatBox(messageBoxInputRef);
          }, 200);
          // console.log("received message", data, socketMsgs.length);
        } else if (data && data.type === "agent_status") {
          // indicates a status message update
          const agentStatusSpan = document.getElementById("agentstatusspan");
          if (agentStatusSpan) {
            agentStatusSpan.innerHTML = data.data.message;
          }
        } else if (data && data.type === "agent_response") {
          // indicates a final agent response
          processAgentResponse(data.data);
        }
      };

      return () => {
        console.log("Cleanup");
        // Dereference, so it will set up next time
        wsClient.current = null;
        client.close();
      };
    }
  }, [waitingToReconnect]);

  const chatHistory = (messages: IChatMessage[] | null) => {
    let history = "";
    messages?.forEach((message) => {
      history += message.text + "\n"; // message.sender + ": " + message.text + "\n";
    });
    return history;
  };

  const scrollChatBox = (element: any) => {
    element.current?.scroll({
      top: element.current.scrollHeight,
      behavior: "smooth",
    });
  };

  const processAgentResponse = (data: any) => {
    if (data && data.status) {
      const updatedMessages = parseMessages(data.data);
      setTimeout(() => {
        setLoading(false);
        setMessages(updatedMessages);
      }, 2000);
    } else {
      console.log("error", data);
      // setError(data);
      ToastMessage.error(data.message);
      setLoading(false);
    }
  };

  const getCompletion = (query: string) => {
    setError(null);
    socketMsgs = [];
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
    const postBody = {
      message: messagePayload,
      workflow: workflowConfig,
      session: session,
      user_id: user?.email,
      connection_id: connectionId,
    };
    const postData = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(postBody),
    };
    setLoading(true);

    // check if socket connected, send on socket
    // else send on fetch
    if (wsClient.current && wsClient.current.readyState === 1) {
      wsClient.current.send(
        JSON.stringify({
          connection_id: connectionId,
          data: postBody,
          type: "user_message",
        })
      );
      console.log("sending on socket ..");
    } else {
      fetch(textUrl, postData)
        .then((res) => {
          if (res.status === 200) {
            res.json().then((data) => {
              processAgentResponse(data);
            });
          } else {
            res.json().then((data) => {
              console.log("error", data);
              ToastMessage.error(data.message);
              setLoading(false);
            });
            ToastMessage.error(
              "Connection error. Ensure server is up and running."
            );
          }
        })
        .catch(() => {
          setLoading(false);

          ToastMessage.error(
            "Connection error. Ensure server is up and running."
          );
        })
        .finally(() => {
          setTimeout(() => {
            scrollChatBox(messageBoxInputRef);
          }, 500);
        });
    }
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

  const getConnectionColor = (status: string) => {
    if (status === "connected") {
      return "bg-green-500";
    } else if (status === "reconnecting") {
      return "bg-orange-500";
    } else if (status === "disconnected") {
      return "bg-red-500";
    }
  };

  return (
    <div
      style={{ height: "calc(100vh - 160px)" }}
      className="text-primary    relative  h-full rounded  "
    >
      <div
        style={{ zIndex: 100 }}
        className=" absolute right-0  text-secondary -top-8 rounded p-2"
      >
        {" "}
        <div className="text-xs"> {session?.flow_config.name}</div>
      </div>

      <div
        ref={messageBoxInputRef}
        className="flex h-full  flex-col rounded  scroll pr-2 overflow-auto  "
        style={{ minHeight: "30px", height: "calc(100vh - 310px)" }}
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

        {loading && (
          <div className={` inline-flex gap-2 duration-300 `}>
            <div className=""></div>
            <div className="font-semibold text-secondary text-sm w-16">
              AGENTS
            </div>
            <div className="relative w-full  ">
              <div className="mb-2  ">
                <LoadingBar>
                  <div className="mb-1  inline-block ml-2 text-xs text-secondary">
                    <span className="innline-block text-sm ml-2">
                      {" "}
                      <span id="agentstatusspan">
                        {" "}
                        agents working on task ..
                      </span>
                    </span>{" "}
                    {socketMsgs.length > 0 && (
                      <span className="border-l inline-block text-right ml-2 pl-2">
                        {socketMsgs.length} agent message
                        {socketMsgs.length > 1 && "s"} sent/received.
                      </span>
                    )}
                  </div>
                </LoadingBar>
              </div>

              {socketMsgs.length > 0 && (
                <div
                  ref={socketDivRef}
                  style={{
                    minHeight: "300px",
                    maxHeight: "400px",
                    overflowY: "auto",
                  }}
                  className={`inline-block scroll group relative   p-2 rounded w-full bg-light `}
                >
                  <CollapseBox
                    open={true}
                    title={`Agent Messages (${socketMsgs.length} message${
                      socketMsgs.length > 1 ? "s" : ""
                    }) `}
                  >
                    {socketMsgs?.map((message: any, i: number) => {
                      return (
                        <div key={i}>
                          <AgentRow message={message} />
                        </div>
                      );
                    })}
                  </CollapseBox>
                </div>
              )}
            </div>
          </div>
        )}
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
              <Tooltip title={`Socket ${wsConnectionStatus}`}>
                <div
                  className={`w-1 h-3 rounded  inline-block mr-1 ${getConnectionColor(
                    wsConnectionStatus
                  )}`}
                ></div>{" "}
              </Tooltip>
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
            <div className="p-2   rounded mt-4 text-orange-500 text-sm">
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
