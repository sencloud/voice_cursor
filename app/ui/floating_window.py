import math
import os
import threading

from PySide6.QtCore import Qt, QTimer, QRect, Signal, Slot
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QApplication, QTextEdit,
)

from app.config import AppConfig
from app.audio.recorder import AudioRecorder
from app.ai.stt_engine import STTEngine
from app.ai.llm_engine import LLMEngine
from app.cursor.driver import CursorDriver
from app.ui.styles import FLOATING_WINDOW_STYLE

SHADOW_PAD = 10
BG_COLOR = QColor(28, 30, 38)
BORDER_COLOR = QColor(50, 54, 68)
CORNER_RADIUS = 14


class LevelMeter(QWidget):
    """Thin audio level visualization bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)
        self._level = 0.0

    def set_level(self, level: float):
        self._level = max(0.0, min(1.0, level))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(42, 45, 56))
        painter.drawRoundedRect(0, 0, w, h, 1, 1)

        if self._level > 0.01:
            g = QLinearGradient(0, 0, w * self._level, 0)
            g.setColorAt(0, QColor(91, 156, 245))
            g.setColorAt(1, QColor(72, 176, 106))
            painter.setBrush(g)
            painter.drawRoundedRect(0, 0, int(w * self._level), h, 1, 1)

        painter.end()


class RecordButton(QPushButton):
    """Apple Voice Memos style record button.

    Idle: dark circle with red filled circle inside.
    Recording: dark circle with red rounded-square inside + pulsing ring.
    """

    BTN_SIZE = 52
    _recording = False
    _hover = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.BTN_SIZE, self.BTN_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self._phase = 0.0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick)

    def set_recording(self, on: bool):
        self._recording = on
        if on:
            self._phase = 0.0
            self._pulse_timer.start(40)
        else:
            self._pulse_timer.stop()
        self.setToolTip("停止录音" if on else "开始录音")
        self.update()

    def _tick(self):
        self._phase += 0.09
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.BTN_SIZE / 2, self.BTN_SIZE / 2
        outer_r = self.BTN_SIZE / 2 - 2

        if self._recording:
            ring_alpha = int(40 + 30 * math.sin(self._phase))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(224, 84, 84, ring_alpha))
            extra = 4 + 2 * abs(math.sin(self._phase))
            p.drawEllipse(
                int(cx - outer_r - extra), int(cy - outer_r - extra),
                int((outer_r + extra) * 2), int((outer_r + extra) * 2),
            )

        ring_color = QColor(70, 73, 86) if not self._hover else QColor(85, 88, 102)
        p.setPen(QPen(ring_color, 3))
        p.setBrush(QColor(34, 36, 46))
        p.drawEllipse(int(cx - outer_r), int(cy - outer_r),
                       int(outer_r * 2), int(outer_r * 2))

        RED = QColor(224, 74, 74) if not self._hover else QColor(236, 94, 94)

        if not self._recording:
            inner_r = outer_r * 0.6
            p.setPen(Qt.NoPen)
            p.setBrush(RED)
            p.drawEllipse(int(cx - inner_r), int(cy - inner_r),
                           int(inner_r * 2), int(inner_r * 2))
        else:
            half = outer_r * 0.32
            rect_r = 4
            p.setPen(Qt.NoPen)
            p.setBrush(RED)
            p.drawRoundedRect(
                int(cx - half), int(cy - half),
                int(half * 2), int(half * 2),
                rect_r, rect_r,
            )

        p.end()


def _paint_shadow_frame(painter: QPainter, rect: QRect):
    """Paint a soft shadow + filled rounded rect background."""
    for i in range(SHADOW_PAD, 0, -2):
        alpha = int(12 * (SHADOW_PAD - i) / SHADOW_PAD)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, alpha))
        r = rect.adjusted(i, i, -i, -i)
        painter.drawRoundedRect(r, CORNER_RADIUS + i // 2, CORNER_RADIUS + i // 2)

    inner = rect.adjusted(SHADOW_PAD, SHADOW_PAD, -SHADOW_PAD, -SHADOW_PAD)
    painter.setPen(QPen(BORDER_COLOR, 1))
    painter.setBrush(BG_COLOR)
    painter.drawRoundedRect(inner, CORNER_RADIUS, CORNER_RADIUS)


# ── Confirm Toast ──────────────────────────────────────────

CONFIRM_TOAST_STYLE = """
QLabel#toastTitle {
    color: #f0c050;
    font-size: 13px;
    font-weight: bold;
}
QLabel#toastHint {
    color: #8890a0;
    font-size: 11px;
}
QTextEdit#toastText {
    background-color: #22242e;
    border: 1px solid #2e3140;
    border-radius: 6px;
    color: #d0d4dc;
    font-size: 11px;
    padding: 6px;
    selection-background-color: #3d5a99;
}
QPushButton#toastSendBtn {
    background-color: #5b9cf5;
    border: none; border-radius: 6px;
    padding: 7px 18px; color: #fff; font-size: 11px; font-weight: bold;
}
QPushButton#toastSendBtn:hover { background-color: #6eaaf8; }
QPushButton#toastCancelBtn {
    background-color: #2e3140;
    border: none; border-radius: 6px;
    padding: 7px 18px; color: #b0b8c8; font-size: 11px;
}
QPushButton#toastCancelBtn:hover { background-color: #3a3e50; }
"""


class ConfirmToast(QWidget):
    """Popup shown when LLM result is too vague to auto-send."""

    confirmed = Signal(str)
    cancelled = Signal()

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420 + SHADOW_PAD * 2, 300 + SHADOW_PAD * 2)
        self._drag_pos = None
        self._setup_ui(text)

    def _setup_ui(self, text: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW_PAD + 14, SHADOW_PAD + 12,
                                 SHADOW_PAD + 14, SHADOW_PAD + 12)
        outer.setSpacing(8)

        title = QLabel("\u26A0  需求内容不够明确")
        title.setObjectName("toastTitle")
        outer.addWidget(title)

        hint = QLabel("AI 认为内容较模糊，已对语音原文进行润色。\n"
                       "确认无误后点击发送，或取消重新录制。")
        hint.setObjectName("toastHint")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("toastText")
        self._text_edit.setPlainText(text)
        outer.addWidget(self._text_edit, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("toastCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self._on_cancel)
        send_btn = QPushButton("仍然发送")
        send_btn.setObjectName("toastSendBtn")
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.clicked.connect(self._on_send)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(send_btn)
        outer.addLayout(btn_row)

        self.setStyleSheet(CONFIRM_TOAST_STYLE)

    def _on_send(self):
        self.confirmed.emit(self._text_edit.toPlainText().strip())
        self.close()

    def _on_cancel(self):
        self.cancelled.emit()
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        _paint_shadow_frame(painter, self.rect())
        painter.end()


# ── Main Floating Window ──────────────────────────────────

class FloatingWindow(QWidget):
    """Compact floating window with recording controls and status."""

    request_settings = Signal()
    _pipeline_error = Signal(str)
    _pipeline_finished = Signal()
    _pipeline_unclear = Signal(str)

    CONTENT_W, CONTENT_H = 290, 160
    WIN_W = CONTENT_W + SHADOW_PAD * 2
    WIN_H = CONTENT_H + SHADOW_PAD * 2

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config
        self._drag_pos = None

        self._recorder = AudioRecorder(
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
            dtype=config.audio.dtype,
        )
        self._stt = STTEngine(
            model_size=config.whisper.model_size,
            device=config.whisper.device,
            language=config.whisper.language,
        )
        self._llm = LLMEngine(
            provider=config.llm.provider,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            model=config.llm.model,
            vllm_base_url=config.llm.vllm_base_url,
            vllm_model=config.llm.vllm_model,
        )
        self._cursor_driver = CursorDriver(
            shortcut_open_chat=config.cursor.shortcut_open_chat,
            shortcut_paste=config.cursor.shortcut_paste,
            shortcut_send=config.cursor.shortcut_send,
            delay_after_open=config.cursor.delay_after_open,
            delay_after_paste=config.cursor.delay_after_paste,
        )

        self._is_processing = False
        self._setup_ui()
        self._connect_signals()

        self._pipeline_error.connect(self._handle_pipeline_error)
        self._pipeline_finished.connect(self._on_pipeline_done)
        self._pipeline_unclear.connect(self._show_confirm_toast)

        self._confirm_toast = None

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._update_timer_display)

    def _setup_ui(self):
        self.setObjectName("FloatingWindow")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.WIN_W, self.WIN_H)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.WIN_W - 20, 60)

        pad = SHADOW_PAD
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(pad + 16, pad + 10, pad + 16, pad + 12)
        main_layout.setSpacing(6)

        # ── title bar ──
        top = QHBoxLayout()
        top.setSpacing(4)
        self._title = QLabel("VOICE CURSOR")
        self._title.setObjectName("titleLabel")

        self._settings_btn = QPushButton("\u2699")
        self._settings_btn.setObjectName("settingsBtn")
        self._settings_btn.setFixedSize(24, 24)
        self._settings_btn.setCursor(Qt.PointingHandCursor)
        self._settings_btn.setToolTip("设置")

        self._close_btn = QPushButton("\u2715")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setCursor(Qt.PointingHandCursor)

        top.addWidget(self._title)
        top.addStretch()
        top.addWidget(self._settings_btn)
        top.addWidget(self._close_btn)
        main_layout.addLayout(top)

        # ── center: button + info ──
        center = QHBoxLayout()
        center.setSpacing(14)

        self._record_btn = RecordButton()
        self._record_btn.setToolTip("开始录音")

        info = QVBoxLayout()
        info.setSpacing(2)
        self._timer_label = QLabel("00:00")
        self._timer_label.setObjectName("timerLabel")
        self._status_label = QLabel("点击麦克风开始录音")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setWordWrap(True)
        info.addWidget(self._timer_label)
        info.addWidget(self._status_label)

        center.addWidget(self._record_btn)
        center.addLayout(info, 1)
        main_layout.addLayout(center, 1)

        # ── bottom: level meter + progress ──
        self._level_meter = LevelMeter()
        main_layout.addWidget(self._level_meter)

        self._progress = QProgressBar()
        self._progress.setObjectName("progressBar")
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.hide()
        main_layout.addWidget(self._progress)

        self.setStyleSheet(FLOATING_WINDOW_STYLE)

    # ── signals ──

    def _connect_signals(self):
        self._record_btn.clicked.connect(self._toggle_recording)
        self._settings_btn.clicked.connect(self.request_settings.emit)
        self._close_btn.clicked.connect(self._minimize_to_tray)

        self._recorder.level_updated.connect(self._level_meter.set_level)
        self._recorder.error_occurred.connect(self._show_error)

        self._stt.progress_updated.connect(self._update_status)
        self._stt.error_occurred.connect(self._show_error)

        self._llm.progress_updated.connect(self._update_status)
        self._llm.error_occurred.connect(self._show_error)

        self._cursor_driver.progress_updated.connect(self._update_status)
        self._cursor_driver.error_occurred.connect(self._show_error)

    # ── recording ──

    @Slot()
    def _toggle_recording(self):
        if self._is_processing:
            return
        if self._recorder.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        print("[ui] _start_recording")
        self._recorder.start()
        self._record_btn.set_recording(True)
        self._status_label.setText("正在录音...")
        self._tick_timer.start(200)

    def _stop_recording(self):
        print("[ui] _stop_recording")
        self._record_btn.set_recording(False)
        self._tick_timer.stop()
        self._level_meter.set_level(0)

        wav_path = self._recorder.stop()
        print(f"[ui]   wav_path={wav_path}")
        if not wav_path:
            print("[ui]   no wav_path, resetting")
            self._reset_ui()
            return

        self._is_processing = True
        self._record_btn.setEnabled(False)
        self._progress.show()
        self._status_label.setText("处理中...")

        print("[ui]   launching pipeline thread")
        threading.Thread(
            target=self._run_pipeline, args=(wav_path,), daemon=True
        ).start()

    # ── pipeline ──

    def _run_pipeline(self, wav_path: str):
        print(f"\n[pipeline] === START pipeline, wav={wav_path} ===")
        try:
            print("[pipeline] Step 1: STT transcribe...")
            raw_text = self._stt.transcribe(wav_path)
            print(f"[pipeline]   STT result: {len(raw_text) if raw_text else 0} chars")
            if raw_text:
                print(f"[pipeline]   STT text: {raw_text[:200]!r}")
            if not raw_text:
                print("[pipeline]   ERROR: empty STT result")
                self._pipeline_error.emit("语音转录结果为空")
                return

            print("[pipeline] Step 2: LLM organize...")
            result = self._llm.organize(raw_text)
            if result is None:
                print("[pipeline]   ERROR: LLM returned None")
                self._pipeline_error.emit("AI 需求整理结果为空")
                return
            print(f"[pipeline]   LLM organize: is_clear={result.is_clear}, {len(result.text)} chars")
            print(f"[pipeline]   LLM text: {result.text[:200]!r}")

            if not result.is_clear:
                print("[pipeline] Step 2b: LLM polish (unclear)...")
                polished = self._llm.polish(raw_text)
                print(f"[pipeline]   polished: {len(polished)} chars")
                print(f"[pipeline]   polished text: {polished[:200]!r}")
                print("[pipeline]   -> emitting _pipeline_unclear signal")
                self._pipeline_unclear.emit(polished)
                return

            print("[pipeline] Step 3: send to Cursor...")
            self._cursor_driver.send_to_cursor(result.text)
            print("[pipeline]   -> emitting _pipeline_finished signal")
            self._pipeline_finished.emit()
        except Exception as e:
            print(f"[pipeline] EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            self._pipeline_error.emit(str(e))
        finally:
            print(f"[pipeline] === END pipeline ===\n")
            try:
                os.unlink(wav_path)
            except OSError:
                pass

    @Slot(str)
    def _handle_pipeline_error(self, msg: str):
        print(f"[ui] pipeline ERROR: {msg}")
        self._show_error(msg)
        self._reset_ui()

    @Slot(str)
    def _show_confirm_toast(self, text: str):
        print(f"[ui] _show_confirm_toast ({len(text)} chars)")
        self._progress.hide()
        self._update_status("需求不明确，请确认...")

        toast = ConfirmToast(text, parent=None)
        pos = self.geometry().topLeft()
        toast.move(pos.x() - 60, pos.y() + self.height() + 4)
        toast.confirmed.connect(self._on_toast_confirmed)
        toast.cancelled.connect(self._on_toast_cancelled)
        toast.show()
        self._confirm_toast = toast

    @Slot(str)
    def _on_toast_confirmed(self, text: str):
        print(f"[ui] toast CONFIRMED ({len(text)} chars)")
        self._confirm_toast = None
        if not text.strip():
            self._show_error("发送内容为空")
            self._reset_ui()
            return
        self._progress.show()
        self._update_status("正在发送到 Cursor...")

        def _send():
            try:
                print("[ui] toast -> sending to Cursor")
                self._cursor_driver.send_to_cursor(text)
                self._pipeline_finished.emit()
            except Exception as e:
                print(f"[ui] toast send EXCEPTION: {e}")
                self._pipeline_error.emit(str(e))

        threading.Thread(target=_send, daemon=True).start()

    @Slot()
    def _on_toast_cancelled(self):
        print("[ui] toast CANCELLED")
        self._confirm_toast = None
        self._update_status("已取消，可重新录音")
        self._reset_ui()

    @Slot()
    def _on_pipeline_done(self):
        print("[ui] pipeline DONE -> sent to Cursor successfully")
        self._update_status("完成！需求已发送到 Cursor")
        QTimer.singleShot(3000, self._reset_ui)

    # ── UI helpers ──

    @Slot()
    def _reset_ui(self):
        self._is_processing = False
        self._record_btn.setEnabled(True)
        self._record_btn.set_recording(False)
        self._progress.hide()
        self._timer_label.setText("00:00")
        self._status_label.setText("点击麦克风开始录音")
        self._status_label.setStyleSheet("")

    @Slot(str)
    def _update_status(self, msg: str):
        self._status_label.setStyleSheet("")
        self._status_label.setText(msg)

    @Slot(str)
    def _show_error(self, msg: str):
        self._status_label.setText(msg)
        self._status_label.setStyleSheet("color: #e05454;")
        QTimer.singleShot(6000, lambda: self._status_label.setStyleSheet(""))

    @Slot()
    def _update_timer_display(self):
        elapsed = self._recorder.elapsed
        mins = int(elapsed) // 60
        secs = int(elapsed) % 60
        self._timer_label.setText(f"{mins:02d}:{secs:02d}")

    def _minimize_to_tray(self):
        self.hide()

    def reload_config(self, config: AppConfig):
        self._config = config
        self._stt.update_config(
            config.whisper.model_size, config.whisper.device, config.whisper.language
        )
        self._llm.update_config(
            config.llm.provider, config.llm.api_key, config.llm.base_url,
            config.llm.model, config.llm.vllm_base_url, config.llm.vllm_model,
        )
        self._cursor_driver.update_config(
            config.cursor.shortcut_open_chat, config.cursor.shortcut_paste,
            config.cursor.shortcut_send, config.cursor.delay_after_open,
            config.cursor.delay_after_paste,
        )

    # ── dragging ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ── painting ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        _paint_shadow_frame(painter, self.rect())
        painter.end()
