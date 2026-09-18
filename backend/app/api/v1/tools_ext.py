"""实用工具接口：图片压缩、二维码、PDF、网页摘要、邮件发送。"""
import asyncio
import base64

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.ext_tools_service import ext_tools_service
from app.services.email_service import email_service
from app.core.logging import internal_error
from app.core.security import verify_internal_token
from app.ai.llm.factory import MissingUserConfigError


router = APIRouter()


# ==================== 1. 图片压缩 ====================
@router.post("/ext/image/compress", summary="图片压缩")
async def compress_image(
    file: UploadFile = File(...),
    quality: int = Form(70),
    current_user: User = Depends(get_current_user),
):
    try:
        content = await file.read()
        return await asyncio.to_thread(ext_tools_service.compress_image, content, quality)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 2. 二维码 ====================
@router.post("/ext/qrcode", summary="生成二维码（可嵌入 Logo）")
async def generate_qrcode(
    text: str = Form(...),
    size: int = Form(400),
    logo: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
):
    try:
        logo_content = None
        if logo is not None and logo.filename:
            logo_content = await logo.read()
        return await asyncio.to_thread(
            ext_tools_service.generate_qrcode, text, size, logo_content
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 3. PDF 合并（multipart，适合电脑端） ====================
@router.post("/ext/pdf/merge", summary="合并 PDF（多文件表单）")
async def merge_pdfs(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        pdf_files = [(f.filename, await f.read()) for f in files]
        return await asyncio.to_thread(ext_tools_service.merge_pdfs, pdf_files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 3b. PDF 合并（base64，适合小程序） ====================
@router.post("/ext/pdf/merge_base64", summary="合并 PDF（base64 版，小程序用）")
async def merge_pdfs_base64(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    try:
        files = payload.get("files") or []
        if len(files) < 2:
            raise ValueError("至少需要 2 个 PDF 文件")

        pdf_files = []
        for f in files:
            name = f.get("name", "file.pdf")
            content_b64 = f.get("content", "")
            if "," in content_b64:
                content_b64 = content_b64.split(",", 1)[1]
            pdf_files.append((name, base64.b64decode(content_b64)))

        return await asyncio.to_thread(ext_tools_service.merge_pdfs, pdf_files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("合并 PDF", e)


# ==================== 4. 网页摘要 ====================
@router.post("/ext/web/summary", summary="网页摘要")
async def summarize_webpage(
    url: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await ext_tools_service.summarize_webpage(db, current_user.id, url)
    except MissingUserConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("网页摘要", e)


# ==================== 5. 图片转 PDF ====================
@router.post("/ext/image/to_pdf", summary="图片转 PDF")
async def image_to_pdf(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        images = [await f.read() for f in files]
        return await asyncio.to_thread(ext_tools_service.image_to_pdf, images)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 6. 图片加水印 ====================
@router.post("/ext/image/watermark", summary="图片加水印")
async def add_watermark(
    file: UploadFile = File(...),
    text: str = Form(...),
    position: str = Form("br"),
    opacity: int = Form(80),
    current_user: User = Depends(get_current_user),
):
    try:
        content = await file.read()
        return await asyncio.to_thread(
            ext_tools_service.add_watermark, content, text, position, opacity
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 7. PDF 转图片 ====================
@router.post("/ext/pdf/to_images", summary="PDF 转图片")
async def pdf_to_images(
    file: UploadFile = File(...),
    max_pages: int = Form(20),
    current_user: User = Depends(get_current_user),
):
    try:
        content = await file.read()
        return await asyncio.to_thread(ext_tools_service.pdf_to_images, content, max_pages)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 8. 图片拼接长图（base64 数组） ====================
@router.post("/ext/image/merge", summary="图片拼接长图")
async def merge_images(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    try:
        images_b64 = payload.get("images") or []
        direction = payload.get("direction") or "vertical"

        if len(images_b64) < 2:
            raise ValueError("至少需要 2 张图片")

        images = []
        for b64 in images_b64:
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            images.append(base64.b64decode(b64))

        return await asyncio.to_thread(
            ext_tools_service.merge_images_vertical, images, direction
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("拼接图片", e)


# ==================== 9. 邮件发送（内部接口，被工具调用触发） ====================
@router.post("/ext/email/send_internal", summary="发送邮件（内部）")
async def send_email_internal(
    payload: dict,
    x_internal_token: str = Header(None),
):
    """内部接口：通过工具调用触发。校验 INTERNAL_TOKEN，恒定时间比较。"""
    if not verify_internal_token(x_internal_token):
        raise HTTPException(status_code=403, detail="未授权")

    try:
        return email_service.send(
            email=payload.get("email", ""),
            auth_code=payload.get("auth_code", ""),
            smtp_host=payload.get("smtp_host", ""),
            smtp_port=int(payload.get("smtp_port", 465)),
            to=payload.get("to", ""),
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("发送邮件", e)