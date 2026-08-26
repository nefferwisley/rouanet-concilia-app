/**
 * Digital Signature & Dispatch Service (Gov.br / WhatsApp / ZapSign)
 * Padrão de Validade Jurídica MP 2.200-2/2001 e Decreto 10.543/2020 (Gov.br Prata/Ouro)
 */

export interface SignatureDispatchRequest {
  receiptId: string;
  transacaoId: string;
  favorecidoNome: string;
  favorecidoTelefone?: string;
  favorecidoEmail?: string;
  responsavelNome: string;
  responsavelTelefone?: string;
  valor: number;
  funcaoOuServico: string;
  projetoNome: string;
  pronac: string;
}

export interface SignatureDispatchResult {
  success: boolean;
  token: string;
  signatureUrl: string;
  govBrSignUrl: string;
  whatsappMessageText: string;
  whatsappDirectLink: string;
  dispatchedAt: string;
}

/**
 * Gera os links de assinatura digital com suporte ao assinador oficial Gov.br e disparo via WhatsApp
 */
export function generateDigitalSignatureDispatch(req: SignatureDispatchRequest): SignatureDispatchResult {
  const token = `sig_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  const baseUrl = typeof window !== "undefined" ? window.location.origin : "http://localhost:5173";
  const signatureUrl = `${baseUrl}/assinar/${token}`;

  // Link para o Assinador Eletrônico Oficial do Governo Federal (Gratuito - ITI / Gov.br)
  const govBrSignUrl = `https://assinador.iti.br/assinatura/index.xhtml`;

  // Mensagem padronizada e profissional para WhatsApp
  const textoMsg = encodeURIComponent(
    `Olá, *${req.favorecidoNome}*!\n\n` +
    `Aqui é da produção do projeto cultural *${req.projetoNome}* (PRONAC ${req.pronac}).\n\n` +
    `Emitimos o seu *Recibo de Pagamento* no valor líquido de *R$ ${req.valor.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}* referente a _${req.funcaoOuServico}_.\n\n` +
    `Para concluir a prestação de contas no MinC, solicitamos sua assinatura digital pelo link abaixo:\n` +
    `🔗 ${signatureUrl}\n\n` +
    `*(Você também pode assinar gratuitamente usando sua conta Gov.br pelo Assinador ITI: ${govBrSignUrl})*\n\n` +
    `Responsável pela coleta: *${req.responsavelNome}*`
  );

  const foneLimpo = (req.favorecidoTelefone || "").replace(/\D/g, "");
  const whatsappDirectLink = foneLimpo
    ? `https://api.whatsapp.com/send?phone=55${foneLimpo}&text=${textoMsg}`
    : `https://api.whatsapp.com/send?text=${textoMsg}`;

  return {
    success: true,
    token,
    signatureUrl,
    govBrSignUrl,
    whatsappMessageText: decodeURIComponent(textoMsg),
    whatsappDirectLink,
    dispatchedAt: new Date().toISOString(),
  };
}
