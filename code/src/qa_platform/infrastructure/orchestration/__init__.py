"""Orchestration: registro de camadas e primitivos de orquestração (infra).

Pacote de infraestrutura que hospeda o ponto de extensão do roteamento
(``LayerRegistry``) e, futuramente, os primitivos de orquestração (Router,
Cost_Condition, Parallel_Runner, Workflow). Os tipos do framework de orquestração
(Agno) ficam confinados a este pacote — não vazam para o domínio (Requisito 12.2).
"""
