# PDF to Markdown Converter Skill

Skill para converter arquivos PDF para formato Markdown com extração automática de imagens.

## Funcionalidades

- ✅ Extração de texto de PDFs nativos
- ✅ OCR para PDFs escaneados (requer Tesseract)
- ✅ Extração de imagens como arquivos separados
- ✅ Referências automáticas às imagens no markdown
- ✅ Preservação da estrutura do documento
- ✅ Suporte a múltiplas páginas
- ✅ Uso de `uv + venv` para gerenciamento de dependências

## Instalação

A skill gerencia automaticamente suas dependências usando `uv`. Certifique-se de ter o `uv` instalado:

```bash
pip install uv
```

Para PDFs escaneados (OCR), instale o Tesseract:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-por

# macOS
brew install tesseract tesseract-lang

# Fedora
sudo dnf install tesseract tesseract-langpack-por
```

## Uso

A skill é acionada automaticamente quando você menciona:
- "converter PDF"
- "exportar PDF para markdown"
- "extrair texto de PDF"
- "transformar PDF em MD"
- Ou quando fornece um arquivo .pdf

### Exemplo

```
Usuário: "Converte o brandbook.pdf para markdown"

Kiro: [executa a conversão e informa os resultados]
```

## Estrutura

```
pdf-to-markdown/
├── SKILL.md              # Instruções da skill
├── README.md             # Este arquivo
├── scripts/
│   ├── convert_pdf.py    # Script principal de conversão
│   └── .venv/            # Ambiente virtual (criado automaticamente)
└── evals/
    └── evals.json        # Casos de teste
```

## Saída

Para um arquivo `documento.pdf`, a skill cria:

```
documento.md              # Markdown com o conteúdo
documento_images/         # Pasta com imagens extraídas
  ├── image_001.png
  ├── image_002.png
  └── ...
```

## Dependências Python

Gerenciadas automaticamente via `uv`:
- `pymupdf` (fitz) - Extração de PDF
- `pytesseract` - OCR
- `Pillow` - Processamento de imagens

## Limitações

- Tabelas complexas podem precisar de ajustes manuais
- PDFs com layouts muito complexos podem perder formatação
- OCR requer Tesseract instalado no sistema
- Imagens vetoriais podem não ser extraídas corretamente
