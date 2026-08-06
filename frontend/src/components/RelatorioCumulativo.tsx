import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

interface Props {
  ok: number;
  erro: number;
  alerta: number;
}

export function RelatorioCumulativo({ ok, erro, alerta }: Props) {
  const dados = [
    { nome: "OK", valor: ok, fill: "#10b981" },
    { nome: "ERRO", valor: erro, fill: "#ef4444" },
    { nome: "ALERTA", valor: alerta, fill: "#fbbf24" },
  ].filter((d) => d.valor > 0);

  if (dados.length === 0) {
    return <p className="text-sm text-slate-500">Sem dados suficientes pra gerar o gráfico ainda.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={dados} dataKey="valor" nameKey="nome" cx="50%" cy="50%" outerRadius={90} label>
          {dados.map((entry) => (
            <Cell key={entry.nome} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
