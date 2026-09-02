export interface RegrasPlataforma {
  sistemaOrigem: string;
  rotuloIdentificador: string;
  formatoIdentificador: string;
  identificadorObrigatorio: boolean;
  consultaSalicAtiva: boolean;
}
export const regrasPadrao: RegrasPlataforma = { sistemaOrigem: "SALIC", rotuloIdentificador: "PRONAC", formatoIdentificador: "^[0-9]{4,8}$", identificadorObrigatorio: true, consultaSalicAtiva: true };
const chave = "rc_regras_plataforma";
export function obterRegrasPlataforma(): RegrasPlataforma { try { const salvas = localStorage.getItem(chave); return salvas ? { ...regrasPadrao, ...JSON.parse(salvas) } : regrasPadrao; } catch { return regrasPadrao; } }
export function salvarRegrasPlataforma(regras: RegrasPlataforma) { localStorage.setItem(chave, JSON.stringify(regras)); }