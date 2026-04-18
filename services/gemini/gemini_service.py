from typing import Dict, Optional
from langchain_google_genai import GoogleGenerativeAI
import google.generativeai as genai
from services.gemini.gemini_types import GeminiModel
from services.gemini.gemini_setup import GeminiConfig
from common.logger import get_logger


class GeminiService:
    def __init__(self, config: Optional[GeminiConfig] = None):
        if config is None:
            from config.config import settings
            config = GeminiConfig(
                api_key=settings.GOOGLE_API_KEY or "",
                temperature=settings.GEMINI_TEMPERATURE,
                max_tokens=settings.GEMINI_MAX_TOKENS,
                top_p=settings.GEMINI_TOP_P,
                top_k=settings.GEMINI_TOP_K,
                timeout=settings.GEMINI_TIMEOUT,
                max_retries=settings.GEMINI_MAX_RETRIES,
                retry_delay=settings.GEMINI_RETRY_DELAY,
            )
        self.api_key = config.api_key
        self.model = GeminiModel.GEMINI_2_5_FLASH  # Use the flash model which is more widely supported
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.top_p = config.top_p
        self.top_k = config.top_k
        self.timeout = config.timeout
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay
        self.enable_logging = config.enable_logging
        self.log_requests = config.log_requests
        self.safety_settings = config.get_safety_settings()

        self.logger = get_logger(self.__class__.__name__)

        self.client = GoogleGenerativeAI(
            api_key=self.api_key,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            top_k=self.top_k,
            timeout=self.timeout,
            #max_retries=self.max_retries,
            max_retries=2,  # Disable LangChain retry
            retry_delay=self.retry_delay,
            safety_settings=self.safety_settings,
        )

    async def generate_response(self, prompt: str) -> str:
        """Generate a single response from the Gemini model."""
        try:
            response = await self.client.ainvoke(prompt)
            return response
        except Exception as e:
            err_str = str(e)
            if "Quota exceeded" in err_str or "429" in err_str:
                self.logger.error("Quota exceeded. Stopping retry.")
                return "Quota exceeded. Please wait for quota reset or upgrade plan."
            if self.enable_logging:
                print(f"Error generating response: {e}")
            raise

    async def generate_batch_response(self, prompts: list[str]) -> list[str]:
        """Generate batch responses from the Gemini model."""
        try:
            responses = await self.client.abatch(prompts)
            return responses
        except Exception as e:
            err_str = str(e)
            if "Quota exceeded" in err_str or "429" in err_str:
                self.logger.error("Quota exceeded. Stopping retry.")
                return ["Quota exceeded. Please wait for quota reset or upgrade plan."] * len(prompts)
            if self.enable_logging:
                print(f"Error generating batch responses: {e}")
            raise

    def generate_response_sync(self, prompt: str) -> str:
        """Generate a single response synchronously."""
        try:
            response = self.client.invoke(prompt)
            return response
        except Exception as e:
            err_str = str(e)
            if "Quota exceeded" in err_str or "429" in err_str:
                self.logger.error("Quota exceeded. Stopping retry.")
                return "Quota exceeded. Please wait for quota reset or upgrade plan."
            if self.enable_logging:
                print(f"Error generating sync response: {e}")
            raise

    def extract_tool(self, message: str) -> dict:
        """Extract tool name and parameters from a natural language message.

        Returns a dict with keys: tool_name (str), parameters (dict).
        Falls back to empty values on any error.
        """
        import json
        from services.gemini.gemini_prompt import build_tool_extraction_prompt

        prompt = build_tool_extraction_prompt(message)
        try:
            raw = self.generate_response_sync(prompt)
            # Strip markdown code fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            data = json.loads(clean.strip())
            return {
                "tool_name": data.get("tool_name", ""),
                "parameters": data.get("parameters") or {},
            }
        except Exception as exc:
            self.logger.error(f"extract_tool failed: {exc}")
            return {"tool_name": "", "parameters": {}}

    def generate_answer(self, user_message: str, tool_name: str, data) -> str:
        """Ask Gemini to convert raw HRX data into a natural-language answer."""
        from services.gemini.gemini_prompt import build_answer_prompt

        self.logger.info(f"[gemini] generate_answer | tool='{tool_name}'")
        prompt = build_answer_prompt(user_message, tool_name, data)
        try:
            answer = self.generate_response_sync(prompt)
            self.logger.info("[gemini] generate_answer success")
            return answer.strip()
        except Exception as exc:
            self.logger.error(f"[gemini] generate_answer failed: {exc}")
            # Graceful fallback
            count = len(data) if isinstance(data, list) else 1
            return f"Retrieved {count} record(s) for {tool_name}."

    def handle_out_of_scope(self, user_message: str) -> str:
        """Ask Gemini to generate a polite out-of-scope refusal response."""
        from services.gemini.gemini_prompt import build_out_of_scope_prompt

        self.logger.info(f"[gemini] handle_out_of_scope | message='{user_message[:80]}'")
        prompt = build_out_of_scope_prompt(user_message)
        try:
            answer = self.generate_response_sync(prompt)
            self.logger.info("[gemini] handle_out_of_scope response generated")
            return answer.strip()
        except Exception as exc:
            self.logger.error(f"[gemini] handle_out_of_scope failed: {exc}")
            return (
                "I'm an HRX assistant and can only help with HR-related topics "
                "such as attendance, leave, and payroll. "
                "I'm unable to assist with this request."
            )

    @staticmethod
    def parse_keywords_from_csv(csv_text: str) -> list[str]:
        # Best-effort parse: split by comma, strip whitespace, dedupe and keep order
        seen = set()
        keywords: list[str] = []
        for raw in csv_text.split(","):
            token = raw.strip()
            if not token:
                continue
            lowered = token.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            keywords.append(token)
        return keywords

    async def analyze_dataset_context(self, job_title: str, job_description: str, dataset_content: str) -> dict:
        """Analyze dataset content to extract job context insights."""
        from services.gemini.gemini_prompt import GeminiPrompt
        import json
        
        prompt_service = GeminiPrompt()
        prompt = prompt_service.get_dataset_context_analysis_prompt(
            job_title=job_title,
            job_description=job_description,
            dataset_content=dataset_content[:3001]  # Limit to avoid token limits
        )
        
        try:
            response = await self.generate_response(prompt)
            # Try to parse as JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback to basic structure if JSON parsing fails
            return {
                "market_insights": ["Unable to parse dataset insights"],
                "enhanced_keywords": [],
                "candidate_profile_enhancements": [],
                "search_strategies": ["Standard search approach"]
            }