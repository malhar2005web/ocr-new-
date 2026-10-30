import json
import re
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.services.json_generator import clean_dynamic_json

class LLMVerificationEngine:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.model_name = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY
        self.client = None

        if self.api_key:
            self._init_client()
        else:
            logger.info("LLM_API_KEY not configured. Running in deterministic extraction mode.")

    def _init_client(self):
        try:
            if self.provider == "gemini":
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Google Gemini client with model '{self.model_name}' (Free Tier).")
            elif self.provider == "openai":
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"Initialized OpenAI client with model '{self.model_name}'.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.client = None

    def is_available(self) -> bool:
        return self.client is not None and bool(self.api_key)

    def verify_and_structure_document(
        self,
        doc_type: str,
        raw_text: str,
        ocr_tables: list,
        discrepancy_context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Executes LLM's 7 roles:
        1. Classification verification
        2. Semantic understanding
        3. Field mapping
        4. Table reconstruction
        5. Context distinction (Seller vs Buyer vs Consignee)
        6. Cross-verification against source text
        7. Recovery
        """
        if not self.is_available():
            return None

        truncated_text = raw_text[:30000]

        system_prompt = (
            "You are an expert Document Intelligence Auditor & Field Mapper. "
            "Your sole job is to interpret the provided OCR text and reconstruct accurate, structured JSON.\n\n"
            "STRICT RULES:\n"
            "1. NEVER invent, hallucinate, or assume missing information (e.g. GSTIN, bank details, item rows).\n"
            "2. NEVER include null, empty strings (''), placeholders ('-', 'N/A'), or empty arrays/objects. "
            "If a field is not present in the OCR text, OMIT IT ENTIRELY.\n"
            "3. DO NOT calculate arithmetic or totals; simply extract the exact printed numbers from the text.\n"
            "4. Distinguish carefully between SELLER (supplier/issuer), BUYER (customer/billed to), and CONSIGNEE (shipped to).\n"
            "5. Extract EVERY individual item line in tables. Do not merge separate rows.\n"
            "6. Output ONLY valid, parseable JSON without any Markdown code blocks or conversational text."
        )

        user_content = (
            f"DOCUMENT TYPE DETECTED: {doc_type}\n\n"
            f"PRIMARY OCR EXTRACTED TEXT:\n{truncated_text}\n\n"
            f"DETERMINISTIC TABLES DETECTED ({len(ocr_tables)}):\n{json.dumps(ocr_tables[:5], indent=2)}\n\n"
        )

        if discrepancy_context:
            user_content += (
                f"\n[RECOVERY ALERT: PREVIOUS PASS DISCREPANCY DETECTED]\n"
                f"{discrepancy_context}\n"
                f"Please carefully re-examine the raw text specifically for the missing or mismatched details."
            )

        user_content += "\nReturn structured JSON with all actually available sections."

        try:
            if self.provider == "gemini":
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=user_content,
                    config={
                        "system_instruction": system_prompt,
                        "response_mime_type": "application/json"
                    }
                )
                response_text = response.text

            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ]
                )
                response_text = response.choices[0].message.content

            else:
                return None

            cleaned_json_str = response_text.strip()
            cleaned_json_str = re.sub(r"^```(?:json)?\s*", "", cleaned_json_str)
            cleaned_json_str = re.sub(r"\s*```$", "", cleaned_json_str)

            parsed = json.loads(cleaned_json_str)
            return clean_dynamic_json(parsed)

        except Exception as e:
            logger.error(f"LLM verification call failed: {e}")
            return None

llm_verifier = LLMVerificationEngine()
