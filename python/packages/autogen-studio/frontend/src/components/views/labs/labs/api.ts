// api.ts for Tool Maker Lab
import { BaseAPI } from "../../../utils/baseapi";

export interface ToolMakerEvent {
  status: string;
  content: string;
}

export interface ToolComponentModel {
  provider: string;
  component_type: string;
  version: number;
  component_version: number;
  description: string;
  label: string;
  config: any;
}

export type ToolMakerStreamMessage =
  | { event: ToolMakerEvent }
  | { component: ToolComponentModel }
  | { error: string };

export class ToolMakerAPI extends BaseAPI {
  ws: WebSocket | null = null;

  // Helper for WebSocket URL construction (similar to MCP implementation)
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

  connect(
    onMessage: (msg: ToolMakerStreamMessage) => void,
    onError?: (err: any) => void,
    onClose?: () => void
  ) {
    // Use the same server URL logic as other APIs
    const serverUrl = this.getBaseUrl(); // e.g., "/api" or "http://localhost:8081/api"
    const baseUrl = this.getWebSocketBaseUrl(serverUrl);
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${baseUrl}/api/maker/tool`;
    this.ws = new window.WebSocket(wsUrl);
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        if (onError) onError(e);
      }
    };
    this.ws.onerror = (event) => {
      if (onError) onError(event);
    };
    this.ws.onclose = () => {
      if (onClose) onClose();
    };
  }

  sendDescription(description: string) {
    if (this.ws && this.ws.readyState === 1) {
      this.ws.send(JSON.stringify({ description }));
    }
  }

  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

export const toolMakerAPI = new ToolMakerAPI();
