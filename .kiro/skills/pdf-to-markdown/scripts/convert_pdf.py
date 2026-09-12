#!/usr/bin/env python3
"""
PDF to Markdown Converter
Converte arquivos PDF para Markdown com extração de imagens.

Estratégia: Renderiza cada página como imagem de alta qualidade (preservando
o layout visual exato do PDF) e extrai o texto para o markdown.
"""

import sys
import os
import argparse
from pathlib import Path


def setup_environment():
    """Configura o ambiente virtual com uv e instala dependências."""
    import subprocess

    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Erro: 'uv' não está instalado. Instale com: pip install uv")
        sys.exit(1)

    venv_path = Path(__file__).parent / ".venv"
    if not venv_path.exists():
        print("Criando ambiente virtual...")
        subprocess.run(["uv", "venv", str(venv_path)], check=True)

    print("Instalando dependências...")
    deps = ["pymupdf", "pytesseract", "Pillow"]
    for dep in deps:
        subprocess.run(
            ["uv", "pip", "install", dep],
            env={**os.environ, "VIRTUAL_ENV": str(venv_path)},
            check=True,
        )

    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"

    return python_path


def convert_pdf_to_markdown(pdf_path, output_dir=None, dpi=200):
    """
    Converte PDF para Markdown renderizando cada página como imagem.

    Cada página do PDF é renderizada como uma imagem PNG de alta qualidade,
    preservando o layout visual exato. O texto é extraído separadamente
    e colocado no markdown junto com a referência à imagem da página.
    """
    import fitz  # PyMuPDF

    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        print(f"Erro: Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    if output_dir:
        output_dir = Path(output_dir).resolve()
    else:
        output_dir = pdf_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem
    md_path = output_dir / f"{stem}.md"
    images_dir = output_dir / f"{stem}_images"
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"Convertendo: {pdf_path}")
    print(f"Saída: {md_path}")
    print(f"Imagens: {images_dir}")
    print(f"DPI: {dpi}")

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    markdown_parts = []

    markdown_parts.append(f"# {stem}\n")

    for page_num in range(total_pages):
        page = doc[page_num]
        print(f"  Processando página {page_num + 1}/{total_pages}...")

        # 1) Renderiza a página inteira como imagem de alta qualidade
        image_filename = f"page_{page_num + 1:03d}.png"
        image_path = images_dir / image_filename

        pix = page.get_pixmap(dpi=dpi)
        pix.save(str(image_path))

        relative_image = f"{images_dir.name}/{image_filename}"

        # 2) Extrai texto da página
        text = page.get_text().strip()

        # Se não há texto, tenta OCR
        if not text:
            text = _try_ocr(page)

        # 3) Monta o markdown da página
        markdown_parts.append(f"## Página {page_num + 1}\n")
        markdown_parts.append(f"![Página {page_num + 1}]({relative_image})\n")

        if text:
            # Formata o texto extraído
            formatted = _format_text(text)
            markdown_parts.append("<details>\n<summary>Texto extraído</summary>\n")
            markdown_parts.append(formatted)
            markdown_parts.append("\n</details>\n")

        markdown_parts.append("---\n")

    doc.close()

    final_md = "\n".join(markdown_parts)
    md_path.write_text(final_md, encoding="utf-8")

    print("\n✓ Conversão concluída!")
    print(f"  Markdown: {md_path}")
    print(f"  Imagens: {total_pages} páginas renderizadas em {images_dir}")

    return md_path, total_pages


def _format_text(text):
    """Formata o texto extraído para markdown."""
    lines = text.split("\n")
    formatted = []
    for line in lines:
        line = line.strip()
        if not line:
            formatted.append("")
            continue
        # Heurística para títulos
        if len(line) < 60 and line.isupper() and len(line) > 3:
            formatted.append(f"### {line.title()}")
        else:
            formatted.append(line)
    return "\n".join(formatted)


def _try_ocr(page):
    """Tenta extrair texto via OCR para páginas escaneadas."""
    try:
        import pytesseract
        from PIL import Image
        import io

        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        text = pytesseract.image_to_string(img, lang="por+eng")
        return text.strip()
    except Exception as e:
        print(f"    Aviso: OCR falhou: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(
        description="Converte PDF para Markdown com renderização de páginas"
    )
    parser.add_argument("pdf_path", help="Caminho para o arquivo PDF")
    parser.add_argument("--output-dir", "-o", help="Diretório de saída")
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Resolução das imagens em DPI (padrão: 200)",
    )
    parser.add_argument(
        "--no-setup", action="store_true", help="Pula configuração do ambiente"
    )

    args = parser.parse_args()

    if not args.no_setup:
        in_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )
        if not in_venv:
            print("Configurando ambiente virtual...")
            python_path = setup_environment()

            import subprocess

            cmd = [
                str(python_path),
                __file__,
                args.pdf_path,
                "--no-setup",
                "--dpi",
                str(args.dpi),
            ]
            if args.output_dir:
                cmd.extend(["--output-dir", args.output_dir])

            result = subprocess.run(cmd)
            sys.exit(result.returncode)

    convert_pdf_to_markdown(args.pdf_path, args.output_dir, args.dpi)


if __name__ == "__main__":
    main()
