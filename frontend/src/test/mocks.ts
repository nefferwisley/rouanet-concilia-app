import { vi } from 'vitest';

export const mockUseAuth = {
  useAuth: () => ({ token: 'fake-token-123', setToken: vi.fn() }),
};

export const mockUseAPI = {
  useAPI: () => ({
    get: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  }),
};

export const mockUseProjects = {
  useProjects: () => ({
    projetos: [],
    total: 0,
    carregando: false,
    erro: null,
    recarregar: vi.fn(),
  }),
};

export const mockUseImportacoes = {
  useImportacoes: (projeto_id: string) => ({
    importacoes: [],
    total: 0,
    page: 1,
    carregando: false,
    erro: null,
    recarregar: vi.fn(),
  }),
};
