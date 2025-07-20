import { useState, useEffect, useCallback, useRef } from "react";
import {
  WorkflowEventUnion,
  WorkflowEventType,
  WorkflowExecution,
  WorkflowStatus,
  StepStatus,
} from "./types";
import { getServerUrl } from "../../utils/utils";

export interface WebSocketConnectionStatus {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
}

export interface WorkflowExecutionState {
  runId: string | null;
  execution: WorkflowExecution | null;
  status: WorkflowStatus;
  events: WorkflowEventUnion[];
  error: string | null;
}

export interface UseWorkflowWebSocketResult {
  connectionStatus: WebSocketConnectionStatus;
  executionState: WorkflowExecutionState;
  startWorkflow: (runId: string, workflowConfig: any, input?: any) => void;
  stopWorkflow: () => void;
  disconnect: () => void;
  resetState: () => void;
}

/**
 * Custom hook for managing WebSocket connections to workflow execution endpoints
 */
export const useWorkflowWebSocket = (): UseWorkflowWebSocketResult => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<WebSocketConnectionStatus>({
      isConnected: false,
      isConnecting: false,
      error: null,
    });

  const [executionState, setExecutionState] = useState<WorkflowExecutionState>({
    runId: null,
    execution: null,
    status: WorkflowStatus.CREATED,
    events: [],
    error: null,
  });

  // Helper for WebSocket URL construction (similar to MCP client)
  const getWebSocketBaseUrl = (url: string): string => {
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
      throw new Error("Invalid server URL configuration");
    }
  };

  const getWebSocketUrl = useCallback((runId: string): string => {
    const url = getServerUrl();
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const base = getWebSocketBaseUrl(url);
    return `${protocol}//${base}/api/workflow/ws/${runId}`;
  }, []);

  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WorkflowEventUnion = JSON.parse(event.data);

      // Add event to the events list
      setExecutionState((prev) => ({
        ...prev,
        events: [...prev.events, data],
      }));

      // Handle different event types
      switch (data.event_type) {
        case WorkflowEventType.WORKFLOW_STARTED:
          setExecutionState((prev) => ({
            ...prev,
            status: WorkflowStatus.RUNNING,
            error: null,
          }));
          break;

        case WorkflowEventType.WORKFLOW_COMPLETED:
          setExecutionState((prev) => ({
            ...prev,
            status: WorkflowStatus.COMPLETED,
            execution: data.execution,
          }));
          break;

        case WorkflowEventType.WORKFLOW_FAILED:
          setExecutionState((prev) => ({
            ...prev,
            status: WorkflowStatus.FAILED,
            execution: data.execution || prev.execution,
            error: data.error,
          }));
          break;

        case WorkflowEventType.WORKFLOW_CANCELLED:
          setExecutionState((prev) => ({
            ...prev,
            status: WorkflowStatus.CANCELLED,
            execution: data.execution || prev.execution,
            error: data.reason || "Workflow was cancelled",
          }));
          // Disconnect WebSocket after cancellation
          setTimeout(() => {
            if (wsRef.current) {
              wsRef.current.close();
              wsRef.current = null;
            }
            setConnectionStatus({
              isConnected: false,
              isConnecting: false,
              error: null,
            });
          }, 1000); // Give time for final messages
          break;

        case WorkflowEventType.STEP_STARTED:
          setExecutionState((prev) => {
            if (!prev.execution) return prev;

            const updatedExecution = {
              ...prev.execution,
              step_executions: {
                ...prev.execution.step_executions,
                [data.step_id]: {
                  step_id: data.step_id,
                  status: StepStatus.RUNNING,
                  start_time: data.timestamp,
                  input_data: data.input_data,
                  retry_count: 0,
                },
              },
            };

            return {
              ...prev,
              execution: updatedExecution,
            };
          });
          break;

        case WorkflowEventType.STEP_COMPLETED:
          setExecutionState((prev) => {
            if (!prev.execution) return prev;

            const stepExecution = prev.execution.step_executions[data.step_id];
            const updatedExecution = {
              ...prev.execution,
              step_executions: {
                ...prev.execution.step_executions,
                [data.step_id]: {
                  ...stepExecution,
                  status: StepStatus.COMPLETED,
                  end_time: data.timestamp,
                  output_data: data.output_data,
                },
              },
            };

            return {
              ...prev,
              execution: updatedExecution,
            };
          });
          break;

        case WorkflowEventType.STEP_FAILED:
          setExecutionState((prev) => {
            if (!prev.execution) return prev;

            const stepExecution = prev.execution.step_executions[data.step_id];
            const updatedExecution = {
              ...prev.execution,
              step_executions: {
                ...prev.execution.step_executions,
                [data.step_id]: {
                  ...stepExecution,
                  status: StepStatus.FAILED,
                  end_time: data.timestamp,
                  error: data.error,
                },
              },
            };

            return {
              ...prev,
              execution: updatedExecution,
            };
          });
          break;

        case WorkflowEventType.EDGE_ACTIVATED:
          // Handle edge activation - could be used for visual flow indicators
          break;

        default:
          console.warn("Unknown workflow event type:", data);
      }
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error);
      setExecutionState((prev) => ({
        ...prev,
        error: "Failed to parse workflow event",
      }));
    }
  }, []);

  const handleWebSocketError = useCallback((error: Event) => {
    console.error("Workflow WebSocket error:", error);
    setConnectionStatus((prev) => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
      error: "WebSocket connection error",
    }));
  }, []);

  const handleWebSocketClose = useCallback(() => {
    console.log("Workflow WebSocket closed");
    setConnectionStatus((prev) => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
    }));

    wsRef.current = null;
  }, []);

  const connect = useCallback(
    (runId: string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        return; // Already connected
      }

      setConnectionStatus((prev) => ({
        ...prev,
        isConnecting: true,
        error: null,
      }));

      try {
        const wsUrl = getWebSocketUrl(runId);
        console.log("Connecting to workflow WebSocket:", wsUrl);

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log("Workflow WebSocket connected");
          // Add log for debugging
          console.log(
            "[DEBUG] WebSocket connection established for runId:",
            runId
          );
          setConnectionStatus({
            isConnected: true,
            isConnecting: false,
            error: null,
          });

          setExecutionState((prev) => ({
            ...prev,
            runId,
            events: [],
            error: null,
          }));
        };

        ws.onmessage = handleWebSocketMessage;
        ws.onerror = handleWebSocketError;
        ws.onclose = handleWebSocketClose;

        wsRef.current = ws;
      } catch (error) {
        console.error("Failed to create WebSocket connection:", error);
        setConnectionStatus({
          isConnected: false,
          isConnecting: false,
          error: "Failed to create WebSocket connection",
        });
      }
    },
    [
      getWebSocketUrl,
      handleWebSocketMessage,
      handleWebSocketError,
      handleWebSocketClose,
    ]
  );

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket not connected, cannot send message:", message);
    }
  }, []);

  const startWorkflow = useCallback(
    (runId: string, workflowConfig: any, input?: any) => {
      console.log("Starting workflow:", { runId, workflowConfig, input });

      // Reset execution state to initial state
      setExecutionState({
        runId,
        status: WorkflowStatus.CREATED,
        execution: {
          id: runId,
          workflow_id: workflowConfig.id || runId,
          status: WorkflowStatus.CREATED,
          start_time: new Date().toISOString(),
          state: {},
          step_executions: {},
        },
        events: [],
        error: null,
      });

      // Connect to WebSocket
      connect(runId);

      // Send start message after a short delay to ensure connection
      setTimeout(() => {
        sendMessage({
          type: "start",
          workflow_config: workflowConfig,
          input: input || {},
        });
      }, 100);
    },
    [connect, sendMessage]
  );

  const stopWorkflow = useCallback(() => {
    console.log("Stopping workflow");
    sendMessage({ type: "stop" });
  }, [sendMessage]);

  const resetState = useCallback(() => {
    console.log("Resetting workflow execution state");

    setExecutionState({
      runId: null,
      execution: null,
      status: WorkflowStatus.CREATED,
      events: [],
      error: null,
    });
  }, []);

  const disconnect = useCallback(() => {
    console.log("Disconnecting workflow WebSocket");

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnectionStatus({
      isConnected: false,
      isConnecting: false,
      error: null,
    });

    setExecutionState({
      runId: null,
      execution: null,
      status: WorkflowStatus.CREATED,
      events: [],
      error: null,
    });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connectionStatus,
    executionState,
    startWorkflow,
    stopWorkflow,
    disconnect,
    resetState,
  };
};
