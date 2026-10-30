import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncpg
from app.core.config import settings
from app.core.logging import logger

class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._fallback_store: Dict[str, Dict[str, Any]] = {}
        self._fallback_audit: List[Dict[str, Any]] = []
        self._fallback_chunks: List[Dict[str, Any]] = []
        self.is_connected = False

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                dsn=settings.DATABASE_URL,
                min_size=1,
                max_size=10,
                timeout=5.0
            )
            self.is_connected = True
            logger.info("Connected to PostgreSQL successfully.")
            await self._initialize_schema()
        except Exception as e:
            self.is_connected = False
            logger.warning(
                f"PostgreSQL connection failed ({e}). Running in resilient local memory mode. "
                "All extractions will persist during server session."
            )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.is_connected = False
            logger.info("Closed PostgreSQL connection pool.")

    async def _initialize_schema(self):
        if not self.pool:
            return
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            try:
                schema_sql = schema_path.read_text(encoding="utf-8")
                async with self.pool.acquire() as conn:
                    await conn.execute(schema_sql)
                logger.info("PostgreSQL schema initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to execute schema.sql: {e}")

    async def save_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc_data.setdefault("created_at", now)
        doc_data.setdefault("updated_at", now)
        doc_id = doc_data["id"]

        if self.is_connected and self.pool:
            query = """
            INSERT INTO documents (
                id, filename, file_type, file_path, file_size, document_type,
                status, page_count, raw_text, normalized_json, metadata_json,
                error_message, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
            )
            ON CONFLICT (id) DO UPDATE SET
                document_type = EXCLUDED.document_type,
                status = EXCLUDED.status,
                page_count = EXCLUDED.page_count,
                raw_text = EXCLUDED.raw_text,
                normalized_json = EXCLUDED.normalized_json,
                metadata_json = EXCLUDED.metadata_json,
                error_message = EXCLUDED.error_message,
                updated_at = EXCLUDED.updated_at
            RETURNING *;
            """
            try:
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        query,
                        doc_data.get("id"),
                        doc_data.get("filename"),
                        doc_data.get("file_type"),
                        doc_data.get("file_path"),
                        doc_data.get("file_size"),
                        doc_data.get("document_type", "unclassified"),
                        doc_data.get("status", "pending"),
                        doc_data.get("page_count", 1),
                        doc_data.get("raw_text", ""),
                        json.dumps(doc_data.get("normalized_json") or {}),
                        json.dumps(doc_data.get("metadata_json") or {}),
                        doc_data.get("error_message"),
                        doc_data["created_at"],
                        doc_data["updated_at"]
                    )
                    return dict(row) if row else doc_data
            except Exception as e:
                logger.error(f"PostgreSQL save_document failed: {e}. Fallback to memory.")

        # In-memory storage fallback
        self._fallback_store[doc_id] = doc_data
        return doc_data

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        if self.is_connected and self.pool:
            query = "SELECT * FROM documents WHERE id = $1;"
            try:
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(query, doc_id)
                    if row:
                        d = dict(row)
                        if isinstance(d.get("normalized_json"), str):
                            d["normalized_json"] = json.loads(d["normalized_json"])
                        if isinstance(d.get("metadata_json"), str):
                            d["metadata_json"] = json.loads(d["metadata_json"])
                        return d
            except Exception as e:
                logger.error(f"PostgreSQL get_document failed: {e}")

        return self._fallback_store.get(doc_id)

    async def list_documents(
        self,
        document_type: Optional[str] = None,
        filename: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "DESC"
    ) -> Dict[str, Any]:
        offset = (page - 1) * limit

        if self.is_connected and self.pool:
            where_clauses = ["1=1"]
            params = []
            idx = 1

            if document_type:
                where_clauses.append(f"document_type = ${idx}")
                params.append(document_type)
                idx += 1
            if filename:
                where_clauses.append(f"filename ILIKE ${idx}")
                params.append(f"%{filename}%")
                idx += 1
            if status:
                where_clauses.append(f"status = ${idx}")
                params.append(status)
                idx += 1

            order_field = "created_at" if sort_by not in ["created_at", "filename", "status"] else sort_by
            order_dir = "ASC" if sort_order.upper() == "ASC" else "DESC"

            where_sql = " AND ".join(where_clauses)
            count_query = f"SELECT COUNT(*) FROM documents WHERE {where_sql};"
            data_query = f"""
                SELECT * FROM documents
                WHERE {where_sql}
                ORDER BY {order_field} {order_dir}
                LIMIT ${idx} OFFSET ${idx + 1};
            """

            try:
                async with self.pool.acquire() as conn:
                    total = await conn.fetchval(count_query, *params)
                    rows = await conn.fetch(data_query, *params, limit, offset)
                    docs = []
                    for r in rows:
                        d = dict(r)
                        if isinstance(d.get("normalized_json"), str):
                            d["normalized_json"] = json.loads(d["normalized_json"])
                        if isinstance(d.get("metadata_json"), str):
                            d["metadata_json"] = json.loads(d["metadata_json"])
                        docs.append(d)
                    return {"documents": docs, "total": total, "page": page, "limit": limit}
            except Exception as e:
                logger.error(f"PostgreSQL list_documents error: {e}")

        # In-memory fallback
        all_docs = list(self._fallback_store.values())
        if document_type:
            all_docs = [d for d in all_docs if d.get("document_type") == document_type]
        if filename:
            all_docs = [d for d in all_docs if filename.lower() in (d.get("filename") or "").lower()]
        if status:
            all_docs = [d for d in all_docs if d.get("status") == status]

        total = len(all_docs)
        reverse = sort_order.upper() != "ASC"
        all_docs.sort(key=lambda x: str(x.get("created_at") or ""), reverse=reverse)
        paged = all_docs[offset: offset + limit]

        return {"documents": paged, "total": total, "page": page, "limit": limit}

    async def save_chunks(self, doc_id: str, chunks: List[Dict[str, Any]]):
        if not chunks:
            return
        if self.is_connected and self.pool:
            query = """
            INSERT INTO document_chunks (document_id, page_number, chunk_index, content, embedding)
            VALUES ($1, $2, $3, $4, $5);
            """
            try:
                async with self.pool.acquire() as conn:
                    for ch in chunks:
                        await conn.execute(
                            query,
                            doc_id,
                            ch.get("page_number", 1),
                            ch.get("chunk_index", 0),
                            ch.get("content", ""),
                            json.dumps(ch.get("embedding") or {})
                        )
            except Exception as e:
                logger.error(f"PostgreSQL save_chunks failed: {e}")

        for ch in chunks:
            self._fallback_chunks.append({
                "document_id": doc_id,
                "page_number": ch.get("page_number", 1),
                "chunk_index": ch.get("chunk_index", 0),
                "content": ch.get("content", "")
            })

    async def get_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        if self.is_connected and self.pool:
            query = "SELECT * FROM document_chunks WHERE document_id = $1 ORDER BY chunk_index ASC;"
            try:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(query, doc_id)
                    return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"PostgreSQL get_chunks error: {e}")

        return [c for c in self._fallback_chunks if c["document_id"] == doc_id]

    async def save_audit(self, doc_id: str, action: str, details: Dict[str, Any]):
        now = datetime.now(timezone.utc)
        if self.is_connected and self.pool:
            query = "INSERT INTO document_audit (document_id, action, details, created_at) VALUES ($1, $2, $3, $4);"
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute(query, doc_id, action, json.dumps(details), now)
            except Exception as e:
                logger.error(f"PostgreSQL save_audit error: {e}")

        self._fallback_audit.append({
            "document_id": doc_id,
            "action": action,
            "details": details,
            "created_at": now
        })

db = DatabaseManager()

