import React, { useState } from "react";
import {
  X,
  Printer,
  Copy,
  CheckCircle2,
  FileText,
  Calculator,
  ShieldCheck,
} from "lucide-react";
import { formatCurrency } from "../utils/formatters";
import { calcularRetencoesTributarias, TaxCalculationResult } from "../utils/taxRetentionCalculator";
import { TransacaoAuditoria } from "../lib/auditoria";

interface TaxRetentionDarfModalProps {
  isOpen: boolean;
  onClose: () => void;
  transaction: TransacaoAuditoria | null;
  projetoNome?: string;
  pronac?: string;
}

export const TaxRetentionDarfModal: React.FC<TaxRetentionDarfModalProps> = ({
  isOpen,
  onClose,
  transaction,
}) => {
  if (!isOpen || !transaction) return null;

  const [tipoPessoa, setTipoPessoa] = useState<"PF" | "PJ">("PF");
  const [dependentes, setDependentes] = useState(0);
  const [aliquotaIss, setAliquotaIss] = useState(0.05);
  const [copied, setCopied] = useState(false);

  const txVal = Number(transaction.valor_bruto) || 0;
  const estimativaBruto = txVal > 0 ? txVal : 5000;

  const calculo: TaxCalculationResult = calcularRetencoesTributarias({
    valorBruto: estimativaBruto,
    tipoPessoa,
    temInssAutonomo: true,
    aliquotaIss,
    dependentes,
  });

  const handleCopyLinha = () => {
    navigator.clipboard.writeText(calculo.linhaDigitavelDarf);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Memória de Cálculo de Retenções & Emissão de DARF
              </h2>
              <p className="text-xs text-slate-400">
                Padrão Receita Federal / MinC — Pagamento na Conta Movimento BB
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6 overflow-y-auto max-h-[70vh] text-xs">
          {/* Left: Input parameters */}
          <div className="space-y-4">
            <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-3">
              <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-2">
                <FileText className="w-4 h-4 text-amber-400" /> Parâmetros do Prestador
              </h3>

              <div>
                <label className="text-slate-400 block mb-1">Enquadramento do Prestador</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setTipoPessoa("PF")}
                    className={`py-2 px-3 rounded-lg border text-xs font-bold transition ${
                      tipoPessoa === "PF"
                        ? "bg-amber-500/20 text-amber-300 border-amber-500/50"
                        : "bg-slate-900 text-slate-400 border-slate-800"
                    }`}
                  >
                    Pessoa Física (RPA)
                  </button>
                  <button
                    type="button"
                    onClick={() => setTipoPessoa("PJ")}
                    className={`py-2 px-3 rounded-lg border text-xs font-bold transition ${
                      tipoPessoa === "PJ"
                        ? "bg-amber-500/20 text-amber-300 border-amber-500/50"
                        : "bg-slate-900 text-slate-400 border-slate-800"
                    }`}
                  >
                    Pessoa Jurídica (NF-e)
                  </button>
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Alíquota de ISS Municipal</label>
                <select
                  value={aliquotaIss}
                  onChange={(e) => setAliquotaIss(parseFloat(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2"
                >
                  <option value={0.02}>2% (Mínimo Legal)</option>
                  <option value={0.03}>3% (Padrão Serviços Culturais)</option>
                  <option value={0.05}>5% (Alíquota Máxima)</option>
                </select>
              </div>

              {tipoPessoa === "PF" && (
                <div>
                  <label className="text-slate-400 block mb-1">Dependentes Legais (Dedução IRRF)</label>
                  <input
                    type="number"
                    min={0}
                    max={10}
                    value={dependentes}
                    onChange={(e) => setDependentes(parseInt(e.target.value) || 0)}
                    className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 font-mono"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Right: Tax Breakdown & DARF Card */}
          <div className="space-y-4">
            <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-3">
              <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" /> Discriminação de Retenções
              </h3>

              <div className="space-y-2">
                <div className="flex justify-between py-1 border-b border-slate-800/80">
                  <span className="text-slate-400">Valor Bruto Pactuado:</span>
                  <span className="font-mono font-bold text-white">{formatCurrency(calculo.valorBruto)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800/80">
                  <span className="text-slate-400">(-) INSS Retido (11%):</span>
                  <span className="font-mono text-amber-400">-{formatCurrency(calculo.inssRetido)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800/80">
                  <span className="text-slate-400">(-) IRRF na Fonte:</span>
                  <span className="font-mono text-amber-400">-{formatCurrency(calculo.irrfRetido)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800/80">
                  <span className="text-slate-400">(-) ISSQN Municipal:</span>
                  <span className="font-mono text-amber-400">-{formatCurrency(calculo.issRetido)}</span>
                </div>
                <div className="flex justify-between py-1.5 bg-emerald-500/10 px-2 rounded-lg font-bold">
                  <span className="text-emerald-300">(=) Valor Líquido a Pagar:</span>
                  <span className="font-mono text-emerald-400">{formatCurrency(calculo.valorLiquido)}</span>
                </div>
              </div>
            </div>

            {/* DARF Box */}
            <div className="bg-amber-500/10 border border-amber-500/30 p-4 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-amber-300 uppercase">Guia DARF (Código {calculo.darfCodigoReceita})</span>
                <span className="text-[10px] text-amber-400 font-mono">Vencimento: {calculo.darfVencimento}</span>
              </div>
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-200 break-all flex items-center justify-between gap-2">
                <span>{calculo.linhaDigitavelDarf}</span>
                <button
                  onClick={handleCopyLinha}
                  className="p-1 text-amber-400 hover:text-amber-300 shrink-0"
                  title="Copiar linha digitável"
                >
                  {copied ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950/60">
          <div className="text-slate-500 text-[11px]">
            * Pague esta guia até o dia 20 através da Conta Movimento BB para evitar glosas.
          </div>
          <button
            onClick={() => window.print()}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-xl flex items-center gap-1.5 transition font-semibold"
          >
            <Printer className="w-4 h-4" />
            <span>Imprimir Memória de Cálculo</span>
          </button>
        </div>
      </div>
    </div>
  );
};
