/**
 * Testes para AuditoriaProjeto — cobre as colunas novas (rubrica, saldo
 * restante, numeração) e a correção do bug de status (CONCILIADO_OK, não
 * 'CONCILIADA'/'OK', que não existem no enum e quebrariam o filtro real).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { AuditoriaProjeto } from './AuditoriaProjeto';
import { mockDownload, mockGet, mockPost } from '../test/setup';
import { ApiError } from '../lib/api';

const mockAuditoria = {
  resumo: {
    total: 2,
    orcado: 100000,
    debitado: 15000,
    saldo: 85000,
    com_docs: 1,
    sem_docs: 1,
    por_status: [{ status: 'CONCILIADO_OK', total: 1 }],
    total_filtrado: 2,
  },
  transacoes: [
    {
      id: 'trans-1',
      fornecedor: 'Mônica Guimarães',
      data_pagamento: '2022-11-04',
      valor_bruto: 11000,
      tem_nf: true,
      tem_comprovante: true,
      status: 'CONCILIADO_OK',
      rubrica_codigo: '1.5.1',
      rubrica_descricao: 'Produtora Executiva',
      documento: 'nota.pdf',
      saldo_restante: 824000,
      documentos: [
        { id: 'doc-1', tipo: 'NFE', arquivo_ref: 'nota.pdf', disponivel: true },
      ],
    },
    {
      id: 'trans-2',
      fornecedor: 'Fornecedor Sem Rubrica',
      data_pagamento: '2022-11-05',
      valor_bruto: 500,
      tem_nf: false,
      tem_comprovante: false,
      status: 'PENDENTE',
      rubrica_codigo: null,
      rubrica_descricao: null,
      documento: null,
      saldo_restante: 823500,
      documentos: [
        { id: 'doc-2', tipo: 'OUTRO', arquivo_ref: 'ausente.pdf', disponivel: false },
      ],
    },
  ],
  paginacao: { page: 1, limit: 20, total: 2 },
};

class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readyState = FakeWebSocket.OPEN;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn((code?: number, _reason?: string) => {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.({ code: code ?? 1000 } as CloseEvent);
  });

  constructor(public readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  emitirQueda(code = 1006) {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.({ code } as CloseEvent);
  }

  emitirErro() {
    this.onerror?.();
  }

  emitirMensagem(data: string) {
    this.onmessage?.({ data } as MessageEvent);
  }
}

describe('AuditoriaProjeto', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockGet.mockResolvedValue(mockAuditoria);
    mockPost.mockClear();
    mockPost.mockResolvedValue({ ticket: 'fake-ws-ticket-123' });
    mockDownload.mockClear();
    FakeWebSocket.instances = [];
    vi.stubGlobal('WebSocket', FakeWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('numera os lançamentos sequencialmente (1, 2)', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getAllByText('1')[0]).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  it('mostra a rubrica do lançamento e "sem rubrica" quando ausente', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText('1.5.1')).toBeInTheDocument();
      expect(screen.getByText('sem rubrica')).toBeInTheDocument();
    });
  });

  it('mostra o saldo restante de cada linha', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/824\.000,00/)).toBeInTheDocument();
      expect(screen.getByText(/823\.500,00/)).toBeInTheDocument();
    });
  });

  it('status CONCILIADO_OK aparece com badge OK verde', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      const badges = screen.getAllByText('OK');
      expect(badges.length).toBeGreaterThanOrEqual(1);
      expect(
        badges.some((b) => /emerald|pill-sucesso/.test(b.className))
      ).toBe(true);
    });
  });

  it('solicita ticket efêmero via POST e conecta ao WebSocket sem expor JWT na URL', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/api/v1/projetos/projeto-123/ws-ticket', {});
      expect(FakeWebSocket.instances).toHaveLength(1);
    });

    const wsUrl = FakeWebSocket.instances[0].url;
    expect(wsUrl).toContain('ticket=fake-ws-ticket-123');
    expect(wsUrl).not.toContain('token=');
    expect(wsUrl).not.toContain('fake-token-123');
  });

  it('mantém uma conexão e cancela a reconexão pendente ao desmontar', async () => {
    vi.useFakeTimers();
    const { rerender, unmount } = render(<AuditoriaProjeto projetoId="projeto-123" />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(FakeWebSocket.instances).toHaveLength(1);

    rerender(<AuditoriaProjeto projetoId="projeto-123" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(FakeWebSocket.instances).toHaveLength(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(FakeWebSocket.instances).toHaveLength(1);

    const primeiraConexao = FakeWebSocket.instances[0];
    await act(async () => {
      primeiraConexao.emitirQueda();
      primeiraConexao.emitirQueda();
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(FakeWebSocket.instances).toHaveLength(2);

    const reconexao = FakeWebSocket.instances[1];
    act(() => reconexao.emitirQueda());
    unmount();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it('fecha uma conexão ativa com código 1000 ao desmontar', async () => {
    const { unmount } = render(<AuditoriaProjeto projetoId="projeto-123" />);
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const conexao = FakeWebSocket.instances[0];

    unmount();

    expect(conexao.close).toHaveBeenCalledWith(1000, 'component unmounted');
  });

  it('reconecta exatamente uma vez quando onerror é disparado', async () => {
    vi.useFakeTimers();
    const { unmount } = render(<AuditoriaProjeto projetoId="projeto-123" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(FakeWebSocket.instances).toHaveLength(1);
    const conexao = FakeWebSocket.instances[0];

    act(() => {
      conexao.emitirErro();
      conexao.emitirErro();
    });
    expect(conexao.close).toHaveBeenCalledTimes(1);
    expect(conexao.close).toHaveBeenCalledWith(1000, 'websocket error');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(FakeWebSocket.instances).toHaveLength(2);

    unmount();
  });

  it('ignora eventos de socket obsoleto após reconectar', async () => {
    vi.useFakeTimers();
    const { unmount } = render(<AuditoriaProjeto projetoId="projeto-123" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(FakeWebSocket.instances).toHaveLength(1);
    const primeiraConexao = FakeWebSocket.instances[0];

    await act(async () => {
      primeiraConexao.emitirQueda();
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(FakeWebSocket.instances).toHaveLength(2);

    primeiraConexao.readyState = FakeWebSocket.OPEN;
    act(() => {
      primeiraConexao.emitirErro();
      primeiraConexao.emitirQueda();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(FakeWebSocket.instances).toHaveLength(2);

    unmount();
  });

  it('mantém no máximo uma conexão ativa em React.StrictMode', async () => {
    const { unmount } = render(
      <StrictMode>
        <AuditoriaProjeto projetoId="projeto-123" />
      </StrictMode>,
    );

    await waitFor(() => {
      const conexoesAtivas = FakeWebSocket.instances.filter(
        (conexao) => conexao.readyState < FakeWebSocket.CLOSING,
      );
      expect(conexoesAtivas).toHaveLength(1);
    });

    unmount();
  });

  it('processa evento sincronia_arquivos e recarrega os dados', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));

    const conexao = FakeWebSocket.instances[0];
    act(() => {
      conexao.emitirMensagem(
        JSON.stringify({
          tipo: 'sincronia_arquivos',
          projeto_id: 'projeto-123',
          adicionados: ['comprovante.pdf'],
        }),
      );
    });

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it('ignora mensagem malformada sem disparar erros', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));

    const conexao = FakeWebSocket.instances[0];
    expect(() => {
      act(() => {
        conexao.emitirMensagem('INVALID_JSON{{{');
      });
    }).not.toThrow();

    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it('não agenda reconexão ao receber código 4401 (não autorizado)', async () => {
    vi.useFakeTimers();
    const { unmount } = render(<AuditoriaProjeto projetoId="projeto-123" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(FakeWebSocket.instances).toHaveLength(1);

    const conexao = FakeWebSocket.instances[0];
    act(() => {
      conexao.emitirQueda(4401);
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(FakeWebSocket.instances).toHaveLength(1);

    unmount();
  });

  it('baixa documento disponível ao clicar no botão fiscal', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);
    await waitFor(() => expect(screen.getByText(/NF:\s*nota\.pdf/i)).toBeInTheDocument());

    const docBtn = screen.getByText(/NF:\s*nota\.pdf/i);
    await act(async () => {
      docBtn.click();
    });

    expect(mockDownload).toHaveBeenCalledWith('/api/v1/documentos/doc-1/arquivo', 'nota.pdf');
  });

  it('alerta usuário sem chamar download quando documento está indisponível', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);
    await waitFor(() => expect(screen.getByText(/Doc:\s*ausente\.pdf/i)).toBeInTheDocument());

    const docBtn = screen.getByText(/Doc:\s*ausente\.pdf/i);
    await act(async () => {
      docBtn.click();
    });

    expect(await screen.findByText('O arquivo não está disponível. Sincronize a pasta ou anexe-o novamente.')).toBeInTheDocument();
    expect(mockDownload).not.toHaveBeenCalled();
  });

  it('trata erro no download de documento sem expor mensagem bruta', async () => {
    mockDownload.mockRejectedValueOnce(new Error('Documento não encontrado no storage'));

    render(<AuditoriaProjeto projetoId="projeto-123" />);
    await waitFor(() => expect(screen.getByText(/NF:\s*nota\.pdf/i)).toBeInTheDocument());

    const docBtn = screen.getByText(/NF:\s*nota\.pdf/i);
    await act(async () => {
      docBtn.click();
    });

    expect(await screen.findByText('Não foi possível abrir o arquivo. Tente novamente.')).toBeInTheDocument();
  });

  it('impede download duplicado e preserva basename acentuado', async () => {
    let resolverDownload: (() => void) | undefined;
    mockGet.mockResolvedValue({
      ...mockAuditoria,
      transacoes: [{
        ...mockAuditoria.transacoes[0],
        documentos: [{ id: 'doc-acento', tipo: 'NFE', arquivo_ref: 'pasta/nota-áç.pdf', disponivel: true }],
      }],
    });
    mockDownload.mockReturnValue(new Promise<void>((resolve) => { resolverDownload = resolve; }));
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    const botao = await screen.findByRole('button', { name: /NF: nota-áç\.pdf/i });
    fireEvent.click(botao);
    fireEvent.click(botao);

    expect(mockDownload).toHaveBeenCalledTimes(1);
    expect(mockDownload).toHaveBeenCalledWith('/api/v1/documentos/doc-acento/arquivo', 'nota-áç.pdf');
    await act(async () => resolverDownload?.());
  });

  it.each([
    [403, 'Você não tem permissão para abrir este arquivo.'],
    [404, 'O arquivo não está disponível. Sincronize a pasta ou anexe-o novamente.'],
  ])('mostra mensagem acionável para erro %i sem expor caminho', async (status, mensagem) => {
    mockDownload.mockRejectedValue(new ApiError(status, 'projeto/comprovantes/privado.pdf'));
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    fireEvent.click(await screen.findByText(/NF:\s*nota\.pdf/i));

    expect(await screen.findByText(mensagem)).toBeInTheDocument();
    expect(screen.queryByText(/projeto\/comprovantes/i)).not.toBeInTheDocument();
  });

  it('usa os endpoints do extrato por projeto e revoga a URL da prévia', async () => {
    const createObjectURL = vi.fn(() => 'blob:preview');
    const revokeObjectURL = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'image/png' },
      blob: async () => new Blob(['preview']),
    });
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
    vi.stubGlobal('fetch', fetchMock);
    mockGet.mockResolvedValue({
      ...mockAuditoria,
      transacoes: [{
        ...mockAuditoria.transacoes[0],
        movimento_extrato: { id: 'extrato-1', data: '2022-11-04', documento: 'extrato-áç.pdf', historico: 'Teste', valor: 10 },
      }],
    });
    const { unmount } = render(<AuditoriaProjeto projetoId="projeto-123" />);

    const botao = await screen.findByTitle('Extrato Bancário: extrato-áç.pdf');
    fireEvent.mouseEnter(botao);
    await waitFor(() => expect(createObjectURL).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/projetos/projeto-123/extratos/thumbnail');

    fireEvent.click(botao);
    expect(mockDownload).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/projetos/projeto-123/extratos/arquivo'),
      'extrato-áç.pdf',
    );
    unmount();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:preview');
  });
});
