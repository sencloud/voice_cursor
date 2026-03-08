import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict

CONFIG_DIR = Path.home() / ".voice_cursor"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class LLMConfig:
    provider: str = "qwen"  # "qwen" or "vllm"
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-max"
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "Qwen/Qwen3.5-14B-Instruct"


@dataclass
class WhisperConfig:
    model_size: str = "medium"  # tiny, base, small, medium, large-v3
    device: str = "auto"  # auto, cpu, cuda
    language: str = "zh"


@dataclass
class CursorConfig:
    shortcut_open_chat: str = "ctrl+shift+l"  # New Agent (macOS: cmd+shift+l)
    shortcut_paste: str = "ctrl+v"  # macOS: cmd+v
    shortcut_send: str = "enter"
    delay_after_open: float = 1.2
    delay_after_paste: float = 0.3


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    cursor: CursorConfig = field(default_factory=CursorConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_FILE.exists():
            cfg = cls()
            cfg.save()
            return cfg
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(
                llm=LLMConfig(**data.get("llm", {})),
                whisper=WhisperConfig(**data.get("whisper", {})),
                cursor=CursorConfig(**data.get("cursor", {})),
                audio=AudioConfig(**data.get("audio", {})),
            )
        except Exception:
            return cls()
