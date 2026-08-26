import { act, render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useImportacaoWebSocket } from './useWebSocket';
import { mockPost } from '../test/setup';

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  close = vi.fn();

  constructor(public readonly url: string) {
    FakeWebSocket.instances.push(this);
  }
}

function Sonda({ importacaoId }: { importacaoId: string | null }) {
  useImportacaoWebSocket(importacaoId, vi.fn());
  return null;
}

describe('useImportacaoWebSocket', () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    mockPost.mockReset();
    vi.stubGlobal('WebSocket', FakeWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('solicita ticket autenticado e não expõe token na URL', async () => {
    mockPost.mockResolvedValue({ ticket: 'ticket-efemero' });

    render(<Sonda importacaoId="importacao-123" />);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/api/v1/importacoes/importacao-123/ws-ticket', {});
      expect(FakeWebSocket.instances).toHaveLength(1);
    });
    expect(FakeWebSocket.instances[0].url).toContain('?ticket=ticket-efemero');
    expect(FakeWebSocket.instances[0].url).not.toContain('fake-token-123');
  });

  it('não conecta tardiamente quando desmonta durante a solicitação do ticket', async () => {
    let resolverTicket: ((value: { ticket: string }) => void) | undefined;
    mockPost.mockReturnValue(new Promise((resolve) => { resolverTicket = resolve; }));
    const { unmount } = render(<Sonda importacaoId="importacao-123" />);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledTimes(1);
    });
    unmount();
    await act(async () => {
      resolverTicket?.({ ticket: 'ticket-tardio' });
    });

    expect(FakeWebSocket.instances).toHaveLength(0);
  });
});
