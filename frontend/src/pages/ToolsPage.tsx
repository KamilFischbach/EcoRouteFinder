import { getErrorMessage } from '@/api/errors';
import { MCP_URL } from '@/api/mcp';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageHeader } from '@/components/PageHeader';
import { Spinner } from '@/components/Spinner';
import { McpBadge } from '@/features/mcp/McpBadge';
import { McpToolCard } from '@/features/mcp/McpToolCard';
import { useMcpToolsQuery } from '@/features/mcp/useMcp';
import type { McpServerInfo } from '@/types/mcp';

function McpIntro({ server }: { server: McpServerInfo | undefined }) {
  return (
    <Card className="border-indigo-200 bg-indigo-50/50 p-5 sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-base font-semibold text-stone-900">Model Context Protocol (MCP)</h2>
        <McpBadge />
      </div>
      <p className="mt-2 text-sm text-stone-700">
        This page is an <strong>MCP client</strong>. It does not use the REST API: it connects to
        the EcoRoute <strong>MCP server</strong>, asks it for its tools (<code>tools/list</code>)
        and runs them (<code>tools/call</code>). Any AI agent connected to EcoRoute, such as Claude
        Desktop or the MCP Inspector, sees exactly these tools. The numbers come from the same
        deterministic services as the rest of the app, so <code>get_trip_stats</code> matches the
        Dashboard.
      </p>
      <dl className="mt-4 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
        <div className="flex gap-2">
          <dt className="text-stone-500">Endpoint</dt>
          <dd className="font-mono text-xs break-all text-stone-900 sm:text-sm">{MCP_URL}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-stone-500">Transport</dt>
          <dd className="text-stone-900">Streamable HTTP (stdio: python -m app.mcp_server)</dd>
        </div>
        {server && (
          <>
            <div className="flex gap-2">
              <dt className="text-stone-500">Server</dt>
              <dd className="text-stone-900">
                {server.name} {server.version}
              </dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-stone-500">Protocol</dt>
              <dd className="text-stone-900">{server.protocolVersion ?? 'unknown'}</dd>
            </div>
          </>
        )}
      </dl>
    </Card>
  );
}

export function ToolsPage() {
  const tools = useMcpToolsQuery();

  function renderTools() {
    if (tools.isPending) {
      return (
        <div className="flex justify-center py-14 text-emerald-600">
          <Spinner label="Connecting to the MCP server…" />
        </div>
      );
    }
    if (tools.isError) {
      return (
        <Card>
          <ErrorState
            title="Could not connect to the MCP server"
            message={getErrorMessage(tools.error)}
            onRetry={() => void tools.refetch()}
          />
        </Card>
      );
    }
    if (tools.data.tools.length === 0) {
      return (
        <Card>
          <EmptyState title="The MCP server has no tools" />
        </Card>
      );
    }
    return tools.data.tools.map((tool) => <McpToolCard key={tool.name} tool={tool} />);
  }

  return (
    <>
      <PageHeader
        title="MCP tools"
        description="EcoRoute's tools for AI agents, served over the Model Context Protocol. Fill in the arguments and run a tool to see what an agent gets back."
      />
      <div className="space-y-6">
        <McpIntro server={tools.data?.server} />
        {renderTools()}
      </div>
    </>
  );
}
