"use client";

import * as React from "react";
import { message } from "antd";
import { IMessage, IStatus, LogEvent } from "./../../../types";
import MessageList from "./messagelist";
import ChatInput from "./chatinput";
import { getServerUrl } from "../../../utils";
import SessionManager from "../../shared/sessionmanager";
import { appContext } from "../../../../hooks/provider";

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
  const [messages, setMessages] = React.useState<IMessage[]>([]);
  const [currentSessionId, setCurrentSessionId] = React.useState<string | null>(
    null
  );
  const [sessionLogs, setSessionLogs] = React.useState<
    Record<string, LogEvent[]>
  >({});
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

  const connectWebSocket = async (sessionId: string) => {
    const baseUrl = getBaseUrl(serverUrl);
    const wsUrl = `ws://${baseUrl}/api/ws/logs/${sessionId}`;

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setActiveSockets((prev) => ({
        ...prev,
        [sessionId]: socket,
      }));
    };

    socket.onmessage = (event) => {
      const logEvent = JSON.parse(event.data);

      setSessionLogs((prev) => ({
        ...prev,
        [sessionId]: [...(prev[sessionId] || []), logEvent],
      }));

      if (logEvent.type === "GroupChatPublishEvent") {
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.sessionId === sessionId && msg.sender === "bot") {
              return {
                ...msg,
                text: logEvent.content,
              };
            }
            return msg;
          })
        );
      }

      if (logEvent.type === "TerminationEvent") {
        socket.close();
        setActiveSockets((prev) => {
          const newSockets = { ...prev };
          delete newSockets[sessionId];
          return newSockets;
        });
      }
    };

    socket.onclose = () => {
      setActiveSockets((prev) => {
        const newSockets = { ...prev };
        delete newSockets[sessionId];
        return newSockets;
      });
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      message.error("WebSocket connection error");
      socket.close();
      setActiveSockets((prev) => {
        const newSockets = { ...prev };
        delete newSockets[sessionId];
        return newSockets;
      });
    };

    return socket;
  };

  const createRun = async (): Promise<string> => {
    const response = await fetch(`${serverUrl}/create_session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error("Failed to create session");
    }

    const data = await response.json();
    return data.session_id;
  };

  const chatHistory = (messages: IMessage[]) => {
    let history = "";
    messages.forEach((message) => {
      history += `${message.config.source}: ${message.config.content}\n`;
    });
    return history;
  };

  const getLastMessage = (messages: any[], n: number = 5) => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const content = messages[i]["content"];
      if (content.length > n) {
        return content;
      }
    }
    return null;
  };

  const getCompletion = async (query: string) => {
    setError(null);
    setLoading(true);

    let currentSessionId: string | null = null;
    try {
      currentSessionId = await createSession();
      setCurrentSessionId(currentSessionId);

      await connectWebSocket(currentSessionId);

      const userMessage: IMessage = {
        text: query,
        sender: "user",
        sessionId: currentSessionId,
      };

      const botMessage: IMessage = {
        text: "",
        sender: "bot",
        sessionId: currentSessionId,
        status: "processing",
      };

      setMessages((prev) => [...prev, userMessage, botMessage]);

      const generateUrl = `${serverUrl}/generate`;
      const response = await fetch(generateUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: query,
          history: chatHistory(messages),
          session_id: currentSessionId,
        }),
      });

      if (!response.ok) {
        throw new Error("Generate request failed");
      }

      const data = await response.json();

      if (data.status) {
        const lastMessage = getLastMessage(data.data.messages);
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.sessionId === currentSessionId && msg.sender === "bot") {
              return {
                ...msg,
                finalResponse: lastMessage,
                status: "complete",
              };
            }
            return msg;
          })
        );
      } else {
        message.error(data.message);
      }
    } catch (err) {
      console.error("Error:", err);
      message.error("Error during request processing");
      if (currentSessionId && activeSockets[currentSessionId]) {
        activeSockets[currentSessionId].close();
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
    <div className="text-primary  h-full   overflow-auto bg-primary relative   rounded flex-1">
      <div className="flex flex-col h-full">
        <div className="flex-1 ">
          {" "}
          <SessionManager />
          <MessageList
            messages={messages}
            sessionLogs={sessionLogs}
            onRetry={getCompletion}
            loading={loading}
          />
        </div>
        <div className=" ">
          {" "}
          <ChatInput onSubmit={getCompletion} loading={loading} error={error} />
        </div>
      </div>
    </div>
  );
}
