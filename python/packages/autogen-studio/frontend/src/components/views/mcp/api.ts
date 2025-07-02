import {
  Gallery,
  Component,
  McpWorkbenchConfig,
  McpServerParams,
} from "../../types/datamodel";
import { BaseAPI } from "../../utils/baseapi";
import { getServerUrl } from "../../utils/utils";

// MCP-specific interfaces for server operations
// MCP types matching backend exactly (native MCP types)
export interface Tool {
  name: string;
  description?: string | null;
  inputSchema: {
    [key: string]: any;
  };
  annotations?: {
    title?: string | null;
    readOnlyHint?: boolean | null;
    destructiveHint?: boolean | null;
    idempotentHint?: boolean | null;
    openWorldHint?: boolean | null;
  } | null;
}

export interface CallToolResult {
  content: Array<{
    type: "text" | "image" | "resource";
    text?: string;
    data?: string;
    mimeType?: string;
    resource?: any;
    annotations?: any;
  }>;
  isError?: boolean;
}

export interface ListToolsResponse {
  status: boolean;
  message: string;
  tools?: Tool[];
}

export interface CallToolResponse {
  status: boolean;
  message: string;
  result?: CallToolResult;
}

export interface ServerCapabilities {
  tools?: {
    listChanged?: boolean;
  };
  resources?: {
    subscribe?: boolean;
    listChanged?: boolean;
  };
  prompts?: {
    listChanged?: boolean;
  };
  logging?: {};
  sampling?: {};
}

export interface GetCapabilitiesResponse {
  status: boolean;
  message: string;
  capabilities?: ServerCapabilities;
}

export class McpAPI extends BaseAPI {
  // Gallery management methods (existing functionality)
  async listGalleries(userId: string): Promise<Gallery[]> {
    const response = await fetch(
      `${this.getBaseUrl()}/gallery/?user_id=${userId}`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to fetch galleries");
    return data.data;
  }

  async getGallery(galleryId: number, userId: string): Promise<Gallery> {
    const response = await fetch(
      `${this.getBaseUrl()}/gallery/${galleryId}?user_id=${userId}`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to fetch gallery");
    return data.data;
  }

  // Helper function to extract MCP workbenches from a gallery
  extractMcpWorkbenches(gallery: Gallery): Component<McpWorkbenchConfig>[] {
    return (
      gallery.config.components.workbenches?.filter(
        (workbench): workbench is Component<McpWorkbenchConfig> =>
          workbench.provider.includes("McpWorkbench") ||
          (workbench.config as any)?.server_params !== undefined
      ) || []
    );
  }

  // MCP Server operations (new functionality)
  async listResources(serverParams: McpServerParams) {
    const response = await fetch(`${this.getBaseUrl()}/mcp/resources/list`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ server_params: serverParams }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to list MCP resources");
    }

    return data;
  }

  async getResource(serverParams: McpServerParams, uri: string) {
    const response = await fetch(`${this.getBaseUrl()}/mcp/resources/get`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        server_params: serverParams,
        uri: uri,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to get MCP resource");
    }

    return data;
  }

  async listPrompts(serverParams: McpServerParams) {
    const response = await fetch(`${this.getBaseUrl()}/mcp/prompts/list`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ server_params: serverParams }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to list MCP prompts");
    }

    return data;
  }

  async getPrompt(
    serverParams: McpServerParams,
    name: string,
    promptArgs?: Record<string, any>
  ) {
    const response = await fetch(`${this.getBaseUrl()}/mcp/prompts/get`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        server_params: serverParams,
        name: name,
        arguments: promptArgs || {},
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to get MCP prompt");
    }

    return data;
  }

  async getCapabilities(
    serverParams: McpServerParams
  ): Promise<GetCapabilitiesResponse> {
    const response = await fetch(`${this.getBaseUrl()}/mcp/capabilities/get`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ server_params: serverParams }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to get MCP capabilities");
    }

    return data;
  }

  async listTools(serverParams: McpServerParams): Promise<ListToolsResponse> {
    const response = await fetch(`${this.getBaseUrl()}/mcp/tools/list`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ server_params: serverParams }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to list MCP tools");
    }

    return data;
  }

  async callTool(
    serverParams: McpServerParams,
    toolName: string,
    toolArguments: Record<string, any>
  ): Promise<CallToolResponse> {
    const response = await fetch(`${this.getBaseUrl()}/mcp/tools/call`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        server_params: serverParams,
        tool_name: toolName,
        arguments: toolArguments,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to call MCP tool");
    }

    return data;
  }

  async healthCheck(): Promise<{ status: boolean; message: string }> {
    const response = await fetch(`${this.getBaseUrl()}/mcp/health`, {
      method: "GET",
      headers: this.getHeaders(),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "MCP health check failed");
    }

    return data;
  }

  // Test MCP server connection
  async testMcpConnection(
    workbench: Component<McpWorkbenchConfig>
  ): Promise<boolean> {
    try {
      // Use the health check or list tools to test connection
      if (workbench.config.server_params) {
        const result = await this.listTools(workbench.config.server_params);
        return result.status;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  // WebSocket connection management
  async createWebSocketConnection(serverParams: McpServerParams): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/mcp/ws/connect`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ server_params: serverParams }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `HTTP ${response.status}: ${
          errorText || "Failed to create WebSocket connection"
        }`
      );
    }

    try {
      const responseText = await response.text();
      return JSON.parse(responseText);
    } catch (jsonError) {
      throw new Error(
        `Invalid JSON response from server. Check if the MCP route is properly configured.`
      );
    }
  }
}

// WebSocket-based MCP functionality
export interface McpWebSocketState {
  connected: boolean;
  connecting: boolean;
  capabilities: ServerCapabilities | null;
  sessionId: string | null;
  error: string | null;
  lastActivity: Date | null;
  activityMessages: McpActivityMessage[];
  pendingElicitations: ElicitationRequest[];
}

export interface McpWebSocketMessage {
  type:
    | "connected"
    | "initializing"
    | "initialized"
    | "operation_result"
    | "operation_error"
    | "error"
    | "pong"
    | "mcp_activity"
    | "elicitation_request";
  session_id?: string;
  capabilities?: ServerCapabilities;
  operation?: string;
  data?: any;
  error?: string;
  message?: string;
  timestamp?: string;
  // Activity message fields
  activity_type?: "protocol" | "error" | "sampling" | "elicitation";
  details?: any;
  // Elicitation fields
  request_id?: string;
  requestedSchema?: any;
}

export interface McpActivityMessage {
  id: string;
  activity_type: "protocol" | "error" | "sampling" | "elicitation";
  message: string;
  details?: any;
  session_id?: string;
  timestamp: Date;
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
  disconnect: () => void;
}

export class McpWebSocketClient {
  private wsRef: WebSocket | null = null;
  private operationPromises: Map<
    string,
    { resolve: (value: any) => void; reject: (error: any) => void }
  > = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private baseReconnectDelay = 1000;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private currentState: McpWebSocketState = {
    connected: false,
    connecting: false,
    capabilities: null,
    sessionId: null,
    error: null,
    lastActivity: null,
    activityMessages: [],
    pendingElicitations: [],
  };

  constructor(
    private serverParams: McpServerParams,
    private onStateChange: (state: Partial<McpWebSocketState>) => void
  ) {}

  private updateState(partialState: Partial<McpWebSocketState>) {
    this.currentState = { ...this.currentState, ...partialState };
    this.onStateChange(partialState);
  }

  // Helper for WebSocket URL construction (similar to chat implementation)
  private getWebSocketBaseUrl(url: string): string {
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
  }

  async connect(): Promise<void> {
    this.updateState({ connecting: true, error: null });

    try {
      // First, get the WebSocket connection URL using proper API construction
      const mcpApiInstance = mcpAPI;
      const connectionData = await mcpApiInstance.createWebSocketConnection(
        this.serverParams
      );

      if (!connectionData.status) {
        throw new Error(
          connectionData.message || "Failed to create WebSocket connection"
        );
      }

      const { session_id, websocket_url } = connectionData;

      // Construct WebSocket URL using the correct server URL (not window.location.host)
      // This handles cases where backend runs on different port (e.g., 8081 vs 8000)
      const serverUrl = getServerUrl(); // e.g., "/api" or "http://localhost:8081/api"
      const baseUrl = this.getWebSocketBaseUrl(serverUrl);
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${baseUrl}${websocket_url}`;

      // Create WebSocket connection
      const ws = new WebSocket(wsUrl);
      this.wsRef = ws;

      ws.onopen = () => {
        this.updateState({
          connected: true,
          connecting: false,
          sessionId: session_id,
          error: null,
          lastActivity: new Date(),
        });
        this.reconnectAttempts = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: McpWebSocketMessage = JSON.parse(event.data);

          this.updateState({ lastActivity: new Date() });

          switch (message.type) {
            case "connected":
              break;

            case "initializing":
              break;

            case "initialized":
              if (message.capabilities) {
                this.updateState({ capabilities: message.capabilities });
              }
              break;

            case "operation_result":
              // Handle operation results
              if (message.operation) {
                const operationKey = message.operation;
                const promise = this.operationPromises.get(operationKey);
                if (promise) {
                  promise.resolve(message.data);
                  this.operationPromises.delete(operationKey);
                }
              }
              break;

            case "operation_error":
              // Handle operation-specific errors - reject the specific operation
              if (message.operation) {
                const promise = this.operationPromises.get(message.operation);
                if (promise) {
                  promise.reject(
                    new Error(message.error || "Operation failed")
                  );
                  this.operationPromises.delete(message.operation);
                }
              }
              break;

            case "error":
              // Handle connection/session-level errors - these affect the whole session
              this.updateState({
                error: message.error || "Connection error",
              });
              break;

            case "pong":
              // Handle pong response
              break;

            case "mcp_activity":
              // Handle activity messages
              if (message.message && message.activity_type) {
                const activityMessage: McpActivityMessage = {
                  id: `${Date.now()}-${Math.random()
                    .toString(36)
                    .substr(2, 9)}`,
                  activity_type: message.activity_type,
                  message: message.message,
                  details: message.details,
                  session_id: message.session_id,
                  timestamp: message.timestamp
                    ? new Date(message.timestamp)
                    : new Date(),
                };

                // Update state with new activity message
                this.updateState({
                  activityMessages: [
                    ...this.currentState.activityMessages,
                    activityMessage,
                  ],
                });
              }
              break;

            case "elicitation_request":
              // Handle elicitation requests
              if (message.request_id && message.message) {
                const elicitationRequest: ElicitationRequest = {
                  request_id: message.request_id,
                  message: message.message,
                  requestedSchema: message.requestedSchema,
                  session_id:
                    message.session_id || this.currentState.sessionId || "",
                  timestamp: message.timestamp || new Date().toISOString(),
                };

                // Add to pending elicitations
                this.updateState({
                  pendingElicitations: [
                    ...this.currentState.pendingElicitations,
                    elicitationRequest,
                  ],
                });
              } else {
                console.error(
                  "Invalid elicitation request - missing request_id or message:",
                  message
                );
              }
              break;

            default:
              // Unknown message type - silently ignore
              break;
          }
        } catch (error) {
          // Error parsing WebSocket message - silently ignore
        }
      };

      ws.onerror = (error) => {
        this.updateState({
          error: "WebSocket connection error",
          connected: false,
          connecting: false,
        });
      };

      ws.onclose = (event) => {
        this.updateState({
          connected: false,
          connecting: false,
        });

        // // Attempt to reconnect if not manually closed
        // if (
        //   event.code !== 1000 &&
        //   this.reconnectAttempts < this.maxReconnectAttempts
        // ) {
        //   const delay =
        //     this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts);

        //   this.reconnectTimeout = setTimeout(() => {
        //     this.reconnectAttempts++;
        //     this.connect();
        //     console.log(
        //       `Reconnecting... Attempt ${this.reconnectAttempts} after ${delay}ms`
        //     );
        //   }, delay);
        // }
      };
    } catch (error) {
      this.updateState({
        error: error instanceof Error ? error.message : "Connection failed",
        connected: false,
        connecting: false,
      });
    }
  }

  async executeOperation(
    operation: Omit<McpOperationMessage, "type">
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.wsRef || this.wsRef.readyState !== WebSocket.OPEN) {
        reject(new Error("WebSocket not connected"));
        return;
      }

      const operationKey = operation.operation;

      // Store the promise for this operation
      this.operationPromises.set(operationKey, { resolve, reject });

      // Send the operation message
      const message: McpOperationMessage = {
        type: "operation",
        ...operation,
      };

      try {
        this.wsRef.send(JSON.stringify(message));
      } catch (error) {
        this.operationPromises.delete(operationKey);
        reject(error);
      }

      // Set a timeout for the operation
      setTimeout(() => {
        if (this.operationPromises.has(operationKey)) {
          this.operationPromises.delete(operationKey);
          reject(new Error("Operation timeout"));
        }
      }, 30000); // 30 second timeout
    });
  }

  ping(): void {
    if (this.wsRef && this.wsRef.readyState === WebSocket.OPEN) {
      this.wsRef.send(JSON.stringify({ type: "ping" }));
    }
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.wsRef) {
      this.wsRef.close();
      this.wsRef = null;
    }

    // Reject all pending operations
    this.operationPromises.forEach(({ reject }) => {
      reject(new Error("WebSocket connection closed"));
    });
    this.operationPromises.clear();

    this.updateState({
      connected: false,
      connecting: false,
      sessionId: null,
      capabilities: null,
      error: null,
    });
  }

  sendElicitationResponse(response: ElicitationResponse): void {
    if (this.wsRef && this.wsRef.readyState === WebSocket.OPEN) {
      try {
        this.wsRef.send(JSON.stringify(response));

        // Remove the elicitation from pending list
        this.updateState({
          pendingElicitations: this.currentState.pendingElicitations.filter(
            (req) => req.request_id !== response.request_id
          ),
        });
      } catch (error) {
        console.error("Failed to send elicitation response:", error);
      }
    } else {
      console.error(
        "WebSocket not connected - cannot send elicitation response"
      );
    }
  }
}

export const mcpAPI = new McpAPI();

// Elicitation interfaces
export interface ElicitationRequest {
  request_id: string;
  message: string;
  requestedSchema?: any;
  session_id: string;
  timestamp: string;
}

export interface ElicitationResponse {
  type: "elicitation_response";
  request_id: string;
  action: "accept" | "decline" | "cancel";
  data?: Record<string, any>;
  session_id: string;
}
