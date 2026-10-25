---
name: drawio-diagram
description: Generate draw.io XML from explicit project context and authorized output paths.
---
# Portable diagram contract
Principal delegates diagram implementation to a qualified specialist. Read brief,
allowed paths and policies. Select output directory explicitly (docs/diagrams is
only a suggestion if authorized). Do not install extensions. Escape XML attributes,
use unique IDs and valid parent/source/target references. Parse XML and check graph
references; separately record actual draw.io opening/rendering verification.


Generate a draw.io diagram for the explicitly selected project.

## Inputs

Read the brief or explicit action input for what to diagram. If empty, ask: "O que quer diagramar? (ex: fluxo de auth, infra AWS, rede Docker, stack de serviços)"

## Process

1. **Gather context** — read the relevant files for the area requested:
   - Auth flow → project-supplied authentication and identity paths
   - AWS infra, if selected → `infra/`, `template.yaml`, any SAM/Terraform files
   - Docker network, if selected → `docker-compose*.yml`, Traefik config
   - Services overview → configured service roots and workspace manifests

2. **Identify components and connections** — list:
   - Nodes (services, lambdas, databases, queues, users, CDN, etc.)
   - Edges (HTTP, events, SQL, token exchange, etc.)
   - Groups (VPC, Docker network, AWS region, etc.)

3. **Generate the `.drawio` file** — write valid draw.io XML to a file at:
   `<configured-diagram-directory>/<slug>.drawio`
   where `<slug>` is derived from the subject (e.g. `auth-flow`, `aws-infra`, `docker-network`).

## draw.io XML skeleton

Use mxGraph XML format. Minimal working example:

```xml
<mxfile>
  <diagram name="Page-1">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- nodes and edges here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

Node cell pattern:
```xml
<mxCell id="n1" value="Service Name" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
  <mxGeometry x="80" y="80" width="120" height="40" as="geometry"/>
</mxCell>
```

Edge cell pattern:
```xml
<mxCell id="e1" value="label" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="n1" target="n2" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

Group/swimlane pattern:
```xml
<mxCell id="g1" value="AWS Region" style="swimlane;" vertex="1" parent="1">
  <mxGeometry x="40" y="40" width="400" height="300" as="geometry"/>
</mxCell>
```

## Styles to use per node type

| Type | Style snippet |
|---|---|
| User/Client | `shape=mxgraph.aws4.user;` |
| Lambda | `shape=mxgraph.aws4.lambda_function;` |
| API Gateway | `shape=mxgraph.aws4.api_gateway;` |
| RDS/Postgres | `shape=mxgraph.aws4.rds;` |
| S3 | `shape=mxgraph.aws4.s3;` |
| Cognito | `shape=mxgraph.aws4.cognito;` |
| Docker container | `rounded=1;whiteSpace=wrap;html=1;` |
| Generic service | `rounded=1;whiteSpace=wrap;html=1;` |

If AWS shapes are not available, fall back to `rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;`.

## Output

- Write the file to `<configured-diagram-directory>/<slug>.drawio`
- Print a one-line confirmation: `Diagrama gerado: <configured-diagram-directory>/<slug>.drawio`
- If VS Code draw.io extension is installed (hediet.vscode-drawio), the file opens directly in the IDE.
