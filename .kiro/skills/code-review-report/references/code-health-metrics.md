# Code Health Metrics — Referência para Code Review

Este documento define métricas de saúde do código, escalas de severidade e critérios para
classificação de débito técnico. Use como referência ao avaliar qualidade e montar a matriz de achados.

---

## Índice

1. [Débito Técnico — Taxonomia](#1-débito-técnico--taxonomia)
2. [Complexidade Ciclomática](#2-complexidade-ciclomática)
3. [Métricas de Testes](#3-métricas-de-testes)
4. [Gargalos de Performance](#4-gargalos-de-performance)
5. [Error Handling e Resiliência](#5-error-handling-e-resiliência)
6. [Observabilidade](#6-observabilidade)
7. [Acessibilidade (WCAG)](#7-acessibilidade-wcag)
8. [Classificação de Severidade](#8-classificação-de-severidade)
9. [Estimativa de Esforço](#9-estimativa-de-esforço)

---

## 1. Débito Técnico — Taxonomia

### Code Smells por Categoria

#### Bloaters (Código Inchado)
| Smell | Descrição | Severidade Típica |
|-------|-----------|-------------------|
| God Class | Classe com responsabilidades demais (>500 linhas, >10 métodos públicos) | Alto |
| Long Method | Método com linhas demais (>50 linhas) ou complexidade alta | Médio |
| Long Parameter List | Método com parâmetros demais (>4) | Baixo-Médio |
| Data Clumps | Grupos de dados que aparecem juntos repetidamente | Baixo |
| Primitive Obsession | Uso excessivo de primitivos em vez de objetos de domínio | Médio |

#### Object-Orientation Abusers
| Smell | Descrição | Severidade Típica |
|-------|-----------|-------------------|
| Switch Statements | Cadeias de switch/if-else para tipos (deveria ser polimorfismo) | Médio |
| Refused Bequest | Subclasse que não usa métodos herdados | Médio |
| Temporary Field | Campos que só são usados em certas circunstâncias | Baixo |
| Alternative Classes | Classes diferentes que fazem a mesma coisa | Médio |

#### Change Preventers (Impedem Mudança)
| Smell | Descrição | Severidade Típica |
|-------|-----------|-------------------|
| Divergent Change | Uma classe muda por razões diferentes (viola SRP) | Alto |
| Shotgun Surgery | Uma mudança requer alterações em muitas classes | Alto |
| Parallel Inheritance | Criar subclasse em uma hierarquia obriga criar em outra | Médio |

#### Dispensables (Dispensáveis)
| Smell | Descrição | Severidade Típica |
|-------|-----------|-------------------|
| Dead Code | Código que nunca é executado | Baixo-Médio |
| Duplicate Code | Blocos de código idênticos ou muito similares | Médio-Alto |
| Speculative Generality | Abstrações criadas "para o futuro" sem uso atual | Baixo |
| Comments (excessivos) | Comentários que compensam código ruim em vez de melhorar o código | Baixo |
| Lazy Class | Classe que faz muito pouco para justificar sua existência | Baixo |

#### Couplers (Acoplamento Excessivo)
| Smell | Descrição | Severidade Típica |
|-------|-----------|-------------------|
| Feature Envy | Método que usa mais dados de outra classe que da própria | Médio |
| Inappropriate Intimacy | Classes que acessam detalhes internos uma da outra | Alto |
| Message Chains | Cadeias longas de chamadas (a.b().c().d()) | Baixo-Médio |
| Middle Man | Classe que só delega para outra sem agregar valor | Baixo |

---

## 2. Complexidade Ciclomática

### Definição
A complexidade ciclomática mede o número de caminhos linearmente independentes através do código.
Cada ponto de decisão (if, else, switch case, loop, catch, operador ternário, &&, ||) adiciona 1 à complexidade.

### Escala de Referência

| Complexidade | Risco | Ação |
|-------------|-------|------|
| 1-10 | 🟢 Baixo | Código simples, fácil de testar e manter |
| 11-20 | 🟡 Moderado | Complexidade aceitável, mas atenção ao crescimento |
| 21-50 | 🟠 Alto | Difícil de testar, propenso a bugs. Refatorar. |
| 50+ | 🔴 Muito Alto | Praticamente impossível de testar adequadamente. Refatorar urgente. |

### Como Estimar sem Ferramentas
Quando não há ferramentas de análise estática disponíveis, estime a complexidade contando:
- Cada `if`, `else if`, `elif` = +1
- Cada `case` em switch = +1
- Cada `for`, `while`, `do-while`, `foreach` = +1
- Cada `catch` = +1
- Cada `&&`, `||` em condições = +1
- Cada operador ternário `? :` = +1
- Cada `?.` (optional chaining com lógica condicional) = considerar +1 se afeta fluxo

### Foco da Análise
Não é necessário calcular complexidade de todo o codebase. Foque em:
- Controllers e handlers de requisição
- Lógica de negócio principal (Services, Use Cases)
- Funções de validação complexas
- Processamento de dados e transformações
- Qualquer método com mais de 30 linhas

---

## 3. Métricas de Testes

### Tipos de Teste
| Tipo | O que testa | Velocidade | Confiabilidade |
|------|------------|-----------|----------------|
| Unit | Funções/métodos isolados | Rápido | Alta |
| Integration | Interação entre componentes | Médio | Média |
| E2E / Functional | Fluxo completo do usuário | Lento | Variável |
| Contract | Contratos de API entre serviços | Rápido | Alta |
| Snapshot | Regressão visual/estrutural | Rápido | Média |

### Avaliação de Cobertura
| Cobertura | Avaliação |
|-----------|-----------|
| >80% | 🟢 Boa — confiança alta para refatoração |
| 60-80% | 🟡 Razoável — áreas críticas provavelmente cobertas |
| 30-60% | 🟠 Baixa — risco significativo em mudanças |
| <30% | 🔴 Muito baixa — mudanças são arriscadas |
| 0% | ⚫ Inexistente — qualquer mudança é um risco |

### Qualidade dos Testes (além de cobertura)
- Testes testam comportamento ou implementação? (comportamento é melhor)
- Testes são independentes entre si?
- Testes são determinísticos (não flaky)?
- Testes cobrem edge cases e cenários de erro?
- Testes são legíveis e servem como documentação?
- Há testes para os caminhos críticos (auth, pagamentos, dados sensíveis)?

### Frameworks de Teste por Linguagem
| Linguagem | Frameworks Comuns |
|-----------|------------------|
| PHP | PHPUnit, Pest, Codeception |
| JavaScript/TypeScript | Jest, Vitest, Mocha, Cypress, Playwright |
| Python | pytest, unittest, Robot Framework |
| Java | JUnit, TestNG, Mockito |
| Kotlin | JUnit, MockK, Kotest |
| Swift | XCTest, Quick/Nimble |
| Go | testing (stdlib), testify |
| Rust | cargo test (stdlib) |
| C# | xUnit, NUnit, MSTest |
| Ruby | RSpec, Minitest |
| Dart/Flutter | flutter_test, mockito |

---

## 4. Gargalos de Performance

### Padrões Comuns por Categoria

#### Banco de Dados
| Problema | Descrição | Impacto |
|----------|-----------|---------|
| N+1 Queries | Loop que executa uma query por iteração | 🔴 Alto |
| Falta de índices | Queries em colunas sem índice | 🟠 Alto |
| SELECT * | Buscar todas as colunas quando precisa de poucas | 🟡 Médio |
| Queries em loop | Queries dentro de foreach/for/while | 🔴 Alto |
| Falta de paginação | Carregar todos os registros de uma vez | 🟠 Alto |
| Transações longas | Locks mantidos por muito tempo | 🟠 Alto |

#### Memória e CPU
| Problema | Descrição | Impacto |
|----------|-----------|---------|
| Memory leaks | Referências não liberadas (event listeners, closures) | 🔴 Alto |
| Processamento síncrono pesado | Operações CPU-intensive no thread principal | 🟠 Alto |
| Falta de streaming | Carregar arquivos grandes inteiros na memória | 🟡 Médio |
| Serialização ineficiente | JSON.parse/stringify de objetos enormes | 🟡 Médio |

#### Rede e I/O
| Problema | Descrição | Impacto |
|----------|-----------|---------|
| Chamadas HTTP sequenciais | Requisições que poderiam ser paralelas | 🟠 Alto |
| Falta de cache | Dados que não mudam buscados repetidamente | 🟡 Médio |
| Payloads grandes | Respostas de API com dados desnecessários | 🟡 Médio |
| Falta de compressão | Respostas sem gzip/brotli | 🟡 Médio |
| Polling em vez de push | Verificação periódica onde websocket/SSE seria melhor | 🟡 Médio |

#### Frontend Específico
| Problema | Descrição | Impacto |
|----------|-----------|---------|
| Re-renders desnecessários | Componentes que re-renderizam sem mudança de dados | 🟠 Alto |
| Bundle size | Dependências pesadas importadas inteiras | 🟡 Médio |
| Falta de lazy loading | Tudo carregado no bundle inicial | 🟡 Médio |
| Layout thrashing | Leitura e escrita alternada do DOM | 🟠 Alto |
| Imagens não otimizadas | Imagens sem compressão, sem responsive sizes | 🟡 Médio |

#### Mobile Específico
| Problema | Descrição | Impacto |
|----------|-----------|---------|
| Main thread blocking | Operações pesadas na UI thread | 🔴 Alto |
| Falta de cache offline | Sem estratégia de cache para uso offline | 🟡 Médio |
| Battery drain | Polling frequente, GPS contínuo, wake locks | 🟠 Alto |
| Memory pressure | Imagens em alta resolução sem downsampling | 🟠 Alto |

---

## 5. Error Handling e Resiliência

### O que avaliar

#### Tratamento de Erros
| Aspecto | O que procurar | Severidade se ausente |
|---------|---------------|----------------------|
| Catch genérico | `catch (Exception $e)` / `catch (e)` sem tratamento específico | Médio |
| Catch vazio | Blocos catch sem logging nem re-throw — erros silenciados | Alto |
| Logging em catch | Erros capturados mas não logados — invisíveis em produção | Alto |
| Exceções específicas | Uso de exceções de domínio vs. genéricas | Médio |
| Mensagens de erro | Mensagens úteis para debugging vs. genéricas | Baixo |
| Stack traces expostos | Detalhes internos vazando para o usuário final | Alto (segurança) |
| Validação de input | Dados do usuário validados antes de processar | Alto |

#### Resiliência em Integrações Externas
| Aspecto | O que procurar | Severidade se ausente |
|---------|---------------|----------------------|
| Timeout | Chamadas HTTP/SDK sem timeout configurado — podem travar | Alto |
| Retry com backoff | Falhas transientes sem retry automático | Médio |
| Circuit breaker | Serviço externo fora do ar derruba o sistema inteiro | Médio-Alto |
| Fallback/graceful degradation | Sem alternativa quando serviço externo falha | Médio |
| Idempotência | Operações de escrita que podem duplicar em retry | Alto |
| Dead letter queue | Mensagens que falham são perdidas sem DLQ | Médio |

### Padrões por linguagem

**PHP/Laravel:** `try/catch`, `report()`, `abort()`, `retry()`, middleware de exception handling
**Node.js:** `try/catch`, `.catch()`, `process.on('unhandledRejection')`, middleware de erro Express
**Python:** `try/except`, logging module, middleware Django/FastAPI
**Java/Kotlin:** `try/catch`, `@ExceptionHandler`, `@Retryable`, Resilience4j
**Go:** `if err != nil`, error wrapping, middleware
**Swift:** `do/try/catch`, `Result<T, Error>`, Combine error handling
**Dart/Flutter:** `try/catch`, `Future.catchError`, error boundaries

---

## 6. Observabilidade

### O que avaliar

| Aspecto | Bom (🟢) | Parcial (🟡) | Ruim (🔴) |
|---------|----------|-------------|-----------|
| Logging | Estruturado (JSON), com contexto (user, request ID, timestamp) | Existe mas sem estrutura, contexto parcial | Ausente ou apenas print/echo |
| Correlation IDs | Request ID propagado entre serviços | Existe em alguns endpoints | Ausente |
| Health checks | Endpoint dedicado que verifica dependências | Endpoint básico (200 OK) | Ausente |
| Métricas | Métricas de negócio e técnicas exportadas | Apenas métricas de infra | Ausente |
| Tracing | Traces distribuídos entre serviços | Tracing local apenas | Ausente |
| Alertas | Alertas para erros críticos e anomalias | Alertas básicos | Ausente |
| Dados sensíveis | Logs sanitizados, sem PII/secrets | Parcialmente sanitizados | Senhas/tokens em logs |

### Sinais de alerta no código
- `var_dump()`, `dd()`, `console.log()`, `print()` em código de produção
- Logging sem nível (tudo como INFO ou sem nível)
- Dados sensíveis logados (email, CPF, token, senha)
- Ausência de try/catch com logging em chamadas externas
- Sem correlation ID em sistemas com múltiplos serviços

---

## 7. Acessibilidade (WCAG)

Aplicável apenas a projetos com frontend web ou mobile. Referência: WCAG 2.1 nível AA.

### O que procurar no código

| Aspecto | O que verificar | Severidade se ausente |
|---------|----------------|----------------------|
| Alt text | Imagens sem atributo `alt` ou com alt genérico ("image", "foto") | Médio |
| Labels | Inputs de formulário sem `<label>` associado ou `aria-label` | Médio |
| ARIA | Componentes interativos sem roles/states ARIA adequados | Médio |
| Semântica | Uso de `<div>` e `<span>` onde deveria ser `<nav>`, `<main>`, `<article>`, `<button>` | Baixo-Médio |
| Teclado | Elementos interativos não acessíveis via Tab/Enter/Space | Alto |
| Contraste | Cores de texto/fundo com contraste insuficiente (ratio < 4.5:1) | Médio |
| Focus | Falta de indicador visual de foco (`:focus-visible`) | Médio |
| Responsividade | Layout quebrado em telas pequenas, texto não redimensionável | Médio |
| Idioma | Falta de `lang` no `<html>` | Baixo |
| Skip links | Falta de link "pular para conteúdo" em páginas com navegação | Baixo |

### Mobile específico
- **iOS**: VoiceOver labels, Dynamic Type support, sufficient touch targets (44x44pt)
- **Android**: Content descriptions, TalkBack support, minimum touch target (48x48dp)
- **Flutter**: Semantics widgets, `excludeFromSemantics`, `Semantics()` wrapper
- **React Native**: `accessibilityLabel`, `accessibilityRole`, `accessibilityState`

### Nota importante
Avaliação de acessibilidade por inspeção de código é limitada. Problemas como contraste, ordem de leitura e experiência com screen reader requerem testes manuais com tecnologias assistivas. Sinalize esta limitação no relatório.

---

## 8. Classificação de Severidade

### Critérios para Classificação

| Severidade | Símbolo | Critério | Exemplos |
|------------|---------|----------|----------|
| Crítico | 🔴 | Risco imediato de segurança, perda de dados ou indisponibilidade. Requer correção antes de qualquer deploy. | Secret hardcoded, SQL injection, falta de autenticação em endpoint público, dados sensíveis expostos |
| Alto | 🟠 | Problema significativo que afeta segurança, confiabilidade ou manutenibilidade. Corrigir no próximo sprint. | God classes, N+1 queries em endpoints críticos, falta de rate limiting, dependência com CVE alta, catch vazio em fluxo de pagamento |
| Médio | 🟡 | Melhoria importante que reduz risco ou melhora qualidade. Planejar para os próximos 30 dias. | Código duplicado, complexidade ciclomática alta, falta de testes em módulos importantes, logs insuficientes, falta de timeout em chamadas externas |
| Baixo | 🔵 | Melhoria desejável que aumenta qualidade mas não representa risco. Backlog de qualidade. | Nomenclatura inconsistente, comentários desatualizados, dead code, formatação inconsistente, falta de alt text |

### Fatores que Elevam Severidade
- Código em endpoint público (vs. interno)
- Código que lida com dados sensíveis (PII, financeiro, saúde)
- Código em caminho crítico de negócio (pagamentos, autenticação)
- Código sem testes que cubram o cenário
- Código em produção ativa com tráfego real

### Fatores que Reduzem Severidade
- Código em ambiente de desenvolvimento/staging apenas
- Código protegido por outras camadas (WAF, API Gateway, middleware)
- Código com testes que validam o comportamento
- Código em módulo de baixo uso/tráfego
- Código em processo de deprecação

---

## 9. Estimativa de Esforço

### Escala de Esforço para Remediação

| Esforço | Tempo | Descrição |
|---------|-------|-----------|
| Trivial | <1h | Renomear variável, remover dead code, corrigir typo, adicionar alt text |
| Pequeno | 1-4h | Extrair método, adicionar validação, corrigir query, adicionar timeout |
| Médio | 4h-2d | Refatorar classe, adicionar testes, implementar cache, adicionar logging estruturado |
| Grande | 2-5d | Reestruturar módulo, implementar padrão de design, migrar dependência, implementar circuit breaker |
| Muito Grande | 1-3 semanas | Reescrever subsistema, migrar arquitetura, implementar observabilidade completa |

### Priorização no Roadmap

A priorização combina severidade com esforço:

| | Esforço Baixo | Esforço Médio | Esforço Alto |
|---|---|---|---|
| **Severidade Crítica** | Fase 1 (imediato) | Fase 1 (imediato) | Fase 1 (imediato) |
| **Severidade Alta** | Fase 1 (imediato) | Fase 2 (curto prazo) | Fase 2 (curto prazo) |
| **Severidade Média** | Fase 2 (curto prazo) | Fase 3 (médio prazo) | Fase 3 (médio prazo) |
| **Severidade Baixa** | Fase 2 (curto prazo) | Fase 3 (médio prazo) | Fase 4 (longo prazo) |

Quick wins (severidade alta + esforço baixo) devem ser priorizados pois entregam valor rápido.

---

## Notas para o Revisor

1. **Use ferramentas quando disponíveis**: Se o projeto tem linters, formatters ou ferramentas de análise estática configuradas, execute-as e incorpore os resultados. Dados objetivos de ferramentas são mais confiáveis que estimativas manuais.
2. **Pesquise online**: Para CVEs, versões atuais de dependências e best practices específicas do framework, use pesquisa web para dados atualizados.
3. **Seja pragmático**: Um projeto com 3 meses de vida tem expectativas diferentes de um com 5 anos. Considere o contexto.
4. **Foque no que importa**: Em um projeto com SQL injection, não gaste tempo catalogando variáveis mal nomeadas. Priorize.
5. **Documente o que não foi analisado**: Se o projeto é muito grande e você focou em módulos específicos, diga quais módulos foram analisados e quais ficaram de fora.
6. **Adapte ao tipo de projeto**: Backend, frontend e mobile têm prioridades diferentes. Não force seções irrelevantes.
