// api.ts for Tool Maker Lab
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

export class ToolMakerAPI {
  ws: WebSocket | null = null;

  connect(
    onMessage: (msg: ToolMakerStreamMessage) => void,
    onError?: (err: any) => void,
    onClose?: () => void
  ) {
    const wsUrl = `${window.location.protocol === "https:" ? "wss" : "ws"}://${
      window.location.host
    }/api/maker/tool`;
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
