"""实用工具服务：图片压缩、二维码、PDF合并、网页摘要、图片转PDF、加水印、PDF转图片、拼接长图。"""
import base64
import io
import uuid

import httpx
from PIL import Image, ImageDraw, ImageFont
import qrcode
from pypdf import PdfWriter
from sqlalchemy.orm import Session

from app.core.config import UPLOAD_ROOT
from app.ai.llm.factory import get_llm_client_for_user


OUTPUT_DIR = UPLOAD_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_MAX_SIZE = 20 * 1024 * 1024
PDF_MAX_SIZE = 50 * 1024 * 1024

# 中文字体候选路径
FONT_PATHS = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]


def _load_font(size: int):
    """尝试加载中文字体，失败则用默认字体。"""
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _to_rgb(img: Image.Image) -> Image.Image:
    """统一转 RGB，处理透明通道。"""
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            bg.paste(img, mask=img.split()[-1])
        else:
            bg.paste(img)
        return bg
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


class ExtToolsService:

    # ==================== 1. 图片压缩 ====================
    def compress_image(self, content: bytes, quality: int = 70, max_width: int = 1600) -> dict:
        if len(content) == 0:
            raise ValueError("图片为空")
        if len(content) > IMAGE_MAX_SIZE:
            raise ValueError(f"图片过大（{len(content) // 1024 // 1024}MB），限制 20MB")

        try:
            img = Image.open(io.BytesIO(content))
        except Exception:
            raise ValueError("无法识别图片格式")

        original_size = len(content)
        img = _to_rgb(img)

        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=quality, optimize=True)
        out_bytes = out.getvalue()

        filename = f"compressed_{uuid.uuid4().hex}.jpg"
        (OUTPUT_DIR / filename).write_bytes(out_bytes)

        return {
            "filename": filename,
            "url": f"/static/output/{filename}",
            "original_size": original_size,
            "compressed_size": len(out_bytes),
            "saved_percent": round((1 - len(out_bytes) / original_size) * 100, 1),
            "width": img.width,
            "height": img.height,
        }

    # ==================== 2. 二维码生成 ====================
    def generate_qrcode(self, text: str, size: int = 400, logo_content: bytes | None = None) -> dict:
        if not text or not text.strip():
            raise ValueError("内容不能为空")
        if len(text) > 1000:
            raise ValueError("内容过长，最多 1000 字符")

        error_level = (
            qrcode.constants.ERROR_CORRECT_H if logo_content
            else qrcode.constants.ERROR_CORRECT_M
        )

        qr = qrcode.QRCode(version=None, error_correction=error_level, box_size=10, border=2)
        qr.add_data(text)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qr_img = qr_img.resize((size, size), Image.LANCZOS)

        if logo_content:
            try:
                logo = _to_rgb(Image.open(io.BytesIO(logo_content)))
                logo_size = int(size * 0.22)
                logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

                padding = max(6, int(size * 0.015))
                bordered_size = logo_size + padding * 2
                logo_bg = Image.new("RGB", (bordered_size, bordered_size), "white")
                logo_bg.paste(logo, (padding, padding))

                pos = ((size - bordered_size) // 2, (size - bordered_size) // 2)
                qr_img.paste(logo_bg, pos)
            except Exception as e:
                raise ValueError(f"Logo 处理失败：{str(e)}")

        filename = f"qrcode_{uuid.uuid4().hex}.png"
        (OUTPUT_DIR / filename).write_bytes(self._img_to_bytes(qr_img, "PNG"))

        return {
            "filename": filename,
            "url": f"/static/output/{filename}",
            "size": size,
            "has_logo": bool(logo_content),
        }

    # ==================== 3. PDF 合并 ====================
    def merge_pdfs(self, pdf_files: list[tuple[str, bytes]]) -> dict:
        if len(pdf_files) < 2:
            raise ValueError("至少需要 2 个 PDF 文件")

        total_size = sum(len(c) for _, c in pdf_files)
        if total_size > PDF_MAX_SIZE:
            raise ValueError(f"总大小过大（{total_size // 1024 // 1024}MB），限制 50MB")

        writer = PdfWriter()
        try:
            for _, content in pdf_files:
                writer.append(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"PDF 解析失败：{str(e)}")

        filename = f"merged_{uuid.uuid4().hex}.pdf"
        file_path = OUTPUT_DIR / filename
        with open(file_path, "wb") as f:
            writer.write(f)
        writer.close()

        return {
            "filename": filename,
            "url": f"/static/output/{filename}",
            "file_count": len(pdf_files),
            "total_size": total_size,
        }

    # ==================== 4. 网页摘要 ====================
    async def summarize_webpage(self, db: Session, user_id: int, url: str) -> dict:
        if not url or not url.startswith(("http://", "https://")):
            raise ValueError("URL 必须以 http:// 或 https:// 开头")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"https://r.jina.ai/{url}",
                    headers={"User-Agent": "suishouyi/1.0"},
                )
            if resp.status_code != 200:
                raise ValueError(f"网页抓取失败：HTTP {resp.status_code}")
            content = resp.text[:15000]
        except httpx.TimeoutException:
            raise ValueError("网页抓取超时，请稍后再试")
        except Exception as e:
            raise ValueError(f"网页抓取失败：{str(e)}")

        client = get_llm_client_for_user(db, user_id)
        prompt = f"请总结以下网页内容的核心要点：\n\n{content}"
        summary = await client.chat(prompt)

        return {"url": url, "summary": summary, "content_length": len(content)}

    # ==================== 5. 图片转 PDF ====================
    def image_to_pdf(self, images: list[bytes]) -> dict:
        """把多张图片合并成一个 PDF。"""
        if not images:
            raise ValueError("没有图片")

        total_size = sum(len(c) for c in images)
        if total_size > IMAGE_MAX_SIZE:
            raise ValueError("总图片过大")

        pil_images = []
        for content in images:
            try:
                img = _to_rgb(Image.open(io.BytesIO(content)))
                pil_images.append(img)
            except Exception:
                raise ValueError("有图片无法识别")

        filename = f"images_{uuid.uuid4().hex}.pdf"
        file_path = OUTPUT_DIR / filename

        pil_images[0].save(
            file_path, "PDF",
            save_all=True,
            append_images=pil_images[1:],
            resolution=100.0,
        )

        return {
            "filename": filename,
            "url": f"/static/output/{filename}",
            "image_count": len(images),
            "total_size": total_size,
        }

    # ==================== 6. 图片加水印 ====================
    def add_watermark(
        self,
        content: bytes,
        text: str,
        position: str = "br",
        opacity: int = 80,
    ) -> dict:
        """给图片加文字水印。position: tl / tr / bl / br / center / tile。"""
        if not text or not text.strip():
            raise ValueError("水印文字不能为空")

        try:
            img = _to_rgb(Image.open(io.BytesIO(content)))
        except Exception:
            raise ValueError("无法识别图片格式")

        # 水印文字大小按图片宽度自适应
        font_size = max(20, int(img.width * 0.04))
        font = _load_font(font_size)

        # 用一个透明层画水印，再合成
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 计算文字尺寸
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # 位置映射
        padding = 30
        positions = {
            "tl": (padding, padding),
            "tr": (img.width - text_w - padding, padding),
            "bl": (padding, img.height - text_h - padding),
            "br": (img.width - text_w - padding, img.height - text_h - padding),
            "center": ((img.width - text_w) // 2, (img.height - text_h) // 2),
        }

        alpha = int(255 * opacity / 100)

        if position == "tile":
            # 平铺水印（斜着铺满全图）
            tile = Image.new("RGBA", img.size, (0, 0, 0, 0))
            tile_draw = ImageDraw.Draw(tile)
            step_x = text_w + 200
            step_y = text_h + 300
            for x in range(0, img.width, step_x):
                for y in range(0, img.height, step_y):
                    tile_draw.text((x, y), text, font=font, fill=(128, 128, 128, alpha))
            overlay = tile.rotate(30, expand=False, fillcolor=(0, 0, 0, 0))
        else:
            pos = positions.get(position, positions["br"])
            draw.text(pos, text, font=font, fill=(128, 128, 128, alpha))

        # 合成
        img_rgba = img.convert("RGBA")
        final = Image.alpha_composite(img_rgba, overlay).convert("RGB")

        filename = f"watermark_{uuid.uuid4().hex}.jpg"
        (OUTPUT_DIR / filename).write_bytes(self._img_to_bytes(final, "JPEG", quality=90))

        return {
            "filename": filename,
            "url": f"/static/output/{filename}",
            "text": text,
            "position": position,
        }

    # ==================== 7. PDF 转图片 ====================
    def pdf_to_images(self, content: bytes, max_pages: int = 20) -> dict:
        """把 PDF 每页转成 PNG 图片。"""
        if not content:
            raise ValueError("PDF 为空")

        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ValueError("服务端未安装 PyMuPDF，请先 pip install pymupdf")

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            raise ValueError(f"PDF 解析失败：{str(e)}")

        total_pages = doc.page_count
        images = []
        limit = min(total_pages, max_pages)

        for i in range(limit):
            page = doc.load_page(i)
            # 2 倍缩放，输出更清晰
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)

            filename = f"pdf_page_{uuid.uuid4().hex}_{i+1}.png"
            file_path = OUTPUT_DIR / filename
            pix.save(str(file_path))

            images.append({
                "page": i + 1,
                "filename": filename,
                "url": f"/static/output/{filename}",
            })

        doc.close()

        return {
            "total_pages": total_pages,
            "converted": limit,
            "images": images,
        }

    # ==================== 8. 图片拼接长图 ====================
    def merge_images_vertical(self, images: list[bytes], direction: str = "vertical") -> dict:
        """把多张图拼接成一张。direction: vertical / horizontal。"""
        if len(images) < 2:
            raise ValueError("至少需要 2 张图片")
        if len(images) > 10:
            raise ValueError("最多 10 张图片")

        pil_images = []
        for content in images:
            try:
                img = _to_rgb(Image.open(io.BytesIO(content)))
                pil_images.append(img)
            except Exception:
                raise ValueError("有图片无法识别")

        if direction == "horizontal":
            # 横向拼接：统一高度
            target_h = min(img.height for img in pil_images)
            # 缩放到高度统一
            scaled = []
            for img in pil_images:
                ratio = target_h / img.height
                new_w = int(img.width * ratio)
                scaled.append(img.resize((new_w, target_h), Image.LANCZOS))

            total_w = sum(img.width for img in scaled)
            canvas = Image.new("RGB", (total_w, target_h), "white")
            x = 0
            for img in scaled:
                canvas.paste(img, (x, 0))
                x += img.width
        else:
            # 纵向拼接：统一宽度
            target_w = min(img.width for img in pil_images)
            scaled = []
            for img in pil_images:
                ratio = target_w / img.width
                new_h = int(img.height * ratio)
                scaled.append(img.resize((target_w, new_h), Image.LANCZOS))

            total_h = sum(img.height for img in scaled)
            canvas = Image.new("RGB", (target_w, total_h), "white")
            y = 0
            for img in scaled:
                canvas.paste(img, (0, y))
                y += img.height

        # 限制长图最大尺寸（防止内存爆）
        if canvas.width > 2000:
            ratio = 2000 / canvas.width
            canvas = canvas.resize((2000, int(canvas.height * ratio)), Image.LANCZOS)
        if canvas.height > 20000:
            raise ValueError("拼接后过长，请减少图片数量")

        filename = f"merged_img_{uuid.uuid4().hex}.jpg"
        (OUTPUT_DIR / filename).write_bytes(self._img_to_bytes(canvas, "JPEG", quality=88))

        return {
            "filename": filename,
            "url": f"/static/output/{filename}",
            "image_count": len(images),
            "direction": direction,
            "width": canvas.width,
            "height": canvas.height,
        }

    # ==================== 工具方法 ====================
    def _img_to_bytes(self, img: Image.Image, fmt: str, **kwargs) -> bytes:
        out = io.BytesIO()
        img.save(out, format=fmt, **kwargs)
        return out.getvalue()


ext_tools_service = ExtToolsService()