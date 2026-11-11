import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { MCP_URL } from '@/api/mcp';
import { mcpRequests } from '@/test/handlers';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/utils';

import { ToolsPage } from './ToolsPage';

function toolCard(name: string) {
  return screen.getByRole('region', { name });
}

describe('ToolsPage', () => {
  it('lists the tools from the MCP server and labels them as MCP tools', async () => {
    renderWithProviders(<ToolsPage />);

    expect(await screen.findByRole('heading', { name: 'get_trip_stats' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'calculate_emissions' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'MCP tools' })).toBeInTheDocument();
    expect(within(toolCard('get_trip_stats')).getByText('MCP tool')).toBeInTheDocument();
    expect(screen.getByText(/This page is an/)).toHaveTextContent('MCP client');
    expect(screen.getByText(MCP_URL)).toBeInTheDocument();
    expect(screen.getByText('ecoroute 0.1.0')).toBeInTheDocument();
    // A real MCP handshake, then tools/list.
    expect(mcpRequests.map((m) => m.method)).toEqual([
      'initialize',
      'notifications/initialized',
      'tools/list',
    ]);
  });

  it('runs a tool with tools/call and shows the request and the quoted values', async () => {
    const { user } = renderWithProviders(<ToolsPage />);
    await screen.findByRole('heading', { name: 'get_trip_stats' });
    const card = toolCard('get_trip_stats');

    await user.selectOptions(within(card).getByLabelText('Range (optional)'), '30d');
    await user.click(within(card).getByRole('button', { name: 'Run get_trip_stats' }));

    const list = await within(card).findByLabelText('Ready-to-quote values');
    expect(list).toHaveTextContent('co2 footprint270.0 kg');
    expect(list).toHaveTextContent('co2 saved vs petrol car152.2 kg less');
    expect(within(card).getByText(/"method": "tools\/call"/)).toHaveTextContent('"range": "30d"');
    expect(mcpRequests.at(-1)).toMatchObject({
      method: 'tools/call',
      params: { name: 'get_trip_stats', arguments: { range: '30d' } },
    });
  });

  it('shows a tool error result from the server', async () => {
    const { user } = renderWithProviders(<ToolsPage />);
    await screen.findByRole('heading', { name: 'calculate_emissions' });
    const card = toolCard('calculate_emissions');

    await user.type(within(card).getByLabelText('Distance km'), '5');
    await user.click(within(card).getByRole('button', { name: 'Run calculate_emissions' }));

    expect(await within(card).findByRole('alert')).toHaveTextContent(
      'Tool error (isError: true): Invalid arguments',
    );
  });

  it('checks required arguments before calling the server', async () => {
    const { user } = renderWithProviders(<ToolsPage />);
    await screen.findByRole('heading', { name: 'calculate_emissions' });
    const card = toolCard('calculate_emissions');

    await user.click(within(card).getByRole('button', { name: 'Run calculate_emissions' }));

    expect(within(card).getByText('Required.')).toBeInTheDocument();
    expect(mcpRequests.some((m) => m.method === 'tools/call')).toBe(false);
  });

  it('shows an error with Try again when the MCP server is down', async () => {
    server.use(http.post(MCP_URL, () => HttpResponse.error()));
    renderWithProviders(<ToolsPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent("Can't reach the EcoRoute MCP server");
    expect(within(alert).getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});
