import logging
from dataclasses import dataclass

from openai import OpenAI
from PySide6.QtCore import QObject, Signal

from .prompts import (
    SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, UNCLEAR_TAG,
    POLISH_SYSTEM_PROMPT, POLISH_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)


@dataclass
class OrganizeResult:
    text: str
    is_clear: bool  # False when LLM deems the input too vague


class LLMEngine(QObject):
    """LLM engine for organizing transcribed text into structured requirements.
    Supports both Qwen (dashscope) and local vllm via OpenAI-compatible API."""

    organization_done = Signal(str)
    progress_updated = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, provider="qwen", api_key="", base_url="", model="",
                 vllm_base_url="", vllm_model=""):
        super().__init__()
        self._provider = provider
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._vllm_base_url = vllm_base_url
        self._vllm_model = vllm_model

    def update_config(self, provider: str, api_key: str, base_url: str,
                      model: str, vllm_base_url: str, vllm_model: str):
        self._provider = provider
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._vllm_base_url = vllm_base_url
        self._vllm_model = vllm_model

    def _get_client(self) -> tuple[OpenAI, str]:
        if self._provider == "vllm":
            client = OpenAI(
                base_url=self._vllm_base_url,
                api_key="not-needed",
            )
            return client, self._vllm_model
        else:
            if not self._api_key:
                raise ValueError("请先在设置中配置 Qwen API Key")
            client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
            )
            return client, self._model

    def organize(self, transcription: str) -> OrganizeResult | None:
        """Organize raw transcription into structured dev requirements."""
        print(f"[llm] organize: input {len(transcription)} chars")
        self.progress_updated.emit("正在使用 AI 整理需求...")

        try:
            client, model = self._get_client()
            print(f"[llm]   provider={self._provider}  model={model}")
            user_msg = USER_PROMPT_TEMPLATE.format(transcription=transcription)

            print("[llm]   calling chat.completions.create...")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=4096,
            )

            result = response.choices[0].message.content.strip()
            print(f"[llm]   raw response: {len(result)} chars")
            print(f"[llm]   response preview: {result[:300]!r}")
            if not result:
                print("[llm]   ERROR: empty response")
                self.error_occurred.emit("AI 返回了空结果")
                return None

            is_clear = not result.startswith(UNCLEAR_TAG)
            clean_text = result
            if not is_clear:
                clean_text = result[len(UNCLEAR_TAG):].strip()

            print(f"[llm]   is_clear={is_clear}, clean_text={len(clean_text)} chars")
            logger.info(
                "LLM organization complete, %d chars, clear=%s",
                len(result), is_clear,
            )
            self.progress_updated.emit("AI 需求整理完成")
            self.organization_done.emit(clean_text)
            return OrganizeResult(text=clean_text, is_clear=is_clear)

        except Exception as e:
            print(f"[llm] organize EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"AI 整理失败: {e}")
            return None

    def polish(self, transcription: str) -> str:
        """Polish raw transcription text without structuring into requirements."""
        print(f"[llm] polish: input {len(transcription)} chars")
        self.progress_updated.emit("正在润色语音内容...")

        try:
            client, model = self._get_client()
            user_msg = POLISH_USER_TEMPLATE.format(transcription=transcription)

            print("[llm]   calling chat.completions.create for polish...")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": POLISH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=4096,
            )

            result = response.choices[0].message.content.strip()
            print(f"[llm]   polish result: {len(result)} chars")
            print(f"[llm]   polish preview: {result[:200]!r}")
            if not result:
                print("[llm]   polish empty, fallback to raw")
                return transcription

            logger.info("Polish complete, %d chars", len(result))
            self.progress_updated.emit("润色完成")
            return result

        except Exception as e:
            print(f"[llm] polish EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            logger.warning("Polish failed, using raw text: %s", e)
            return transcription
