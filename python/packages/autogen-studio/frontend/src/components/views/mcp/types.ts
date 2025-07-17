import type { McpServerParams } from "../../types/datamodel";

// Define a more complete MCP Server interface for the playground
export interface McpServer {
  id: string;
  name: string;
  description?: string;
  serverParams: McpServerParams;
  isConnected?: boolean;
  lastConnected?: string;
  tools?: Array<{
    name: string;
    description: string;
    schema?: any;
  }>;
}
