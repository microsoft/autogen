import * as React from "react";
import { message } from "antd";
import { getServerUrl } from "../../../utils";
import { SessionManager } from "../../shared/session/manager";
import { IStatus } from "../../../types/app";
import {
  Message,
  ThreadStatus,
  WebSocketMessage,
} from "../../../types/datamodel";
import { useConfigStore } from "../../../../hooks/store";
import { appContext } from "../../../../hooks/provider";
import ChatInput from "./chatinput";
import { ModelUsage, ThreadState, TIMEOUT_CONFIG } from "./types";
import { MessageList } from "./messagelist";
import TeamManager from "../../shared/team/manager";
import { teamAPI } from "../../shared/team/api";

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
  const timeoutRefs = React.useRef<Record<string, NodeJS.Timeout>>({});

  const { user } = React.useContext(appContext);
  const { session, sessions } = useConfigStore();
  const [activeSockets, setActiveSockets] = React.useState<
    Record<string, WebSocket>
  >({});
  const activeSocketsRef = React.useRef<Record<string, WebSocket>>({});

  const [teamConfig, setTeamConfig] = React.useState<any>(null);

  React.useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, threadMessages]);

  React.useEffect(() => {
    if (session && session.team_id && user && user.email) {
      teamAPI.getTeam(session.team_id, user?.email).then((team) => {
        setTeamConfig(team.config);
        // console.log("Team Config", team.config);
      });
    }
  }, [session]);

  const updateSocket = (runId: string, socket: WebSocket | null) => {
    if (socket) {
      activeSocketsRef.current[runId] = socket;
      setActiveSockets((prev) => ({ ...prev, [runId]: socket }));
    } else {
      delete activeSocketsRef.current[runId];
      setActiveSockets((prev) => {
        const next = { ...prev };
        delete next[runId];
        return next;
      });
    }
  };

  React.useEffect(() => {
    return () => {
      Object.values(activeSockets).forEach((socket) => socket.close());
    };
  }, [activeSockets]);

  const handleTimeoutForRun = (runId: string) => {
    const socket = activeSocketsRef.current[runId];
    if (socket && socket.readyState === WebSocket.OPEN) {
      // Send stop message to backend, just like when user clicks stop
      socket.send(
        JSON.stringify({
          type: "stop",
          reason: TIMEOUT_CONFIG.DEFAULT_MESSAGE,
        })
      );
    }

    // Update thread state with timeout reason
    setThreadMessages((prev) => {
      const currentThread = prev[runId];
      if (!currentThread) return prev;

      return {
        ...prev,
        [runId]: {
          ...currentThread,
          status: "cancelled", // Use existing cancelled status
          reason: "Input request timed out after 3 minutes",
          isExpanded: true,
          inputRequest: currentThread.inputRequest
            ? {
                prompt: currentThread.inputRequest.prompt,
                isPending: true,
              }
            : undefined,
        },
      };
    });

    if (timeoutRefs.current[runId]) {
      clearTimeout(timeoutRefs.current[runId]);
      delete timeoutRefs.current[runId];
    }
  };

  const handleInputResponse = async (runId: string, response: string) => {
    // Clear timeout when response is received
    if (timeoutRefs.current[runId]) {
      clearTimeout(timeoutRefs.current[runId]);
      delete timeoutRefs.current[runId];
    }

    if (response === "TIMEOUT") {
      handleTimeoutForRun(runId);
      return;
    }

    const socket = activeSockets[runId];
    if (socket && socket.readyState === WebSocket.OPEN) {
      try {
        socket.send(
          JSON.stringify({
            type: "input_response",
            response: response,
          })
        );

        setThreadMessages((prev) => ({
          ...prev,
          [runId]: {
            ...prev[runId],
            status: "streaming",
            inputRequest: undefined,
          },
        }));
      } catch (error) {
        console.error("Error sending input response:", error);
        message.error("Failed to send response");

        setThreadMessages((prev) => ({
          ...prev,
          [runId]: {
            ...prev[runId],
            status: "error",
            reason: "Failed to send input response",
          },
        }));
      }
    } else {
      message.error("Connection lost. Please try again.");
    }
  };

  const getBaseUrl = (url: string): string => {
    try {
      // Remove protocol (http:// or https://)
      let baseUrl = url.replace(/(^\w+:|^)\/\//, "");

      // Handle both localhost and production cases
      if (baseUrl.startsWith("localhost")) {
        // For localhost, keep the port if it exists
        baseUrl = baseUrl.replace("/api", "");
      } else if (baseUrl === "/api") {
        // For production where url is just '/api'
        baseUrl = window.location.host;
      } else {
        // For other cases, remove '/api' and trailing slash
        baseUrl = baseUrl.replace("/api", "").replace(/\/$/, "");
      }

      return baseUrl;
    } catch (error) {
      console.error("Error processing server URL:", error);
      throw new Error("Invalid server URL configuration");
    }
  };

  const createRun = async (sessionId: number): Promise<string> => {
    const payload = { session_id: sessionId, user_id: user?.email || "" };

    const response = await fetch(`${serverUrl}/runs/`, {
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

  const connectWebSocket = (runId: string, query: string) => {
    const baseUrl = getBaseUrl(serverUrl);
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${baseUrl}/api/ws/runs/${runId}`;

    const socket = new WebSocket(wsUrl);
    let isClosing = false;

    const clearTimeoutForRun = () => {
      if (timeoutRefs.current[runId]) {
        clearTimeout(timeoutRefs.current[runId]);
        delete timeoutRefs.current[runId];
      }
    };

    const closeSocket = () => {
      if (!isClosing && socket.readyState !== WebSocket.CLOSED) {
        isClosing = true;
        socket.close();
        updateSocket(runId, null);
      }
    };

    socket.onopen = async () => {
      try {
        updateSocket(runId, socket);

        setThreadMessages((prev) => ({
          ...prev,
          [runId]: {
            messages: [],
            status: "streaming",
            isExpanded: true,
          },
        }));

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

        await startRun(runId, query);
      } catch (error) {
        closeSocket();
        setThreadMessages((prev) => ({
          ...prev,
          [runId]: {
            ...prev[runId],
            status: "error",
            isExpanded: true,
          },
        }));
      }
    };

    socket.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);

      switch (message.type) {
        case "input_request":
          clearTimeoutForRun();

          timeoutRefs.current[runId] = setTimeout(() => {
            handleTimeoutForRun(runId);
          }, TIMEOUT_CONFIG.DURATION_MS);

          setThreadMessages((prev) => ({
            ...prev,
            [runId]: {
              ...prev[runId],
              status: "awaiting_input",
              inputRequest: {
                prompt: message.data?.content || "",
                isPending: false,
              },
            },
          }));
          break;

        case "message":
          clearTimeoutForRun();

          setThreadMessages((prev) => {
            const currentThread = prev[runId] || {
              messages: [],
              status: "streaming",
              isExpanded: true,
            };

            const models_usage: ModelUsage | undefined = message.data
              ?.models_usage
              ? {
                  prompt_tokens: message.data.models_usage.prompt_tokens,
                  completion_tokens:
                    message.data.models_usage.completion_tokens,
                }
              : undefined;

            return {
              ...prev,
              [runId]: {
                ...currentThread,
                messages: [
                  ...currentThread.messages,
                  {
                    source: message.data?.source || "",
                    content: message.data?.content || "",
                    models_usage,
                  },
                ],
                status: "streaming",
              },
            };
          });
          break;

        case "result":
        case "completion":
          clearTimeoutForRun();

          setThreadMessages((prev) => {
            const currentThread = prev[runId];
            if (!currentThread) return prev;

            const status: ThreadStatus = message.status || "complete";
            const reason =
              message.data?.task_result?.stop_reason ||
              (message.error ? `Error: ${message.error}` : undefined);

            return {
              ...prev,
              [runId]: {
                ...currentThread,
                status,
                reason,
                isExpanded: true,
                finalResult: message.data?.task_result?.messages
                  ?.filter((msg: any) => msg.content !== "TERMINATE")
                  .pop(),
              },
            };
          });
          closeSocket();
          break;
      }
    };

    socket.onclose = (event) => {
      clearTimeoutForRun();

      if (!isClosing) {
        updateSocket(runId, null);

        setThreadMessages((prev) => {
          const thread = prev[runId];
          if (thread && thread.status === "streaming") {
            return {
              ...prev,
              [runId]: {
                ...thread,
                status:
                  event.code === TIMEOUT_CONFIG.WEBSOCKET_CODE
                    ? "timeout"
                    : "complete",
                reason: event.reason || "Connection closed",
              },
            };
          }
          return prev;
        });
      }
    };

    socket.onerror = (error) => {
      clearTimeoutForRun();

      setThreadMessages((prev) => {
        const thread = prev[runId];
        if (!thread) return prev;

        return {
          ...prev,
          [runId]: {
            ...thread,
            status: "error",
            reason: "WebSocket connection error occurred",
            isExpanded: true,
          },
        };
      });

      closeSocket();
    };

    return socket;
  };

  const cancelRun = async (runId: string) => {
    const socket = activeSockets[runId];
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({ type: "stop", reason: "Cancelled by user" })
      );

      setThreadMessages((prev) => ({
        ...prev,
        [runId]: {
          ...prev[runId],
          status: "cancelled",
          reason: "Cancelled by user",
          isExpanded: true,
        },
      }));
    }
  };

  // Clean up timeouts when component unmounts
  React.useEffect(() => {
    return () => {
      Object.entries(timeoutRefs.current).forEach(([_, timeout]) =>
        clearTimeout(timeout)
      );
      timeoutRefs.current = {};
    };
  }, []);

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
      connectWebSocket(runId, query); // Now passing query to connectWebSocket
    } catch (err) {
      console.error("Error:", err);
      message.error("Error during request processing");

      if (runId) {
        if (activeSockets[runId]) {
          activeSockets[runId].close();
        }

        setThreadMessages((prev) => ({
          ...prev,
          [runId!]: {
            ...prev[runId!],
            status: "error",
            isExpanded: true,
          },
        }));
      }

      setError({
        status: false,
        message: err instanceof Error ? err.message : "Unknown error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    // session changed
    if (session) {
      setMessages([]);
      setThreadMessages({});
    }
  }, [session]);

  return (
    <div className="text-primary h-[calc(100vh-195px)] bg-primary relative rounded flex-1 scroll">
      <div className="flex gap-4 w-full">
        <div className="flex-1">
          <SessionManager />
        </div>
        <TeamManager />
      </div>
      <div className="flex flex-col h-full">
        <div
          className="flex-1 overflow-y-auto scroll mt-2 relative min-h-0"
          ref={chatContainerRef}
        >
          <MessageList
            messages={messages}
            threadMessages={threadMessages}
            setThreadMessages={setThreadMessages}
            onRetry={runTask}
            onCancel={cancelRun}
            onInputResponse={handleInputResponse} // Add the new prop
            loading={loading}
            teamConfig={teamConfig}
          />
        </div>

        {sessions !== null && sessions?.length === 0 ? (
          <div className="flex h-[calc(100%-100px)] flex-col items-center justify-center w-full">
            <div className="mt-4 text-sm text-secondary text-center">
              <img src={logo} alt="Welcome" className="w-72 h-72 mb-4" />
              Welcome! Create a session to get started!
            </div>
          </div>
        ) : (
          <>
            {session && (
              <div className="flex-shrink-0">
                <ChatInput
                  onSubmit={runTask}
                  loading={loading}
                  error={error}
                  disabled={Object.values(threadMessages).some(
                    (thread) => thread.status === "awaiting_input"
                  )} // Disable input while waiting for user input
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
