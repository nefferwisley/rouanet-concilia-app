"""Testes do gerador de dry-run do OpenCode."""

from scripts.orquestrar_opencode import gerar_plano, parsear_fases


def test_fase_cinco_seleciona_somente_tarefas_opencode() -> None:
    plano = gerar_plano([5])

    assert plano["modo"] == "dry-run"
    assert plano["executor"] == "opencode"
    assert plano["total_tarefas"] == 2
    assert all(tarefa["executor_ideal"] == "opencode" for tarefa in plano["tarefas"])
    assert plano["garantias"] == {
        "executou_opencode": False,
        "executou_shell": False,
        "alterou_codigo": False,
        "iniciou_subagentes": False,
    }


def test_ordem_respeita_dependência_entre_tarefas_de_ui() -> None:
    plano = gerar_plano([5])

    assert plano["ordem_execução"] == [
        "fase5_ui_tabela_lançamentos",
        "fase5_ui_edição_auditoria",
    ]
    assert "fase4_sync_bidirecional" in plano["dependências_externas"]


def test_parseia_intervalo_de_fases() -> None:
    assert parsear_fases("4-6") == [4, 5, 6]
