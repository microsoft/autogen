import * as React from "react";
import { message } from "antd";
import { getServerUrl } from "../../../utils";
import { SessionManager } from "../../shared/session/manager";
import { IStatus } from "../../../types/app";
import { Message } from "../../../types/datamodel";
import { useConfigStore } from "../../../../hooks/store";
import { appContext } from "../../../../hooks/provider";
import ChatInput from "./chatinput";
import { SocketMessage, ThreadState } from "./types";
import { MessageList } from "./messagelist";
import TeamManager from "../../shared/team/manager";

const logo = require("../../../../images/landing/welcome.svg").default;
export default function ChatView({
  initMessages,
}: {
  initMessages: Message[];
}) {
  const serverUrl = getServerUrl();
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });
  const [messages, setMessages] = React.useState<Message[]>(initMessages);
  const [threadMessages, setThreadMessages] = React.useState<
    Record<string, ThreadState>
  >({});
  const chatContainerRef = React.useRef<HTMLDivElement>(null);

  const { user } = React.useContext(appContext);
  const { session, sessions } = useConfigStore();
  const [activeSockets, setActiveSockets] = React.useState<
    Record<string, WebSocket>
  >({});

  // Add scroll effect when messages change
  React.useEffect(() => {
    console.log("scrolling ...");
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, threadMessages]);

  // ... (keeping the utility functions: getBaseUrl)

  React.useEffect(() => {
    return () => {
      Object.values(activeSockets).forEach((socket) => socket.close());
    };
  }, [activeSockets]);

  const getBaseUrl = (url: string): string => {
    try {
      return url
        .replace(/(^\w+:|^)\/\//, "") // Remove protocol (http:// or https://)
        .replace("/api", "") // Remove /api
        .replace(/\/$/, ""); // Remove trailing slash
    } catch (error) {
      console.error("Error processing server URL:", error);
      throw new Error("Invalid server URL configuration");
    }
  };

  const createRun = async (sessionId: number): Promise<string> => {
    const payload = { session_id: sessionId, user_id: user?.email || "" };

    const response = await fetch(`${serverUrl}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error("Failed to create run");
    }

    const data = await response.json();
    return data.data.run_id;
  };

  const startRun = async (runId: string, query: string) => {
    const messagePayload = {
      user_id: user?.email,
      session_id: session?.id,
      config: {
        content: query,
        source: "user",
      },
    };

    const response = await fetch(`${serverUrl}/runs/${runId}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(messagePayload),
    });

    if (!response.ok) {
      throw new Error("Failed to start run");
    }

    return await response.json();
  };

  interface RequestUsage {
    prompt_tokens: number;
    completion_tokens: number;
  }

  const connectWebSocket = async (runId: string) => {
    const baseUrl = getBaseUrl(serverUrl);
    const wsUrl = `ws://${baseUrl}/api/ws/runs/${runId}`;
    const socket = new WebSocket(wsUrl);
    let isClosing = false; // Track closure state

    const closeSocket = () => {
      if (!isClosing && socket.readyState !== WebSocket.CLOSED) {
        isClosing = true;
        socket.close();
        setActiveSockets((prev) => {
          const newSockets = { ...prev };
          delete newSockets[runId];
          return newSockets;
        });
      }
    };

    socket.onopen = () => {
      setActiveSockets((prev) => ({
        ...prev,
        [runId]: socket,
      }));

      // Initialize thread state
      setThreadMessages((prev) => ({
        ...prev,
        [runId]: {
          messages: [],
          status: "streaming",
          isExpanded: true,
        },
      }));

      // Initial bot message with proper typing
      setMessages((prev: Message[]) =>
        prev.map((msg: Message) => {
          if (msg.run_id === runId && msg.config.source === "bot") {
            return {
              ...msg,
              config: {
                ...msg.config,
                content: "Starting...",
              },
            };
          }
          return msg;
        })
      );
    };

    socket.onmessage = (event) => {
      const message: SocketMessage = JSON.parse(event.data);

      switch (message.type) {
        case "message":
          // Add new message to thread while preserving existing ones
          setThreadMessages((prev) => {
            const currentThread = prev[runId] || {
              messages: [],
              status: "streaming",
              isExpanded: true,
            };

            if (message.data?.content === "TERMINATE") {
              return prev;
            }

            const models_usage: RequestUsage | undefined = message.data
              ?.models_usage
              ? {
                  prompt_tokens: message.data.models_usage.prompt_tokens,
                  completion_tokens:
                    message.data.models_usage.completion_tokens,
                }
              : undefined;

            const newMessage = {
              source: message.data?.source || "",
              content: message.data?.content || "",
              models_usage,
            };

            return {
              ...prev,
              [runId]: {
                ...currentThread,
                messages: [...currentThread.messages, newMessage],
                status: "streaming",
              },
            };
          });
          break;

        case "result":
        case "completion":
          setThreadMessages((prev) => {
            const currentThread = prev[runId];
            if (!currentThread) return prev;

            const finalMessage = message.data?.task_result?.messages
              ?.filter((msg: any) => msg.content !== "TERMINATE")
              .pop();

            return {
              ...prev,
              [runId]: {
                ...currentThread,
                status: "complete",
                isExpanded: true,
                finalResult: finalMessage,
                messages: currentThread.messages,
              },
            };
          });

          // Update final bot message content
          const finalMessage = message.data?.task_result?.messages
            ?.filter((msg: any) => msg.content !== "TERMINATE")
            .pop();

          if (finalMessage) {
            setMessages((prev: Message[]) =>
              prev.map((msg: Message) => {
                if (msg.run_id === runId && msg.config.source === "bot") {
                  const models_usage: RequestUsage | undefined =
                    finalMessage.models_usage
                      ? {
                          prompt_tokens:
                            finalMessage.models_usage.prompt_tokens,
                          completion_tokens:
                            finalMessage.models_usage.completion_tokens,
                        }
                      : undefined;

                  return {
                    ...msg,
                    config: {
                      ...msg.config,
                      content: finalMessage.content,
                      models_usage,
                    },
                  };
                }
                return msg;
              })
            );
          }
          closeSocket();
          break;
      }
    };

    socket.onclose = (event) => {
      console.log(
        `WebSocket closed for run ${runId}. Code: ${event.code}, Reason: ${event.reason}`
      );

      // Only update states if we haven't already done so
      if (!isClosing) {
        setActiveSockets((prev) => {
          const newSockets = { ...prev };
          delete newSockets[runId];
          return newSockets;
        });

        setThreadMessages((prev) => {
          const thread = prev[runId];
          if (thread && thread.status === "streaming") {
            return {
              ...prev,
              [runId]: {
                ...thread,
                status: "complete",
              },
            };
          }
          return prev;
        });
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      message.error("WebSocket connection error");

      setThreadMessages((prev) => {
        const thread = prev[runId];
        if (!thread) return prev;

        return {
          ...prev,
          [runId]: {
            ...thread,
            status: "error",
            isExpanded: true,
          },
        };
      });

      closeSocket();
    };

    return socket;
  };

  const cancelRun = async (runId: string) => {
    console.log("cancel run", runId);
    const socket = activeSockets[runId];
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "stop" }));

      // Update thread status to cancelled
      setThreadMessages((prev) => ({
        ...prev,
        [runId]: {
          ...prev[runId],
          status: "cancelled",
          isExpanded: true, // Keep expanded when cancelled
        },
      }));
    }
  };

  const runTask = async (query: string) => {
    setError(null);
    setLoading(true);

    if (!session?.id) {
      setLoading(false);
      return;
    }

    let runId: string | null = null;

    try {
      runId = (await createRun(session.id)) + "";

      const userMessage: Message = {
        config: {
          content: query,
          source: "user",
        },
        session_id: session.id,
        run_id: runId,
      };

      const botMessage: Message = {
        config: {
          content: "Thinking...",
          source: "bot",
        },
        session_id: session.id,
        run_id: runId,
      };

      setMessages((prev) => [...prev, userMessage, botMessage]);
      await connectWebSocket(runId);
      await startRun(runId, query);
    } catch (err) {
      console.error("Error:", err);
      message.error("Error during request processing");

      if (runId) {
        if (activeSockets[runId]) {
          activeSockets[runId].close();
        }

        if (runId) {
          // Type guard to ensure runId is not null
          setThreadMessages((prev) => ({
            ...prev,
            [runId]: {
              ...prev[runId],
              status: "error",
              isExpanded: true,
            },
          }));
        }
      }

      setError({
        status: false,
        message: err instanceof Error ? err.message : "Unknown error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-primary h-[calc(100vh-180px)]  bg-primary relative rounded flex-1 scroll">
      <div className="  flex gap-4 w-full">
        <div className="flex-1">
          {" "}
          <SessionManager />
        </div>
        <TeamManager />
      </div>
      <div className="flex flex-col h-full">
        <div
          className="flex-1  overflow-y-auto scroll relative min-h-0"
          ref={chatContainerRef}
        >
          <MessageList
            messages={messages}
            threadMessages={threadMessages}
            setThreadMessages={setThreadMessages}
            onRetry={runTask}
            onCancel={cancelRun}
            loading={loading}
          />
        </div>

        {sessions?.length === 0 ? (
          <div className="flex  h-[calc(100%-100px)]  flex-col items-center justify-center w-full  ">
            <div className="mt-4 text-sm text-secondary text-center">
              <img src={logo} alt="Welcome" className="w-72 h-72 mb-4" />
              Welcome! Create a session to get started!
            </div>
          </div>
        ) : (
          // Chat input stays at bottom, outside scroll area
          <>
            {session && (
              <div className="flex-shrink-0">
                <ChatInput onSubmit={runTask} loading={loading} error={error} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
