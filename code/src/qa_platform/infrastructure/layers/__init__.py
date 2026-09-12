"""Layers: implementações concretas de QA_Layers (infraestrutura).

Pacote de infraestrutura que hospeda as ``QA_Layer`` concretas que implementam o
``QALayerContract`` do domínio. Nesta fase contém apenas a ``AILayerStub``, a
camada de IA mínima que prova a extensibilidade do roteamento sem integrar
ferramentas reais de avaliação/red teaming.

Qualquer tipo de framework de agentes (ex.: Agno) usado por uma camada fica
**confinado a este pacote** — nunca vaza para o domínio (Requisitos 7.3, 12.2).
O import-linter restringe o import de ``agno`` a
``qa_platform.infrastructure.orchestration.*`` e
``qa_platform.infrastructure.layers.*``.
"""
