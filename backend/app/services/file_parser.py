"""文件解析器：把各种格式的文件统一转成纯文本。"""
from pathlib import Path
from pypdf import PdfReader
from docx import Document


# 支持的文件类型
SUPPORTED_TYPES = {"pdf", "docx", "txt", "md"}

# 文件大小上限：10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024


def get_extension(filename: str) -> str:
    """从文件名里取扩展名，比如 'x.PDF' → 'pdf'"""
    return Path(filename).suffix.lstrip(".").lower()


def is_supported(filename: str) -> bool:
    """检查文件类型是否支持"""
    return get_extension(filename) in SUPPORTED_TYPES


def parse_file(file_path: str, file_type: str) -> str:
    """
    核心方法：根据文件类型，调用对应的解析器，返回纯文本。
    出现任何异常都抛出，让上层业务处理。
    """
    file_type = file_type.lower()

    if file_type == "pdf":
        return _parse_pdf(file_path)
    elif file_type == "docx":
        return _parse_docx(file_path)
    elif file_type in ("txt", "md"):
        return _parse_text(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


def _parse_pdf(file_path: str) -> str:
    """解析 PDF：逐页提取文字，拼成一个字符串。"""
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"--- 第 {i + 1} 页 ---\n{text}")
    if not pages:
        raise ValueError("PDF 中没有可提取的文本（可能是扫描件/图片 PDF）")
    return "\n\n".join(pages)


def _parse_docx(file_path: str) -> str:
    """解析 Word：把每个段落的文字提取出来。"""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        raise ValueError("Word 文档中没有可提取的文本")
    return "\n".join(paragraphs)


def _parse_text(file_path: str) -> str:
    """解析 TXT / Markdown：直接读文件，自动尝试多种编码。"""
    # 常见编码依次尝试，防止中文乱码
    for encoding in ("utf-8", "gbk", "utf-16"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            if not content.strip():
                raise ValueError("文件内容为空")
            return content
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别文件编码（尝试过 utf-8/gbk/utf-16）")