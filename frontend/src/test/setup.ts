import '@testing-library/jest-dom';
import { vi } from 'vitest';

export const mockGet = vi.fn().mockResolvedValue({});
export const mockPatch = vi.fn().mockResolvedValue({});
export const mockPatchForm = vi.fn().mockResolvedValue({});
export const mockPost = vi.fn().mockResolvedValue({});
export const mockPostForm = vi.fn().mockResolvedValue({});
export const mockDelete = vi.fn().mockResolvedValue({});
export const mockDownload = vi.fn().mockResolvedValue(undefined);

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ token: 'fake-token-123', setToken: vi.fn() }),
}));

vi.mock('../hooks/useAPI', () => ({
  useAPI: () => ({
    get: mockGet,
    patch: mockPatch,
    patchForm: mockPatchForm,
    post: mockPost,
    postForm: mockPostForm,
    delete: mockDelete,
    download: mockDownload,
  }),
}));

vi.mock('../hooks/useProjects', () => ({
  useProjects: () => ({
    projetos: [],
    total: 0,
    carregando: false,
    erro: null,
    recarregar: vi.fn(),
  }),
}));

vi.mock('../hooks/useImportacoes', () => ({
  useImportacoes: (projeto_id: string) => ({
    importacoes: [],
    total: 0,
    page: 1,
    carregando: false,
    erro: null,
    recarregar: vi.fn(),
  }),
}));

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock);
