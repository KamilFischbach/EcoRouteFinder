// What the web MCP client keeps from the MCP server's answers (backend/app/mcp_server.py).
// Input schemas are the JSON schemas of the Pydantic argument models in backend/app/ai/tools.py.

/** The subset of JSON Schema that the tool form understands. */
export interface JsonSchemaProperty {
  type?: string;
  enum?: unknown[];
  $ref?: string;
  description?: string;
  default?: unknown;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
}

export interface ToolInputSchema {
  type?: string;
  properties?: Record<string, JsonSchemaProperty>;
  required?: string[];
  $defs?: Record<string, JsonSchemaProperty>;
}

export interface McpTool {
  name: string;
  description: string;
  inputSchema: ToolInputSchema;
}

export interface McpServerInfo {
  name: string;
  version: string;
  protocolVersion: string | null;
  instructions: string | null;
}

export interface McpToolList {
  server: McpServerInfo;
  tools: McpTool[];
}

export interface McpCallResult {
  isError: boolean;
  /** `structuredContent` of the result. */
  data: unknown;
  /** The text content blocks, joined. */
  text: string;
}
