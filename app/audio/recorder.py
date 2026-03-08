import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtCore import QObject, Signal


class AudioRecorder(QObject):
    """Cross-platform audio recorder using sounddevice."""

    recording_started = Signal()
    recording_stopped = Signal(str)  # emits path to WAV file
    level_updated = Signal(float)  # RMS level 0.0-1.0 for UI meter
    duration_updated = Signal(float)  # elapsed seconds
    error_occurred = Signal(str)

    def __init__(self, sample_rate=16000, channels=1, dtype="int16"):
        super().__init__()
        self._sample_rate = sample_rate
        self._channels = channels
        self._dtype = dtype
        self._is_recording = False
        self._chunks: list[np.ndarray] = []
        self._stream = None
        self._lock = threading.Lock()
        self._start_time = 0.0

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def elapsed(self) -> float:
        if not self._is_recording:
            return 0.0
        return time.time() - self._start_time

    def start(self):
        if self._is_recording:
            return
        self._chunks.clear()
        self._is_recording = True
        self._start_time = time.time()

        try:
            print(f"[recorder] start: rate={self._sample_rate} ch={self._channels} dtype={self._dtype}")
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=self._dtype,
                blocksize=int(self._sample_rate * 0.1),
                callback=self._audio_callback,
            )
            self._stream.start()
            print("[recorder] stream started OK")
            self.recording_started.emit()
        except Exception as e:
            print(f"[recorder] start EXCEPTION: {e}")
            self._is_recording = False
            self.error_occurred.emit(f"无法启动录音: {e}")

    def stop(self) -> str | None:
        if not self._is_recording:
            print("[recorder] stop called but not recording")
            return None
        self._is_recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if not self._chunks:
                print("[recorder] stop: no chunks recorded")
                self.error_occurred.emit("没有录到任何音频数据")
                return None
            audio_data = np.concatenate(self._chunks, axis=0)
            self._chunks.clear()

        dur = len(audio_data) / self._sample_rate
        print(f"[recorder] stop: {len(audio_data)} samples, {dur:.1f}s")
        wav_path = self._save_wav(audio_data)
        print(f"[recorder] saved: {wav_path}")
        self.recording_stopped.emit(wav_path)
        return wav_path

    def _audio_callback(self, indata: np.ndarray, frames, time_info, status):
        if status:
            pass  # drop status warnings silently
        with self._lock:
            self._chunks.append(indata.copy())

        rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2)) / 32768.0
        level = min(1.0, rms * 10)
        self.level_updated.emit(level)
        self.duration_updated.emit(time.time() - self._start_time)

    def _save_wav(self, audio_data: np.ndarray) -> str:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".wav", prefix="voice_cursor_", delete=False
        )
        tmp.close()
        sf.write(tmp.name, audio_data, self._sample_rate)
        return tmp.name
