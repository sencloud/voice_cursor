import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

BUNDLED_MODEL_SIZE = "medium"


def _get_project_root() -> Path:
    """Return the voice_cursor project root regardless of how the app is run."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def _get_bundled_model_path() -> Path | None:
    """Return path to bundled whisper-medium model if it exists locally."""
    model_dir = _get_project_root() / "resources" / f"whisper-{BUNDLED_MODEL_SIZE}"
    required_files = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
    if model_dir.is_dir() and all((model_dir / f).is_file() for f in required_files):
        return model_dir
    return None


class STTEngine(QObject):
    """Speech-to-text engine using faster-whisper (CTranslate2)."""

    transcription_done = Signal(str)
    progress_updated = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, model_size="medium", device="auto", language="zh"):
        super().__init__()
        self._model_size = model_size
        self._device = device
        self._language = language
        self._model = None

    def _resolve_model_path(self) -> str:
        """Decide what to pass to WhisperModel() as the model identifier.

        - If the requested size matches the bundled model AND the local files
          exist, return the local directory path (no download).
        - Otherwise return the model-size string so faster-whisper downloads
          from Hugging Face on demand.
        """
        if self._model_size == BUNDLED_MODEL_SIZE:
            local = _get_bundled_model_path()
            if local is not None:
                logger.info("Using bundled model at %s", local)
                return str(local)

        logger.info(
            "Bundled model not available for '%s', will download from HF",
            self._model_size,
        )
        return self._model_size

    def _ensure_model(self):
        if self._model is not None:
            return

        model_path = self._resolve_model_path()
        is_local = not model_path.isalpha()  # local paths are never pure alpha
        if is_local:
            self.progress_updated.emit(f"正在加载内置 Whisper {self._model_size} 模型...")
        else:
            self.progress_updated.emit(
                f"正在下载并加载 Whisper {self._model_size} 模型（首次需要下载）..."
            )

        try:
            from faster_whisper import WhisperModel

            compute_type = "float16" if self._device == "cuda" else "int8"
            device = self._device
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"

            self._model = WhisperModel(
                model_path,
                device=device,
                compute_type=compute_type,
                local_files_only=is_local,
            )
            self.progress_updated.emit("Whisper 模型加载完成")
        except Exception as e:
            self.error_occurred.emit(f"Whisper 模型加载失败: {e}")
            raise

    def update_config(self, model_size: str, device: str, language: str):
        needs_reload = (model_size != self._model_size or device != self._device)
        self._model_size = model_size
        self._device = device
        self._language = language
        if needs_reload:
            self._model = None

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text. Blocks until complete."""
        print(f"[stt] transcribe: {audio_path}")
        self._ensure_model()
        self.progress_updated.emit("正在转录语音...")

        try:
            print("[stt] calling model.transcribe...")
            segments, info = self._model.transcribe(
                audio_path,
                language=self._language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=300,
                ),
            )

            texts = []
            for segment in segments:
                texts.append(segment.text.strip())
                print(f"[stt]   segment: [{segment.start:.1f}-{segment.end:.1f}] {segment.text.strip()[:80]}")

            full_text = "\n".join(texts)
            if not full_text.strip():
                print("[stt] WARNING: no valid speech detected")
                self.error_occurred.emit("未识别到有效语音内容")
                return ""

            print(f"[stt] transcribe done: lang={info.language} prob={info.language_probability:.2f} "
                  f"dur={info.duration:.1f}s  text_len={len(full_text)}")
            logger.info(
                "Transcription complete: lang=%s prob=%.2f duration=%.1fs",
                info.language, info.language_probability, info.duration,
            )
            self.progress_updated.emit("语音转录完成")
            self.transcription_done.emit(full_text)
            return full_text

        except Exception as e:
            print(f"[stt] EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"语音转录失败: {e}")
            return ""
