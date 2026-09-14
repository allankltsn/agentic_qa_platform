"""Erros tipados da borda de enriquecimento (Fase 2, infraestrutura).

Estes erros vivem no pacote de enriquecimento para manter o ``LLM_Enricher``
(tarefa 8.3) **self-contained** e evitar acoplamento de camadas: a
infraestrutura não deve depender de ``application`` para levantar seus próprios
erros. A tarefa 9.1 (caso de uso ``suggest_manifest`` em ``application/``) pode
re-exportar ou envelopar estes tipos como ``EnrichmentError`` da aplicação,
mantendo ``application`` livre de ``agno``.

Nenhum erro carrega valor de segredo; descrevem apenas a condição de falha
(Requisitos 9.2, 9.3). O fail-fast do provider ausente/blank continua sendo
sinalizado por ``MissingSecretError`` (do ``SecretResolver``), que nomeia SOMENTE
o nome da variável de ambiente.
"""

from __future__ import annotations

__all__ = [
    "EnrichmentError",
    "EnrichmentTimeoutError",
    "ScopeRejectedError",
]


class EnrichmentError(RuntimeError):
    """Base dos erros da Fase 2 de enriquecimento (infraestrutura).

    Não carrega valores de segredo; descreve apenas a condição de falha do
    enricher, permitindo que a fronteira (caso de uso/CLI) a trate como uma
    recusa de enriquecimento sem vazar detalhes internos (Req 6.6).
    """


class EnrichmentTimeoutError(EnrichmentError):
    """O enricher não retornou o ``AnnotatedDraft`` dentro do timeout duro.

    Levantado quando a invocação do provider de LLM excede o limite de tempo
    configurado (padrão 120s), abortando o enriquecimento sem produzir
    ``AnnotatedDraft`` parcial e mantendo o Draft de entrada inalterado
    (Requisito 6.6).
    """


class ScopeRejectedError(EnrichmentError):
    """Conteúdo rejeitado pelo guardrail de escopo mínimo do enricher.

    Levantado quando o guardrail (baseline do portfólio) bloqueia a chamada por
    conteúdo fora do escopo de "descoberta de alvo de QA" — sugerir
    ``expected_domain``/``golden_set``. A chamada é rejeitada sem aplicar
    qualquer sugestão (Requisito 9.5). Mensagem neutra, sem vazar interno.
    """
