import {
  ArrowPathIcon,
  ChatBubbleLeftRightIcon,
  Cog6ToothIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PaperAirplaneIcon,
  SignalSlashIcon,
} from "@heroicons/react/24/outline";
import {
  Button,
  Dropdown,
  MenuProps,
  Tabs,
  message as ToastMessage,
  Tooltip,
  message,
} from "antd";
import * as React from "react";
import {
  IChatMessage,
  IChatSession,
  IMessage,
  IStatus,
  IWorkflow,
} from "../../types";
import { examplePrompts, fetchJSON, getServerUrl, guid } from "../../utils";
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
import ProfilerView from "./utils/profiler";

let socketMsgs: any[] = [];

const ChatBox = ({
  initMessages,
  session,
  editable = true,
  heightOffset = 160,
}: {
  initMessages: IMessage[] | null;
  session: IChatSession | null;
  editable?: boolean;
  heightOffset?: number;
}) => {
  // const session: IChatSession | null = useConfigStore((state) => state.session);
  const textAreaInputRef = React.useRef<HTMLTextAreaElement>(null);
  const messageBoxInputRef = React.useRef<HTMLDivElement>(null);
  const { user } = React.useContext(appContext);
  const wsClient = React.useRef<WebSocket | null>(null);
  const wsMessages = React.useRef<IChatMessage[]>([]);
  const [wsConnectionStatus, setWsConnectionStatus] =
    React.useState<string>("disconnected");
  const [workflow, setWorkflow] = React.useState<IWorkflow | null>(null);

  const [socketMessages, setSocketMessages] = React.useState<any[]>([]);
  const [awaitingUserInput, setAwaitingUserInput] = React.useState(false); // New state for tracking user input
  const setAreSessionButtonsDisabled = useConfigStore(
    (state) => state.setAreSessionButtonsDisabled
  );

  const MAX_RETRIES = 10;
  const RETRY_INTERVAL = 2000;

  const [retries, setRetries] = React.useState(0);

  const serverUrl = getServerUrl();

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
  const connectionId = useConfigStore((state) => state.connectionId);

  const messages = useConfigStore((state) => state.messages);
  const setMessages = useConfigStore((state) => state.setMessages);

  const parseMessage = (message: IMessage) => {
    let meta;
    try {
      meta = JSON.parse(message.meta);
    } catch (e) {
      meta = message?.meta;
    }
    const msg: IChatMessage = {
      text: message.content,
      sender: message.role === "user" ? "user" : "bot",
      meta: meta,
      id: message.id,
    };
    return msg;
  };

  const parseMessages = (messages: any) => {
    return messages?.map(parseMessage);
  };

  React.useEffect(() => {
    // console.log("initMessages changed", initMessages);
    const initMsgs: IChatMessage[] = parseMessages(initMessages);
    setMessages(initMsgs);
    wsMessages.current = initMsgs;
  }, [initMessages]);

  const promptButtons = examplePrompts.map((prompt, i) => {
    return (
      <Button
        key={"prompt" + i}
        type="primary"
        className=""
        onClick={() => {
          runWorkflow(prompt.prompt);
        }}
      >
        {" "}
        {prompt.title}{" "}
      </Button>
    );
  });

  const messageListView = messages && messages?.map((message: IChatMessage, i: number) => {
    const isUser = message.sender === "user";
    const css = isUser ? "bg-accent text-white  " : "bg-light";
    // console.log("message", message);
    let hasMeta = false;
    if (message.meta) {
      hasMeta =
        message.meta.code !== null ||
        message.meta.images?.length > 0 ||
        message.meta.files?.length > 0 ||
        message.meta.scripts?.length > 0;
    }

    let items: MenuProps["items"] = [];

    if (isUser) {
      items.push({
        label: (
          <div
            onClick={() => {
              console.log("retrying");
              runWorkflow(message.text);
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
        id={"message" + i} className={`align-right ${isUser ? "text-righpt" : ""}  mb-2 border-b`}
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
            {message.meta && !isUser && (
              <>
                {" "}
                <Tabs
                  defaultActiveKey="1"
                  items={[
                    {
                      label: (
                        <>
                          {" "}
                          <ChatBubbleLeftRightIcon className="h-4 w-4 inline-block mr-1" />
                          Agent Messages
                        </>
                      ),
                      key: "1",
                      children: (
                        <div className="text-primary">
                          <MetaDataView metadata={message.meta} />
                        </div>
                      ),
                    },
                    {
                      label: (
                        <div>
                          {" "}
                          <SignalSlashIcon className="h-4 w-4 inline-block mr-1" />{" "}
                          Profiler
                        </div>
                      ),
                      key: "2",
                      children: (
                        <div className="text-primary">
                          <ProfilerView agentMessage={message} />
                        </div>
                      ),
                    },
                  ]}
                />
              </>
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

  const textAreaDefaultHeight = "64px";
  // clear text box if loading has just changed to false and there is no error
  React.useEffect(() => {
    if ((awaitingUserInput || loading === false) && textAreaInputRef.current) {
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
        } else if (data && data.type === "user_input_request") {
          setAwaitingUserInput(true); // Set awaiting input state
          textAreaInputRef.current.value = ""
          textAreaInputRef.current.placeholder = data.data.message.content
          const newsocketMessages = Object.assign([], socketMessages);
          newsocketMessages.push(data.data);
          setSocketMessages(newsocketMessages);
          socketMsgs.push(data.data);
          setTimeout(() => {
            scrollChatBox(socketDivRef);
            scrollChatBox(messageBoxInputRef);
          }, 200);
          ToastMessage.info(data.data.message)
        } else if (data && data.type === "agent_status") {
          // indicates a status message update
          const agentStatusSpan = document.getElementById("agentstatusspan");
          if (agentStatusSpan) {
            agentStatusSpan.innerHTML = data.data.message;
          }
        } else if (data && data.type === "agent_response") {
          // indicates a final agent response
          setAwaitingUserInput(false); // Set awaiting input state
          setAreSessionButtonsDisabled(false);
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

  const scrollChatBox = (element: any) => {
    element.current?.scroll({
      top: element.current.scrollHeight,
      behavior: "smooth",
    });
  };

  const mainDivRef = React.useRef<HTMLDivElement>(null);

  const processAgentResponse = (data: any) => {
    if (data && data.status) {
      const msg = parseMessage(data.data);
      wsMessages.current.push(msg);
      setMessages(wsMessages.current);
      setLoading(false);
      setAwaitingUserInput(false);
    } else {
      console.log("error", data);
      // setError(data);
      ToastMessage.error(data.message);
      setLoading(false);
      setAwaitingUserInput(false);
    }
  };

  const fetchWorkFlow = (workflowId: number) => {
    const fetchUrl = `${serverUrl}/workflows/${workflowId}?user_id=${user?.email}`;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const onSuccess = (data: any) => {
      if (data && data.status) {
        if (data.data && data.data.length > 0) {
          setWorkflow(data.data[0]);
        }
      } else {
        message.error(data.message);
      }
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
    };
    fetchJSON(fetchUrl, payLoad, onSuccess, onError);
  };

  const runWorkflow = (query: string) => {
    setError(null);
    setAreSessionButtonsDisabled(true);
    socketMsgs = [];
    let messageHolder = Object.assign([], messages);

    const userMessage: IChatMessage = {
      text: query,
      sender: "user",
    };
    messageHolder.push(userMessage);
    setMessages(messageHolder);
    wsMessages.current.push(userMessage);

    const messagePayload: IMessage = {
      role: "user",
      content: query,
      user_id: user?.email || "",
      session_id: session?.id,
      workflow_id: session?.workflow_id,
      connection_id: connectionId,
    };

    const runWorkflowUrl = `${serverUrl}/sessions/${session?.id}/workflow/${session?.workflow_id}/run`;

    const postData = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(messagePayload),
    };
    setLoading(true);

    // check if socket connected, send on socket
    // else send on fetch
    if (wsClient.current && wsClient.current.readyState === 1) {
      wsClient.current.send(
        JSON.stringify({
          connection_id: connectionId,
          data: messagePayload,
          type: "user_message",
          session_id: session?.id,
          workflow_id: session?.workflow_id,
        })
      );
    } else {
      fetch(runWorkflowUrl, postData)
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

  const sendUserResponse = (userResponse: string) => {
    setAwaitingUserInput(false);
    setError(null);
    setLoading(true);

    textAreaInputRef.current.placeholder = "Write message here..."

    const userMessage: IChatMessage = {
      text: userResponse,
      sender: "system",
    };

    const messagePayload: IMessage = {
      role: "user",
      content: userResponse,
      user_id: user?.email || "",
      session_id: session?.id,
      workflow_id: session?.workflow_id,
      connection_id: connectionId,
    };

    // check if socket connected,
    if (wsClient.current && wsClient.current.readyState === 1) {
      wsClient.current.send(
        JSON.stringify({
          connection_id: connectionId,
          data: messagePayload,
          type: "user_message",
          session_id: session?.id,
          workflow_id: session?.workflow_id,
        })
      );
    } else {
        console.err("websocket client error")
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
      if (textAreaInputRef.current &&(awaitingUserInput || !loading)) {
        event.preventDefault();
        if (awaitingUserInput) {
          sendUserResponse(textAreaInputRef.current.value); // New function call for sending user input
          textAreaInputRef.current.value = "";
        } else {
          runWorkflow(textAreaInputRef.current.value);
        }
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

  React.useEffect(() => {
    if (session && session.workflow_id) {
      fetchWorkFlow(session.workflow_id);
    }
  }, [session]);

  const WorkflowView = ({ workflow }: { workflow: IWorkflow }) => {
    return (
      <div id="workflow-view" className="text-xs cursor-pointer  inline-block">
        {" "}
        {workflow.name}
      </div>
    );
  };

  return (
    <div
      id="chatbox-main"
      style={{ height: "calc(100vh - " + heightOffset + "px)" }}
      className="text-primary    relative   rounded  "
      ref={mainDivRef}
    >
      <div
        id="workflow-name"
        style={{ zIndex: 100 }}
        className=" absolute right-3 bg-primary   rounded  text-secondary -top-6  p-2"
      >
        {" "}
        {workflow && <div className="text-xs"> {workflow.name}</div>}
      </div>

      <div
        id="message-box"
        ref={messageBoxInputRef}
        className="flex h-full  flex-col rounded  scroll pr-2 overflow-auto  "
        style={{ minHeight: "30px", height: "calc(100vh - 310px)" }}
      >
        <div id="scroll-gradient" className="scroll-gradient h-10">
          {" "}
          <span className="  inline-block h-6"></span>{" "}
        </div>
        <div className="flex-1  boder mt-4"></div>
        {!messages && messages !== null && (
          <div id="loading-messages" className="w-full text-center boder mt-4">
            <div>
              {" "}
              <BounceLoader />
            </div>
            loading messages
          </div>
        )}

        {messages && messages?.length === 0 && (
          <div id="no-messages" className="ml-2 text-sm text-secondary ">
            <InformationCircleIcon className="inline-block h-6 mr-2" />
            No messages in the current session. Start a conversation to begin.
          </div>
        )}

        <div id="message-list" className="ml-2"> {messageListView}</div>
        {(loading || awaitingUserInput) && (
          <div id="loading-bar" className={` inline-flex gap-2 duration-300 `}>
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
                  id="agent-messages"
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
        <div id="input-area" className="mt-2 p-2 absolute   bg-primary  bottom-0 w-full">
          <div
            id="input-form"
            className={`rounded p-2 shadow-lg flex mb-1  gap-2 ${
              loading && !awaitingUserInput ? " opacity-50 pointer-events-none" : ""
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
                className="flex items-center w-full resize-none text-gray-600 bg-white p-2 ring-2 rounded-sm pl-5 pr-16 h-64"
                style={{
                  maxHeight: "120px",
                  overflowY: "auto",
                  minHeight: "50px",
                }}
              />
              <div
                id="send-button"
                role={"button"}
                style={{ width: "45px", height: "35px" }}
                title="Send message"
                onClick={() => {
                  if (textAreaInputRef.current && (awaitingUserInput || !loading)) {
                    if (awaitingUserInput) {
                      sendUserResponse(textAreaInputRef.current.value); // Use the new function for user input
                    } else {
                      runWorkflow(textAreaInputRef.current.value);
                    }
                  }
                }}
                className="absolute right-3 bottom-2 bg-accent hover:brightness-75 transition duration-300 rounded cursor-pointer flex justify-center items-center"
              >
                {" "}
                {(awaitingUserInput || !loading) && (
                  <div className="inline-block  ">
                    <PaperAirplaneIcon className="h-6 w-6 text-white " />{" "}
                  </div>
                )}
                {loading && !awaitingUserInput && (
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
              id="prompt-buttons"
              className={`mt-2 inline-flex gap-2 flex-wrap  ${
                (loading && !awaitingUserInput) ? "brightness-75 pointer-events-none" : ""
              }`}
            >
              {promptButtons}
            </div>
          </div>
          {error && !error.status && (
            <div id="error-message" className="p-2   rounded mt-4 text-orange-500 text-sm">
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
