---
name: pdf-to-markdown
description: Converte arquivos PDF para formato Markdown com extração de texto, tabelas e imagens. Use esta skill sempre que o usuário mencionar "converter PDF", "exportar PDF para markdown", "extrair texto de PDF", "transformar PDF em MD", "PDF para texto", ou quando fornecer um arquivo .pdf e pedir para trabalhar com ele em formato editável. Também use quando o usuário precisar processar PDFs escaneados (com OCR), extrair conteúdo estruturado de documentos PDF, ou criar versões markdown de manuais, relatórios, brandbooks, ou qualquer documento PDF.
---

# PDF to Markdown Converter

Esta skill converte arquivos PDF para formato Markdown, preservando a estrutura do documento e extraindo imagens separadamente.

## Capacidades

- Extração de texto de PDFs nativos e escaneados (OCR)
- Preservação da estrutura (títulos, parágrafos, listas)
- Extração de tabelas em formato Markdown
- Extração de imagens como arquivos separados
- Referências automáticas às imagens no markdown
- Suporte a PDFs com múltiplas páginas

## Quando Usar

Use esta skill quando o usuário:
- Fornecer um arquivo PDF e pedir para convertê-lo
- Mencionar "extrair", "converter", "exportar" em relação a PDFs
- Precisar trabalhar com o conteúdo de um PDF em formato editável
- Quiser documentação ou relatórios em markdown a partir de PDFs

## Fluxo de Trabalho

### 1. Identificar o Arquivo PDF

Primeiro, confirme o caminho do arquivo PDF. Se o usuário não especificou claramente, pergunte ou procure por arquivos .pdf no contexto.

### 2. Preparar o Ambiente

Use o script `scripts/convert_pdf.py` que já está configurado com todas as dependências necessárias. O script usa `uv` para gerenciar o ambiente virtual Python automaticamente.

### 3. Executar a Conversão

Execute o script de conversão:

```bash
python ~/.kiro/skills/pdf-to-markdown/scripts/convert_pdf.py <caminho-do-pdf> [--output-dir <diretório-saída>] [--dpi 200]
```

Parâmetros:
- `<caminho-do-pdf>`: Caminho para o arquivo PDF (obrigatório)
- `--output-dir`: Diretório onde salvar os arquivos (opcional, padrão: mesmo diretório do PDF)
- `--dpi`: Resolução das imagens em DPI (opcional, padrão: 200). Use 300 para alta qualidade.

### 4. Verificar os Resultados

O script cria:
- `<nome-do-arquivo>.md`: Arquivo markdown com o conteúdo extraído
- `<nome-do-arquivo>_images/`: Pasta com uma imagem PNG por página do PDF
- Cada página é renderizada como imagem completa preservando o layout visual exato
- O texto extraído fica em blocos `<details>` colapsáveis abaixo de cada imagem

### 5. Revisar e Ajustar

Após a conversão:
- Leia o arquivo markdown gerado
- Verifique se a estrutura foi preservada corretamente
- Confirme que as imagens foram extraídas e referenciadas
- Se necessário, faça ajustes manuais na formatação

## Tratamento de Casos Especiais

### PDFs Escaneados (OCR)

O script detecta automaticamente se o PDF contém texto extraível. Se não contiver (PDF escaneado), ele usa OCR (Tesseract) para extrair o texto. Certifique-se de que o Tesseract está instalado no sistema.

### Tabelas Complexas

Tabelas são convertidas para formato Markdown table. Tabelas muito complexas podem precisar de ajustes manuais após a conversão.

### Imagens

- Cada página do PDF é renderizada como uma imagem PNG completa
- A renderização preserva o layout visual exato do PDF (textos, imagens, gráficos, backgrounds)
- Resolução padrão de 200 DPI (use --dpi 300 para maior qualidade)
- Nomeadas sequencialmente: `page_001.png`, `page_002.png`, etc.

### PDFs Grandes

Para PDFs com muitas páginas (>50), o script pode demorar alguns minutos. Informe o usuário sobre o progresso.

## Dependências

O script gerencia automaticamente as seguintes dependências via `uv`:
- `pymupdf` (fitz): Extração de texto e imagens
- `pytesseract`: OCR para PDFs escaneados
- `Pillow`: Processamento de imagens

## Solução de Problemas

### Erro: "Tesseract not found"

Se o usuário encontrar este erro ao processar PDFs escaneados, instrua-o a instalar o Tesseract:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-por

# macOS
brew install tesseract tesseract-lang

# Fedora
sudo dnf install tesseract tesseract-langpack-por
```

### Texto Mal Formatado

Se o texto extraído estiver mal formatado:
- Verifique se o PDF original tem boa qualidade
- Para PDFs escaneados, uma resolução maior ajuda no OCR
- Considere ajustes manuais no markdown gerado

### Imagens Não Extraídas

Se imagens não forem extraídas:
- Verifique se o PDF contém imagens reais (não apenas backgrounds)
- Algumas imagens vetoriais podem não ser extraídas corretamente
- Considere usar ferramentas especializadas para casos complexos

## Exemplo de Uso

```
Usuário: "Converte o brandbook.pdf para markdown"

Você:
1. Localiza o arquivo brandbook.pdf
2. Executa: python ~/.kiro/skills/pdf-to-markdown/scripts/convert_pdf.py brandbook.pdf
3. Informa: "Conversão concluída! Criei brandbook.md com o conteúdo e extraí X imagens para a pasta brandbook_images/"
4. Oferece: "Quer que eu revise o markdown gerado?"
```

## Notas Importantes

- Sempre use caminhos absolutos ou relativos corretos ao executar o script
- Informe o usuário sobre o tempo estimado para PDFs grandes
- Ofereça-se para revisar e ajustar o markdown após a conversão
- Se o usuário quiser modificações no formato, edite o markdown diretamente
