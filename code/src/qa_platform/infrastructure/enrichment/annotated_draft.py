"""Modelos Pydantic da borda de enriquecimento (Fase 2).

O ``Annotated_Draft`` é a saída da Fase 2 — uma borda externa/serialização —
então Pydantic é apropriado aqui (steering 12: "Pydantic na fronteira"),
**não** no domínio. Este módulo é infraestrutura de borda e **não** importa
``agno`` (esse import vive apenas em ``llm_enricher.py``).

Invariantes principais (Requisito 7):

- Cada saída do LLM vira uma :class:`Suggestion` marcada com ``origin``
  (``"sugestão"`` para ``expected_domain`` — Req 7.1; ``"candidato"`` para cada
  ``GoldenCase`` — Req 7.2) e ``state="pendente"``.
- :attr:`AnnotatedDraft.base_fields` é uma cópia **fiel** do Draft de entrada e
  nunca é alterada pelo enricher (invariante da Propriedade 6).
- A resolução (Req 7.5) aplica **exatamente uma** das três ações
  ``{aceitar, editar, descartar}``, transicionando ``state`` de ``"pendente"``
  para ``aceito``/``editado``/``descartado`` respectivamente. Ações inválidas
  não alteram o estado (comportamento validado pela Propriedade 7).
"""

from typing import Literal

from pydantic import BaseModel

__all__ = [
    "AnnotatedDraft",
    "ResolutionAction",
    "Suggestion",
    "SuggestionField",
    "SuggestionOrigin",
    "SuggestionState",
]

# Aliases de tipo para os conjuntos fechados usados nas anotações Literal.
SuggestionField = Literal["expected_domain", "golden_set"]
SuggestionOrigin = Literal["sugestão", "candidato"]
SuggestionState = Literal["pendente", "aceito", "editado", "descartado"]
ResolutionAction = Literal["aceitar", "editar", "descartar"]

# Mapa determinístico ação -> estado resultante (Req 7.5). A resolução aplica
# exatamente uma ação; qualquer chave fora deste conjunto é inválida e não
# altera o estado.
_ACTION_TO_STATE: dict[str, SuggestionState] = {
    "aceitar": "aceito",
    "editar": "editado",
    "descartar": "descartado",
}


class Suggestion(BaseModel):
    """Uma sugestão marcada, resolvida conscientemente pelo Developer (Req 7).

    Campos:
        field: campo do manifesto ao qual a sugestão se refere
            (``expected_domain`` ou ``golden_set``).
        value: valor sugerido — ``str`` para ``expected_domain`` ou ``dict`` do
            ``GoldenCase`` para ``golden_set``.
        origin: origem do achado — ``"sugestão"`` para ``expected_domain``
            (Req 7.1) e ``"candidato"`` para cada ``GoldenCase`` (Req 7.2).
        state: estado da resolução; começa em ``"pendente"`` e transiciona via
            :meth:`resolve` (Req 7.5).
    """

    field: SuggestionField
    value: object
    origin: SuggestionOrigin
    state: SuggestionState = "pendente"

    def resolve(
        self, action: ResolutionAction, *, value: object | None = None
    ) -> "Suggestion":
        """Aplica exatamente uma ação, transicionando ``state`` (Req 7.5).

        Aplica **uma** das três ações ``{aceitar, editar, descartar}`` a uma
        sugestão ``"pendente"``, retornando uma nova :class:`Suggestion` com o
        estado correspondente (``aceito``/``editado``/``descartado``). A ação
        ``editar`` pode substituir o ``value``; ``aceitar``/``descartar``
        preservam o valor.

        Ações inválidas (fora do conjunto) ou sugestões que não estão
        ``"pendente"`` não alteram o estado — retornam uma cópia inalterada,
        garantindo que apenas transições válidas a partir de ``"pendente"``
        tenham efeito.

        Args:
            action: ação de resolução escolhida pelo Developer.
            value: novo valor a aplicar quando ``action == "editar"``; ignorado
                para as demais ações.

        Returns:
            Nova :class:`Suggestion` com o estado resultante. Instância original
            permanece inalterada (transição imutável).
        """
        new_state = _ACTION_TO_STATE.get(action)
        if new_state is None or self.state != "pendente":
            # Ação inválida ou entrada já resolvida: estado não muda.
            return self.model_copy()

        if action == "editar" and value is not None:
            return self.model_copy(update={"state": new_state, "value": value})
        return self.model_copy(update={"state": new_state})


class AnnotatedDraft(BaseModel):
    """Saída da Fase 2: Draft determinístico + sugestões marcadas (Req 7).

    Campos:
        base_fields: cópia **fiel** do Draft de entrada. O enricher nunca a
            altera, remove ou reordena (invariante da Propriedade 6, Req 7.3).
        suggestions: sugestões marcadas produzidas pela Fase 2; cada uma entra
            como entrada separada, mesmo quando o Draft já traz valor não vazio
            para o campo (Req 7.4).
    """

    base_fields: dict[str, object]
    suggestions: list[Suggestion] = []

    def to_json(self) -> str:
        """Serializa o Annotated_Draft em JSON determinístico.

        Usa a serialização do Pydantic preservando unicode (``ensure_ascii``
        desligado internamente pelo dumper JSON do Pydantic) para manter
        acentos em ``"sugestão"``/``"descartado"`` legíveis. A ordem dos campos
        de ``base_fields`` e das sugestões é preservada tal como recebida.

        Returns:
            Representação JSON (``str``) do Annotated_Draft.
        """
        return self.model_dump_json()
