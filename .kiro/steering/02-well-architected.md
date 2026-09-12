---
inclusion: always
---

# AWS Well-Architected Framework

Checklist acionável com os 6 pilares do Well-Architected, aplicável a todas as soluções serverless do time.

## Excelência Operacional

- ✅ Toda infraestrutura definida como código (AWS SAM, CloudFormation, Terraform)
- ✅ Deploys automatizados via CI/CD — nunca deploy manual em produção
- ✅ Runbooks documentados para operações recorrentes e incidentes conhecidos
- ✅ Playbooks de resposta a incidentes com passos claros de mitigação
- ✅ Observabilidade completa: logs estruturados, traces distribuídos, métricas customizadas
- ✅ Revisões pós-incidente (post-mortem) com ações corretivas rastreáveis
- ✅ Feature flags para deploys progressivos e rollback rápido
- ✅ Versionamento de APIs com estratégia de deprecação definida

## Segurança

- ✅ Princípio do menor privilégio em todas as políticas IAM
- ✅ Criptografia em trânsito (TLS 1.2+) para toda comunicação entre serviços
- ✅ Criptografia em repouso para dados em DynamoDB, S3, SQS, SNS e RDS
- ✅ Rotação automática de segredos via AWS Secrets Manager
- ✅ Rastreabilidade completa com AWS CloudTrail habilitado em todas as contas
- ✅ Validação e sanitização de toda entrada de dados externa
- ✅ WAF configurado em APIs públicas com regras contra OWASP Top 10
- ✅ Security groups e VPC configurados com acesso mínimo necessário
- ✅ Auditoria regular de dependências (`npm audit`, `pip-audit`, `safety`)
- ✅ Nunca expor detalhes internos ou stack traces em respostas de erro

## Confiabilidade

- ✅ Retry com exponential backoff e jitter em chamadas a serviços externos
- ✅ Circuit breaker para proteger contra falhas em cascata
- ✅ Dead Letter Queues (DLQ) configuradas em todas as filas SQS e funções Lambda assíncronas
- ✅ Idempotência em handlers Lambda — processar a mesma mensagem múltiplas vezes sem efeitos colaterais
- ✅ Timeouts explícitos em todas as chamadas HTTP e SDK
- ✅ Health checks e readiness probes em serviços com estado
- ✅ Multi-AZ habilitado para recursos com estado (RDS, ElastiCache)
- ✅ Testes de carga e chaos engineering em ambientes de staging
- ✅ Plano de disaster recovery documentado com RTO e RPO definidos

## Eficiência de Performance

- ✅ Right-sizing de Lambda: memória ajustada com base em profiling (Lambda Power Tuning)
- ✅ Caching em camadas: API Gateway cache, DAX para DynamoDB, ElastiCache para dados frequentes
- ✅ Conexões reutilizáveis: clientes SDK inicializados fora do handler (connection reuse)
- ✅ Provisioned Concurrency para Lambdas com requisitos de latência baixa
- ✅ Escolha de runtime adequado ao workload (Python para scripts, Node.js para I/O intensivo)
- ✅ Batch processing para operações em lote (SQS batch, DynamoDB BatchWriteItem)
- ✅ Compressão de payloads em APIs com respostas grandes
- ✅ Monitoramento contínuo de latência P50, P90 e P99

## Otimização de Custos

- ✅ Savings Plans e Reserved Instances para workloads previsíveis
- ✅ Monitoramento de custos com AWS Cost Explorer e alertas de budget
- ✅ Tags de custo obrigatórias em todos os recursos (projeto, ambiente, time)
- ✅ Lifecycle policies em S3 para transição automática entre classes de armazenamento
- ✅ TTL habilitado em tabelas DynamoDB para dados temporários
- ✅ Revisão periódica de recursos ociosos ou subutilizados
- ✅ Uso de Spot Instances para workloads tolerantes a interrupção
- ✅ Dimensionamento adequado: evitar over-provisioning de memória e timeout em Lambda

## Sustentabilidade

- ✅ Minimizar recursos ociosos — escalar para zero quando possível (serverless-first)
- ✅ Otimizar utilização de recursos: right-sizing contínuo baseado em métricas reais
- ✅ Escolher regiões AWS com menor pegada de carbono quando viável
- ✅ Reduzir transferência de dados desnecessária entre serviços e regiões
- ✅ Usar formatos de dados eficientes (binário sobre texto quando aplicável)
- ✅ Arquiteturas event-driven para processar apenas quando necessário
- ✅ Cache agressivo para evitar recomputação e chamadas redundantes
- ✅ Monitorar e otimizar duração de execução de funções Lambda
