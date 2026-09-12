---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# Organização de Dataclasses por Papel Arquitetural

Onde colocar `@dataclass` (e afins como `TypedDict`, `NamedTuple`, Pydantic `BaseModel`) em projetos Python. Para convenções gerais de código, consulte #[[file:.kiro/steering/01-padroes-gerais.md]]. Para padrões de handler e camadas em Python, consulte #[[file:.kiro/steering/03-sam-python.md]].

## Princípio Central

- Organize pelo **papel arquitetural** da classe, nunca pela tecnologia usada para declará-la.
- `@dataclass` é **detalhe de implementação** — não é critério de organização de pastas.
- **Nunca** crie uma pasta genérica `dataclasses/`. Ela agrupa por tecnologia, não por responsabilidade, e vira depósito sem coesão.
- Antes de posicionar a classe, pergunte: **"Por que essa classe existe?"** — a resposta determina a pasta.

## Regra de Decisão (Finalidade → Pasta)

| Finalidade                     | Pasta                         |
| ------------------------------ | ----------------------------- |
| Dados de entrada/saída (DTO)   | `application/dto/`            |
| Entidade de negócio            | `domain/entities/`           |
| Objeto-valor                   | `domain/value_objects/`      |
| Schema de API (request/resp.)  | `interface/api/schemas/`     |
| Modelo ORM                     | `infrastructure/persistence/`|
| Configuração                   | `config/` ou junto do módulo |
| Resultado de uma operação      | `results/` ou junto do caso de uso |
| Estado interno de um módulo    | junto do próprio módulo       |

## Alinhamento com a Arquitetura do Repo

Este projeto usa camadas em `code/src/qa_platform/`: `domain/`, `application/`, `infrastructure/`, `interface/`. Posicione dataclasses respeitando essas fronteiras e a direção de dependência (domínio não depende de infra/interface).

- **Domínio** — entidades e objetos-valor que expressam conceitos de negócio:

```python
# domain/entities/agent.py
from dataclasses import dataclass


@dataclass
class Agent:
    id: str
    name: str
    model: str
```

```python
# domain/value_objects/email.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    value: str
```

- **Aplicação** — DTOs de entrada/saída dos casos de uso:

```python
# application/dto/create_user_input.py
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateUserInput:
    name: str
    email: str
```

- **Interface** — schemas de API (o formato do contrato HTTP), separados dos DTOs internos:

```python
# interface/api/schemas/user.py
```

- **Infraestrutura** — modelos de persistência/ORM, isolados do domínio.

## Estado Interno de um Módulo

- Se a dataclass é usada **somente** dentro de um módulo, mantenha-a junto dele (ex.: `models.py` no próprio pacote). Não promova a uma pasta compartilhada.

```python
# infrastructure/orchestration/models.py
from dataclasses import dataclass


@dataclass
class AgentExecution:
    agent_id: str
    input: str
    output: str
```

## `@dataclass` vs Pydantic `BaseModel`

- **`@dataclass`** — estruturas internas do domínio/aplicação, sem necessidade de validação/coerção em runtime. Prefira `frozen=True` para objetos-valor e DTOs imutáveis.
- **Pydantic `BaseModel`** — fronteiras externas (schemas de API, parsing de payloads/manifests, config vinda de env). Onde há validação e (de)serialização, use Pydantic e mantenha na camada de borda (`interface/`), não no domínio.
- Não misture: evite Pydantic no núcleo do domínio só por conveniência de validação — converta na fronteira e passe tipos de domínio para dentro.

## Anti-padrões

- ❌ Pasta `dataclasses/` (organização por tecnologia).
- ❌ Pasta `models/` genérica em projetos grandes — ambígua (ORM? Pydantic? domínio? schema?). Prefira nomes específicos: `entities/`, `value_objects/`, `dto/`, `schemas/`.
- ❌ Dataclass de domínio importando de `infrastructure/` ou `interface/` (viola a direção de dependência).
