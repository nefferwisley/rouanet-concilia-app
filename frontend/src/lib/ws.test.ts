import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { conectarWsImportacao } from './ws';

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onmessage: ((event: MessageEvent) => void) | null = null;
  close = vi.fn();

  constructor(public readonly url: string) {
    FakeWebSocket.instances.push(this);
  }
}

describe('conectarWsImportacao', () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    vi.stubGlobal('WebSocket', FakeWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('usa somente o ticket efêmero na URL do WebSocket', () => {
    conectarWsImportacao('importacao-123', 'ticket-temporario', vi.fn());

    expect(FakeWebSocket.instances).toHaveLength(1);
    const url = FakeWebSocket.instances[0].url;
    expect(url).toContain('/ws/importacao/importacao-123?ticket=ticket-temporario');
    expect(url).not.toContain('?token=');
    expect(url).not.toContain('&token=');
  });
});
