// A real MCP client: talks JSON-RPC to the backend's MCP server over Streamable HTTP.
// It does not use the REST API, so the page shows what any AI agent connected to EcoRoute sees.
import { Client, StreamableHTTPClientTransport } from '@modelcontextprotocol/client';

import type {
  McpCallResult,
  McpServerInfo,
  McpTool,
  McpToolList,
  ToolInputSchema,
} from '@/types/mcp';

import { API_URL, ApiError } from './client';

/** The MCP endpoint sits next to the REST API, e.g. http://localhost:8000/mcp. */
export const MCP_URL = new URL('/mcp', API_URL).toString();

const CLIENT_INFO = { name: 'ecoroute-web', version: '0.1.0' };

let connection: Promise<Client> | null = null;

function connect(): Promise<Client> {
  connection ??= (async () => {
    const client = new Client(CLIENT_INFO);
    await client.connect(new StreamableHTTPClientTransport(new URL(MCP_URL)));
    return client;
  })().catch((error: unknown) => {
    connection = null;
    throw error;
  });
  return connection;
}

/** Runs `run` on the shared session; a protocol or network failure drops the session so the
 * next call reconnects. Tool errors are results (`isError`), not exceptions. */
async function withClient<T>(run: (client: Client) => Promise<T>): Promise<T> {
  let client: Client;
  try {
    client = await connect();
  } catch (error) {
    throw unavailable(error);
  }
  try {
    return await run(client);
  } catch (error) {
    connection = null;
    void client.close().catch(() => undefined);
    throw unavailable(error);
  }
}

function unavailable(error: unknown): ApiError {
  const message = error instanceof Error ? error.message : String(error);
  return new ApiError(0, 'MCP_UNAVAILABLE', message);
}

/** Forget the session (tests use it to start every test with a fresh handshake). */
export function resetMcpConnection(): void {
  const current = connection;
  connection = null;
  void current?.then((client) => client.close()).catch(() => undefined);
}

function serverInfo(client: Client): McpServerInfo {
  const version = client.getServerVersion();
  return {
    name: version?.name ?? 'unknown',
    version: version?.version ?? '',
    protocolVersion: client.getNegotiatedProtocolVersion() ?? null,
    instructions: client.getInstructions() ?? null,
  };
}

export const mcpApi = {
  /** `tools/list` */
  listTools: (): Promise<McpToolList> =>
    withClient(async (client) => {
      const { tools } = await client.listTools();
      return {
        server: serverInfo(client),
        tools: tools.map((tool): McpTool => ({
          name: tool.name,
          description: tool.description ?? '',
          // Untyped JSON from the server; the form only reads the parts it understands.
          inputSchema: tool.inputSchema as ToolInputSchema,
        })),
      };
    }),

  /** `tools/call` */
  callTool: (name: string, args: Record<string, unknown>): Promise<McpCallResult> =>
    withClient(async (client) => {
      const result = await client.callTool({ name, arguments: args });
      const text = result.content
        .map((block) => (block.type === 'text' ? block.text : ''))
        .join('\n');
      return { isError: result.isError ?? false, data: result.structuredContent ?? null, text };
    }),
};
