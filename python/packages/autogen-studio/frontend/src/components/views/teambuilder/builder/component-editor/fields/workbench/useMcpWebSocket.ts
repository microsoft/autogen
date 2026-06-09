import { useState, useEffect, useCallback, useRef } from "react";
import { McpServerParams } from "../../../../../../types/datamodel";
import {
  ServerCapabilities,
  Tool,
  CallToolResult,
} from "../../../../../mcp/api";
import { getServerUrl } from "../../../../../../utils/utils";

export interface McpWebSocketState {
  connected: boolean;
  connecting: boolean;
  capabilities: ServerCapabilities | null;
  sessionId: string | null;
  error: string | null;
  lastActivity: Date | null;
}

export interface McpWebSocketMessage {
  type:
    | "connected"
    | "initializing"
    | "initialized"
    | "operation_result"
    | "error"
    | "pong";
  session_id?: string;
  capabilities?: ServerCapabilities;
  operation?: string;
  data?: any;
  error?: string;
  message?: string;
  timestamp?: string;
}

export interface McpOperationMessage {
  type: "operation";
  operation: string;
  tool_name?: string;
  arguments?: Record<string, any>;
  uri?: string;
  name?: string;
}

export interface UseMcpWebSocketReturn {
  state: McpWebSocketState;
  connect: () => Promise<void>;
  executeOperation: (
    operation: Omit<McpOperationMessage, "type">
  ) => Promise<any>;
  ping: () => void;
  reconnect: () => void;
  disconnect: () => void;
}

export const useMcpWebSocket = (
  serverParams: McpServerParams
): UseMcpWebSocketReturn => {
  const [state, setState] = useState<McpWebSocketState>({
    connected: false,
    connecting: false,
    capabilities: null,
    sessionId: null,
    error: null,
    lastActivity: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const operationPromisesRef = useRef<
    Map<string, { resolve: (value: any) => void; reject: (error: any) => void }>
  >(new Map());
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000; // 1 second

  const getWebSocketBaseUrl = useCallback((url: string): string => {
    try {
      let baseUrl = url.replace(/(^\w+:|^)\/\//, "");
      if (baseUrl.startsWith("localhost")) {
        baseUrl = baseUrl.replace("/api", "");
      } else if (baseUrl === "/api") {
        baseUrl = window.location.host;
      } else {
        baseUrl = baseUrl.replace("/api", "").replace(/\/$/, "");
      }
      return baseUrl;
    } catch (error) {
      console.error("Error processing server URL:", error);
      throw new Error("Invalid server URL configuration");
    }
  }, []);

  const getWebSocketUrl = useCallback(() => {
    const serverUrl = getServerUrl();
    const baseUrl = getWebSocketBaseUrl(serverUrl);
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${baseUrl}`;
  }, [getWebSocketBaseUrl]);

  const cleanup = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    // Reject all pending operations
    operationPromisesRef.current.forEach(({ reject }) => {
      reject(new Error("WebSocket connection closed"));
    });
    operationPromisesRef.current.clear();
  }, []);

  const connect = useCallback(async () => {
    if (state.connecting || state.connected) {
      return;
    }

    setState((prev) => ({ ...prev, connecting: true, error: null }));

    try {
      // First, get the WebSocket connection URL
      console.log("Connecting to MCP server with params:", serverParams);
      const serverUrl = getServerUrl();
      const response = await fetch(`${serverUrl}/mcp/ws/connect`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ server_params: serverParams }),
      });

      console.log("Response status:", response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("HTTP error response:", errorText);
        throw new Error(
          `HTTP ${response.status}: ${
            errorText || "Failed to create WebSocket connection"
          }`
        );
      }

      let connectionData;
      try {
        const responseText = await response.text();
        console.log("Raw response:", responseText);
        connectionData = JSON.parse(responseText);
      } catch (jsonError) {
        console.error("JSON parse error:", jsonError);
        throw new Error(
          `Invalid JSON response from server. Check if the MCP route is properly configured.`
        );
      }

      if (!connectionData.status) {
        throw new Error(
          connectionData.message || "Failed to create WebSocket connection"
        );
      }

      const { session_id, websocket_url } = connectionData;
      const wsUrl = `${getWebSocketUrl()}${websocket_url}`;

      // Create WebSocket connection
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`MCP WebSocket connected to session ${session_id}`);
        setState((prev) => ({
          ...prev,
          connected: true,
          connecting: false,
          sessionId: session_id,
          error: null,
          lastActivity: new Date(),
        }));
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: McpWebSocketMessage = JSON.parse(event.data);

          setState((prev) => ({ ...prev, lastActivity: new Date() }));

          switch (message.type) {
            case "connected":
              console.log("MCP session connected");
              break;

            case "initializing":
              console.log("MCP session initializing:", message.message);
              break;

            case "initialized":
              console.log("MCP session initialized with capabilities");
              if (message.capabilities) {
                // Use native MCP capabilities directly
                console.log(
                  "Using native MCP capabilities:",
                  message.capabilities
                );
                setState((prev) => ({
                  ...prev,
                  capabilities: message.capabilities || null,
                }));
              }
              break;

            case "operation_result":
              // Handle operation results
              if (message.operation) {
                const operationKey = message.operation;
                const promise = operationPromisesRef.current.get(operationKey);
                if (promise) {
                  promise.resolve(message.data);
                  operationPromisesRef.current.delete(operationKey);
                }
              }
              break;

            case "error":
              console.error("MCP WebSocket error:", message.error);
              setState((prev) => ({
                ...prev,
                error: message.error || "Unknown error",
              }));

              // If it's an operation error, reject the specific operation
              if (message.operation) {
                const promise = operationPromisesRef.current.get(
                  message.operation
                );
                if (promise) {
                  promise.reject(
                    new Error(message.error || "Operation failed")
                  );
                  operationPromisesRef.current.delete(message.operation);
                }
              }
              break;

            case "pong":
              // Handle pong response
              break;

            default:
              console.warn("Unknown MCP message type:", message.type);
          }
        } catch (error) {
          console.error("Error parsing MCP WebSocket message:", error);
        }
      };

      ws.onerror = (error) => {
        console.error("MCP WebSocket error:", error);
        setState((prev) => ({
          ...prev,
          error: "WebSocket connection error",
          connected: false,
          connecting: false,
        }));
      };

      ws.onclose = (event) => {
        console.log("MCP WebSocket closed:", event.code, event.reason);
        setState((prev) => ({
          ...prev,
          connected: false,
          connecting: false,
        }));

        // Attempt to reconnect if not manually closed
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < maxReconnectAttempts
        ) {
          const delay =
            baseReconnectDelay * Math.pow(2, reconnectAttempts.current);
          console.log(
            `Attempting to reconnect in ${delay}ms (attempt ${
              reconnectAttempts.current + 1
            }/${maxReconnectAttempts})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error("Failed to establish MCP WebSocket connection:", error);
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Connection failed",
        connected: false,
        connecting: false,
      }));
    }
  }, [serverParams, state.connecting, state.connected, getWebSocketUrl]);

  const executeOperation = useCallback(
    async (operation: Omit<McpOperationMessage, "type">): Promise<any> => {
      return new Promise((resolve, reject) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          reject(new Error("WebSocket not connected"));
          return;
        }

        const operationKey = operation.operation;

        // Store the promise for this operation
        operationPromisesRef.current.set(operationKey, { resolve, reject });

        // Send the operation message
        const message: McpOperationMessage = {
          type: "operation",
          ...operation,
        };

        try {
          wsRef.current.send(JSON.stringify(message));
        } catch (error) {
          operationPromisesRef.current.delete(operationKey);
          reject(error);
        }

        // Set a timeout for the operation
        setTimeout(() => {
          if (operationPromisesRef.current.has(operationKey)) {
            operationPromisesRef.current.delete(operationKey);
            reject(new Error("Operation timeout"));
          }
        }, 30000); // 30 second timeout
      });
    },
    []
  );

  const ping = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "ping" }));
    }
  }, []);

  const reconnect = useCallback(() => {
    cleanup();
    setState((prev) => ({
      ...prev,
      connected: false,
      connecting: false,
      error: null,
    }));
    reconnectAttempts.current = 0;
    connect();
  }, [cleanup, connect]);

  const disconnect = useCallback(() => {
    cleanup();
    setState((prev) => ({
      ...prev,
      connected: false,
      connecting: false,
      sessionId: null,
      capabilities: null,
      error: null,
    }));
  }, [cleanup]);

  // Manual connection only - no auto-connect
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  // Periodic ping to keep connection alive
  useEffect(() => {
    if (state.connected) {
      const pingInterval = setInterval(ping, 30000); // Ping every 30 seconds
      return () => clearInterval(pingInterval);
    }
  }, [state.connected, ping]);

  return {
    state,
    connect,
    executeOperation,
    ping,
    reconnect,
    disconnect,
  };
};
