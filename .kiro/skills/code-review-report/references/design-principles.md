# Princípios e Padrões de Design — Referência para Code Review

Este documento define os critérios de avaliação para princípios e padrões de design de software.
Use como referência ao analisar aderência do código a boas práticas.

---

## Índice

1. [Princípios SOLID](#1-princípios-solid)
2. [Clean Code](#2-clean-code)
3. [DRY, KISS, YAGNI](#3-dry-kiss-yagni)
4. [Padrões de Design Comuns](#4-padrões-de-design-comuns)
5. [Padrões Arquiteturais](#5-padrões-arquiteturais)
6. [API Design e Contracts](#6-api-design-e-contracts)
7. [Gestão de Configuração e Ambientes](#7-gestão-de-configuração-e-ambientes)
8. [Critérios de Avaliação](#8-critérios-de-avaliação)

---

## 1. Princípios SOLID

### SRP — Single Responsibility Principle
**Definição:** Uma classe deve ter apenas um motivo para mudar.

**Sinais de violação:**
- Classes com mais de 300-500 linhas (varia por linguagem)
- Classes que fazem validação, persistência e notificação ao mesmo tempo
- Métodos que fazem coisas não relacionadas ao nome da classe
- Muitas dependências injetadas (>5-7 sugere responsabilidades demais)

**Como avaliar:**
- 🟢 Classes focadas, com nome que descreve bem sua única responsabilidade
- 🟡 Algumas classes acumulam 2-3 responsabilidades, mas a maioria está ok
- 🔴 God classes frequentes, controllers com lógica de negócio, models com tudo

### OCP — Open/Closed Principle
**Definição:** Entidades devem ser abertas para extensão, fechadas para modificação.

**Sinais de violação:**
- Cadeias de if/else ou switch para tipos/categorias que crescem com o tempo
- Modificação frequente de classes existentes para adicionar novos comportamentos
- Falta de interfaces/abstrações para pontos de extensão

**Como avaliar:**
- 🟢 Uso de Strategy, Factory, ou polimorfismo para variações de comportamento
- 🟡 Alguns pontos de extensão, mas com if/else em áreas que mudam frequentemente
- 🔴 Código rígido que requer modificação direta para qualquer novo requisito

### LSP — Liskov Substitution Principle
**Definição:** Subtipos devem ser substituíveis por seus tipos base sem alterar o comportamento.

**Sinais de violação:**
- Subclasses que lançam exceções não esperadas pelo tipo base
- Métodos override que não respeitam o contrato do pai
- Verificações de tipo (instanceof, typeof) para tratar subclasses diferentemente

**Como avaliar:**
- 🟢 Hierarquias de herança coerentes, contratos respeitados
- 🟡 Algumas violações pontuais, mas sem impacto grave
- 🔴 Herança usada para reuso de código sem relação semântica "é um"

### ISP — Interface Segregation Principle
**Definição:** Clientes não devem depender de interfaces que não usam.

**Sinais de violação:**
- Interfaces com muitos métodos (>5-7)
- Classes que implementam interfaces mas deixam métodos vazios ou com throw
- Uma interface "faz tudo" usada por classes com necessidades diferentes

**Como avaliar:**
- 🟢 Interfaces pequenas e focadas, composição de interfaces quando necessário
- 🟡 Algumas interfaces grandes, mas sem implementações vazias
- 🔴 Interfaces monolíticas com implementações parciais frequentes

### DIP — Dependency Inversion Principle
**Definição:** Módulos de alto nível não devem depender de módulos de baixo nível. Ambos devem depender de abstrações.

**Sinais de violação:**
- Instanciação direta de dependências (new ConcreteClass()) em lógica de negócio
- Imports diretos de implementações concretas em módulos de alto nível
- Falta de injeção de dependência
- Acoplamento direto a frameworks, bancos de dados ou serviços externos

**Como avaliar:**
- 🟢 Injeção de dependência consistente, interfaces para serviços externos
- 🟡 DI usado parcialmente, alguns acoplamentos diretos
- 🔴 Instanciação direta generalizada, sem abstrações entre camadas

---

## 2. Clean Code

### Nomenclatura
- Nomes revelam intenção? (`$d` vs `$elapsedDays`)
- Nomes são pronunciáveis e buscáveis?
- Classes são substantivos, métodos são verbos?
- Convenções de nomenclatura da linguagem são seguidas? (camelCase, snake_case, PascalCase)

### Funções/Métodos
- São pequenos? (ideal: 5-20 linhas, aceitável: até 30-40)
- Fazem uma coisa só?
- Poucos parâmetros? (ideal: 0-2, aceitável: 3, flag arguments são code smell)
- Sem efeitos colaterais ocultos?
- Nível de abstração consistente dentro do método?

### Comentários
- O código é autoexplicativo sem comentários?
- Comentários explicam "por quê", não "o quê"?
- Há comentários desatualizados ou enganosos?
- TODO/FIXME/HACK são rastreados?

### Formatação
- Indentação consistente?
- Linhas com tamanho razoável? (<120 caracteres)
- Agrupamento lógico de código?
- Imports organizados?

### Tratamento de Erros
- Exceções são usadas em vez de códigos de retorno?
- Exceções são específicas (não catch genérico)?
- Erros são logados adequadamente?
- Mensagens de erro são úteis?
- Happy path é claro e separado do error handling?

---

## 3. DRY, KISS, YAGNI

### DRY — Don't Repeat Yourself
**Definição:** Cada pedaço de conhecimento deve ter uma representação única e não ambígua no sistema.

**Sinais de violação:**
- Blocos de código copiados e colados (>5 linhas idênticas em 2+ lugares)
- Lógica de validação duplicada (frontend e backend sem compartilhamento)
- Queries SQL repetidas em múltiplos lugares
- Constantes/configurações definidas em múltiplos arquivos

**Nota:** DRY não é sobre eliminar toda duplicação textual. Duas funções com código similar mas razões de mudança diferentes não violam DRY. A regra é sobre duplicação de conhecimento, não de texto.

### KISS — Keep It Simple, Stupid
**Definição:** A solução mais simples que resolve o problema é a melhor.

**Sinais de violação:**
- Abstrações prematuras (interfaces com uma única implementação sem razão clara)
- Padrões de design aplicados onde uma função simples bastaria
- Metaprogramação/reflection onde código direto funcionaria
- Arquitetura de microsserviços para um CRUD simples
- Generics/templates complexos sem necessidade real

### YAGNI — You Ain't Gonna Need It
**Definição:** Não implemente funcionalidade até que seja necessária.

**Sinais de violação:**
- Código comentado "para uso futuro"
- Features parcialmente implementadas e abandonadas
- Abstrações para extensibilidade que nunca foi usada
- Configurações para cenários que não existem
- Classes/métodos sem uso (dead code)

---

## 4. Padrões de Design Comuns

### Padrões Criacionais
| Padrão | Quando procurar | Sinais no código |
|--------|----------------|-----------------|
| Factory | Criação de objetos com lógica | Classes `*Factory`, métodos `create*`, `make*` |
| Builder | Objetos complexos com muitos parâmetros | Métodos encadeados, classes `*Builder` |
| Singleton | Instância única global | `getInstance()`, variável estática de instância |

### Padrões Estruturais
| Padrão | Quando procurar | Sinais no código |
|--------|----------------|-----------------|
| Adapter | Integração com APIs externas | Classes `*Adapter`, wrapping de interfaces |
| Decorator | Extensão de comportamento | Classes que wrappam outras da mesma interface |
| Facade | Simplificação de subsistemas | Classes que agrupam chamadas a múltiplos serviços |

### Padrões Comportamentais
| Padrão | Quando procurar | Sinais no código |
|--------|----------------|-----------------|
| Strategy | Algoritmos intercambiáveis | Interfaces com múltiplas implementações selecionadas em runtime |
| Observer | Eventos e notificações | Event listeners, subscribers, hooks |
| Repository | Acesso a dados | Classes `*Repository` que abstraem persistência |
| Service Layer | Lógica de negócio | Classes `*Service` entre controllers e models |
| Middleware | Pipeline de processamento | Cadeia de handlers (HTTP middleware, message handlers) |

---

## 5. Padrões Arquiteturais

### MVC / MVP / MVVM
- **MVC**: Model-View-Controller — padrão em Laravel, Rails, Django, Spring MVC
- **MVP**: Model-View-Presenter — comum em Android legado
- **MVVM**: Model-View-ViewModel — comum em SwiftUI, Jetpack Compose, Angular, Vue

### Clean Architecture / Hexagonal / Onion
- Camadas com dependência apontando para dentro (domínio no centro)
- Ports & Adapters para serviços externos
- Use cases/interactors como orquestradores de lógica

### Monolito vs. Microsserviços
- Monolito modular: módulos bem separados dentro de um deploy
- Microsserviços: serviços independentes com comunicação via API/mensageria

---

## 6. API Design e Contracts

### O que avaliar em APIs (REST, GraphQL, gRPC)

| Aspecto | Bom (🟢) | Parcial (🟡) | Ruim (🔴) |
|---------|----------|-------------|-----------|
| Validação de input | Todos os endpoints validam request body com schema (Form Request, Joi, Pydantic, Zod) | Validação em endpoints críticos, ausente em outros | Sem validação — dados do usuário usados diretamente |
| Formato de resposta | Envelope consistente em todas as respostas (data, error, meta) | Maioria consistente, alguns endpoints fora do padrão | Cada endpoint retorna formato diferente |
| Códigos HTTP | Uso correto e consistente (200, 201, 400, 401, 403, 404, 422, 500) | Maioria correto, alguns endpoints retornam 200 para erros | Tudo retorna 200 ou códigos inconsistentes |
| Versionamento | API versionada (URL, header ou media type) | Versão existe mas não é usada consistentemente | Sem versionamento |
| Documentação | OpenAPI/Swagger atualizado e completo | Documentação existe mas desatualizada | Sem documentação de API |
| Rate limiting | Rate limiting configurado em endpoints públicos | Rate limiting parcial | Sem rate limiting |
| Paginação | Paginação consistente em listagens (cursor ou offset) | Paginação em algumas listagens | Listagens retornam todos os registros |

### Validação de Input por Framework

| Framework | Mecanismo de Validação |
|-----------|----------------------|
| Laravel | Form Requests, `$request->validate()` |
| Express/Fastify | Joi, Zod, express-validator, AJV |
| Django/DRF | Serializers, Forms |
| FastAPI | Pydantic models (automático) |
| Spring | `@Valid`, `@Validated`, Bean Validation |
| NestJS | class-validator + class-transformer, Pipes |
| Rails | Strong Parameters, ActiveModel Validations |
| Go (Gin/Echo) | binding tags, validator package |

---

## 7. Gestão de Configuração e Ambientes

### O que avaliar

| Aspecto | Bom (🟢) | Parcial (🟡) | Ruim (🔴) |
|---------|----------|-------------|-----------|
| .env.example | Atualizado com todas as variáveis, sem valores sensíveis reais | Existe mas incompleto ou desatualizado | Ausente |
| Validação de env vars | Aplicação valida variáveis obrigatórias no boot e falha rápido | Validação parcial | Sem validação — falha em runtime |
| Defaults perigosos | Nenhum default perigoso (debug=false, sem secrets default) | Alguns defaults questionáveis | APP_DEBUG=true, SECRET_KEY=secret como default |
| Separação de ambientes | Configs claramente separadas por ambiente | Separação parcial | Configs de produção misturadas com dev |
| Configs hardcoded | Todas as configs variáveis vêm de env/config files | Maioria em env, algumas hardcoded | URLs, credenciais e configs hardcoded no código |

### Sinais de alerta
- `APP_DEBUG=true` ou `DEBUG=True` como default no `.env.example`
- `SECRET_KEY=secret` ou `APP_KEY=base64:...` com valor real no `.env.example`
- URLs de API hardcoded no código (ex: `https://api.production.com/v1/`)
- Credenciais de banco de dados com valores default que funcionam (ex: `DB_PASSWORD=root`)
- Falta de `.env.example` quando o projeto usa variáveis de ambiente

---

## 8. Critérios de Avaliação

### Escala de Aderência
| Nível | Símbolo | Significado |
|-------|---------|-------------|
| Bom | 🟢 | Princípio aplicado consistentemente. Violações são exceção rara e justificável. |
| Parcial | 🟡 | Princípio aplicado em partes do código, mas com violações frequentes em outras. |
| Ruim | 🔴 | Princípio não é seguido ou é violado sistematicamente. |
| N/A | ⚪ | Princípio não se aplica ao contexto do projeto. |

### Contexto importa
- Um script de migração não precisa de Clean Architecture
- Uma PoC não precisa de cobertura de testes de 80%
- Um projeto legado em manutenção tem expectativas diferentes de um greenfield
- Mobile e frontend têm padrões diferentes de backend

Sempre considere o contexto do projeto ao avaliar. O objetivo é ser útil, não dogmático.
