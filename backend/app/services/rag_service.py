"""RAG 服务：文档切分 → Embedding → 检索 → 生成。
Embedding 用「用户自己配置的」硅基流动 Key，平台零成本。
"""
import json
import uuid

import httpx
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import UPLOAD_ROOT
from app.models.document import RagDocument, RagChunk
from app.models.user_config import UserConfig
from app.services.file_parser import parse_file, get_extension
from app.ai.llm.factory import get_llm_client_for_user


CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 5


class MissingEmbeddingConfigError(Exception):
    """用户没有配置 Embedding Key。"""
    pass


class RagService:

    def _get_embedding_config(self, db: Session, user_id: int) -> tuple[str, str, str]:
        """读取用户的 Embedding 配置。"""
        config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not config or not config.embedding_api_key:
            raise MissingEmbeddingConfigError(
                "请先在「设置 → API 配置 → 知识库」中配置你的 Embedding Key"
            )
        return (
            config.embedding_api_key,
            config.embedding_base_url or "https://api.siliconflow.cn/v1",
            config.embedding_model or "BAAI/bge-m3",
        )

    # ==================== 1. Embedding ====================
    async def _embed(self, db: Session, user_id: int, texts: list[str]) -> list[list[float]]:
        api_key, base_url, model = self._get_embedding_config(db, user_id)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        all_embeddings = []
        for i in range(0, len(texts), 32):
            batch = texts[i:i + 32]
            data = {"model": model, "input": batch}
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{base_url}/embeddings", headers=headers, json=data)
            if resp.status_code != 200:
                raise ValueError(f"Embedding 失败：HTTP {resp.status_code} - {resp.text[:200]}")
            result = resp.json()
            for item in result["data"]:
                all_embeddings.append(item["embedding"])

        return all_embeddings

    # ==================== 2. 切分 ====================
    def _chunk_text(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = end - CHUNK_OVERLAP
        return chunks

    # ==================== 3. 索引 ====================
    async def index_document(
        self, db: Session, user_id: int, filename: str, content: bytes,
    ) -> RagDocument:
        # 先检查 Key 是否配置
        self._get_embedding_config(db, user_id)

        upload_dir = UPLOAD_ROOT / "rag"
        upload_dir.mkdir(parents=True, exist_ok=True)

        ext = get_extension(filename)
        stored = upload_dir / f"{uuid.uuid4().hex}.{ext}"
        stored.write_bytes(content)

        doc = RagDocument(
            user_id=user_id, filename=filename, file_type=ext,
            file_size=len(content), status="processing",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        try:
            text = parse_file(str(stored), ext)
            if not text or not text.strip():
                raise ValueError("文档没有可提取的文本")

            chunks = self._chunk_text(text)
            if not chunks:
                raise ValueError("文档内容为空")

            embeddings = await self._embed(db, user_id, chunks)

            for chunk_text, emb in zip(chunks, embeddings):
                db.add(RagChunk(
                    user_id=user_id, document_id=doc.id,
                    content=chunk_text, embedding=json.dumps(emb),
                ))

            doc.chunk_count = len(chunks)
            doc.status = "done"
            db.commit()
            db.refresh(doc)

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)
            db.commit()
            raise

        return doc

    # ==================== 4. 检索 ====================
    async def _retrieve(
        self, db: Session, user_id: int, query: str, top_k: int = TOP_K,
    ) -> list[dict]:
        chunks = db.query(RagChunk).filter(RagChunk.user_id == user_id).all()
        if not chunks:
            return []

        query_emb = (await self._embed(db, user_id, [query]))[0]
        query_vec = np.array(query_emb, dtype=np.float32)

        scored = []
        for c in chunks:
            try:
                vec = np.array(json.loads(c.embedding), dtype=np.float32)
                sim = float(np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-8))
                scored.append((sim, c))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        return [
            {"content": c.content, "similarity": round(sim, 3), "document_id": c.document_id}
            for sim, c in top
        ]

    # ==================== 5. 问答 ====================
    async def ask(self, db: Session, user_id: int, question: str) -> dict:
        retrieved = await self._retrieve(db, user_id, question)

        if not retrieved:
            return {"answer": "你的知识库还没有内容，请先上传文档。", "sources": []}

        context = "\n\n---\n\n".join([
            f"[片段 {i+1}]\n{r['content']}"
            for i, r in enumerate(retrieved)
        ])

        prompt = f"""请基于以下参考资料回答用户的问题。

要求：
1. 只使用参考资料中的信息回答
2. 如果资料里没有答案，直接说"参考资料中没有相关信息"
3. 回答要清晰、有条理

参考资料：
---
{context}
---

用户问题：{question}
"""

        client = get_llm_client_for_user(db, user_id)
        answer = await client.chat(prompt)

        return {"answer": answer, "sources": retrieved}

    # ==================== 6. 管理 ====================
    def list_documents(self, db: Session, user_id: int) -> list[RagDocument]:
        return (
            db.query(RagDocument)
            .filter(RagDocument.user_id == user_id)
            .order_by(RagDocument.created_at.desc())
            .all()
        )

    def delete_document(self, db: Session, user_id: int, doc_id: int) -> bool:
        doc = db.query(RagDocument).filter(
            RagDocument.user_id == user_id, RagDocument.id == doc_id
        ).first()
        if not doc:
            return False
        db.query(RagChunk).filter(RagChunk.document_id == doc_id).delete()
        db.delete(doc)
        db.commit()
        return True


rag_service = RagService()