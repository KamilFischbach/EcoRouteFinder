import { useMutation, useQuery } from '@tanstack/react-query';

import { mcpApi } from '@/api/mcp';

export const mcpKeys = {
  all: ['mcp'] as const,
  tools: () => [...mcpKeys.all, 'tools'] as const,
};

/** `tools/list` on the EcoRoute MCP server. */
export function useMcpToolsQuery() {
  return useQuery({ queryKey: mcpKeys.tools(), queryFn: () => mcpApi.listTools() });
}

/** `tools/call`; every tool card has its own mutation. */
export function useCallMcpTool() {
  return useMutation({
    mutationFn: ({ name, args }: { name: string; args: Record<string, unknown> }) =>
      mcpApi.callTool(name, args),
  });
}
