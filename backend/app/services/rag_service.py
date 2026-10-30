import re
from typing import Dict, Any, List
from app.db.database import db
from app.services.llm_verifier import llm_verifier
from app.core.logging import logger

class DocumentRAGService:
    """
    RAG service for natural language question answering with page citations.
    """
    async def chunk_and_index_document(self, doc_id: str, pages: List[Dict[str, Any]]):
        chunks = []
        chunk_idx = 0

        for p in pages:
            page_num = p.get("page", 1)
            text = p.get("text", "")
            if not text:
                continue

            # Split page text into paragraphs / chunks of ~500 chars
            paragraphs = [para.strip() for para in text.split("\n\n") if para.strip()]
            for para in paragraphs:
                chunks.append({
                    "page_number": page_num,
                    "chunk_index": chunk_idx,
                    "content": para
                })
                chunk_idx += 1

        if chunks:
            await db.save_chunks(doc_id, chunks)

    async def answer_query(self, doc_id: str, query: str) -> Dict[str, Any]:
        chunks = await db.get_chunks(doc_id)
        if not chunks:
            # Fallback to fetching document raw text directly
            doc = await db.get_document(doc_id)
            if doc and doc.get("raw_text"):
                chunks = [{"page_number": 1, "chunk_index": 0, "content": doc["raw_text"][:2000]}]
            else:
                return {
                    "answer": "No indexed content found for this document.",
                    "citations": []
                }

        # 1. Retrieve top matching chunks using keyword / term overlap
        query_words = set(re.findall(r"\w+", query.lower()))
        scored_chunks = []
        for ch in chunks:
            content_lower = ch["content"].lower()
            overlap = sum(1 for w in query_words if w in content_lower)
            if overlap > 0:
                scored_chunks.append((overlap, ch))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [c[1] for c in scored_chunks[:3]] if scored_chunks else chunks[:2]

        citations = [
            {"page": c.get("page_number", 1), "content": c["content"][:200]}
            for c in top_chunks
        ]

        # 2. Generate answer via LLM if available
        if llm_verifier.is_available():
            context_text = "\n\n".join([f"[Page {c.get('page_number', 1)}]: {c['content']}" for c in top_chunks])
            prompt = (
                f"Based strictly on the following document context, provide a direct, concise answer to the question. "
                f"Do not guess or assume.\n\nContext:\n{context_text}\n\nQuestion: {query}"
            )
            try:
                if llm_verifier.provider == "gemini":
                    resp = llm_verifier.client.models.generate_content(
                        model=llm_verifier.model_name,
                        contents=prompt
                    )
                    answer = resp.text.strip()
                elif llm_verifier.provider == "openai":
                    resp = llm_verifier.client.chat.completions.create(
                        model=llm_verifier.model_name,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    answer = resp.choices[0].message.content.strip()
                else:
                    answer = top_chunks[0]["content"]
            except Exception as e:
                logger.error(f"RAG LLM query failed: {e}")
                answer = top_chunks[0]["content"]
        else:
            # Deterministic excerpt answer
            answer = f"Found relevant reference:\n\n{top_chunks[0]['content']}"

        return {
            "answer": answer,
            "citations": citations
        }

rag_service = DocumentRAGService()

