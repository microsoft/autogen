"use client";

import * as React from "react";
import { message } from "antd";
import MessageList from "./messagelist";
import ChatInput from "./chatinput";
import { getServerUrl } from "../../../utils";
import { SessionManager } from "../../shared/session/manager";
import { IStatus } from "../../../types/app";
import { Message } from "../../../types/datamodel";

interface ChatViewProps {
  initMessages: any[];
  viewHeight?: string;
}

export default function ChatView({
  initMessages,
  viewHeight = "100%",
}: ChatViewProps) {
  const serverUrl = getServerUrl();
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [currentSessionId, setCurrentSessionId] = React.useState<string | null>(
    null
  );
  const [currentRunId, setCurrentRunId] = React.useState<string | null>(null);
  const [sessionLogs, setSessionLogs] = React.useState<Record<string, any[]>>(
    {}
  );
  const [activeSockets, setActiveSockets] = React.useState<
    Record<string, WebSocket>
  >({});

  const getBaseUrl = (url: string): string => {
    try {
      return url
        .replace(/(^\w+:|^)\/\//, "")
        .replace("/api", "")
        .replace(/\/$/, "");
    } catch (error) {
      console.error("Error processing server URL:", error);
      throw new Error("Invalid server URL configuration");
    }
  };

  React.useEffect(() => {
    setMessages(initMessages);
  }, [initMessages]);

  // Cleanup WebSocket connections
  React.useEffect(() => {
    return () => {
      Object.values(activeSockets).forEach((socket) => socket.close());
    };
  }, [activeSockets]);

  const createRun = async (sessionId: string): Promise<string> => {
    const response = await fetch(`${serverUrl}/sessions/${sessionId}/runs`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: "current-user", // Replace with actual user management
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to create run");
    }

    const data = await response.json();
    return data.data.run_id;
  };

  const startRun = async (runId: string, query: string) => {
    const response = await fetch(`${serverUrl}/runs/${runId}/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: {
          user_id: "current-user", // Replace with actual user management
          session_id: currentSessionId,
          config: {
            content: query,
            source: "user",
          },
          message_meta: {
            team_id: "default-team", // Replace with actual team management
          },
        },
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to start run");
    }

    return await response.json();
  };

  const connectWebSocket = async (runId: string) => {
    const baseUrl = getBaseUrl(serverUrl);
    const wsUrl = `ws://${baseUrl}/api/ws/runs/${runId}`;

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setActiveSockets((prev) => ({
        ...prev,
        [runId]: socket,
      }));
    };

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);

      setSessionLogs((prev) => ({
        ...prev,
        [runId]: [...(prev[runId] || []), message],
      }));

      if (message.type === "StreamEvent") {
        switch (message.event_type) {
          case "message":
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.runId === runId && msg.sender === "bot") {
                  return {
                    ...msg,
                    text: (msg.text || "") + message.data.content,
                  };
                }
                return msg;
              })
            );
            break;

          case "completion":
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.runId === runId && msg.sender === "bot") {
                  return {
                    ...msg,
                    status: "complete",
                    finalResponse: message.data.final_message,
                  };
                }
                return msg;
              })
            );
            break;
        }
      }

      if (message.type === "TerminationEvent") {
        const status =
          message.reason === "cancelled"
            ? "cancelled"
            : message.error
            ? "error"
            : "complete";

        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.runId === runId && msg.sender === "bot") {
              return {
                ...msg,
                status,
                error: message.error,
              };
            }
            return msg;
          })
        );

        socket.close();
      }
    };

    socket.onclose = () => {
      setActiveSockets((prev) => {
        const newSockets = { ...prev };
        delete newSockets[runId];
        return newSockets;
      });
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      message.error("WebSocket connection error");
      socket.close();
    };

    return socket;
  };

  const cancelRun = async (runId: string) => {
    const socket = activeSockets[runId];
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({
          type: "cancel",
        })
      );
    }
  };

  const getCompletion = async (query: string) => {
    setError(null);
    setLoading(true);

    let runId: string | null = null;

    try {
      // Create new run
      runId = await createRun(currentSessionId!);
      setCurrentRunId(runId);

      // Add messages to UI
      const userMessage: Message = {
        text: query,
        sender: "user",
        sessionId: currentSessionId,
        runId: runId,
      };

      const botMessage: Message = {
        text: "",
        sender: "bot",
        sessionId: currentSessionId,
        runId: runId,
        status: "processing",
      };

      setMessages((prev) => [...prev, userMessage, botMessage]);

      // Connect WebSocket first
      await connectWebSocket(runId);

      // Start the run
      await startRun(runId, query);
    } catch (err) {
      console.error("Error:", err);
      message.error("Error during request processing");

      if (runId && activeSockets[runId]) {
        activeSockets[runId].close();
      }

      setError({
        status: false,
        message: err instanceof Error ? err.message : "Unknown error occurred",
      });

      // Update message status if it was created
      if (runId) {
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.runId === runId && msg.sender === "bot") {
              return {
                ...msg,
                status: "error",
                error:
                  err instanceof Error ? err.message : "Unknown error occurred",
              };
            }
            return msg;
          })
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-primary h-full overflow-auto bg-primary relative rounded flex-1">
      <div className="flex flex-col h-full">
        <div className="flex-1">
          <SessionManager />
          <MessageList
            messages={messages}
            sessionLogs={sessionLogs}
            onRetry={getCompletion}
            onCancel={cancelRun}
            loading={loading}
          />
        </div>
        <div>
          <ChatInput onSubmit={getCompletion} loading={loading} error={error} />
        </div>
      </div>
    </div>
  );
}
