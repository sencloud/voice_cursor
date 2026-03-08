# Voice Cursor - 语音驱动 Cursor 开发工具

跨平台桌面悬浮窗工具：录制多人讨论语音 → 本地 Whisper 转文字 → Qwen 大模型整理需求 → 自动发送到 Cursor Agent Chat 驱动开发。

## 安装

```bash
pip install -r requirements.txt
```

首次运行需要先配置Qwen API Key，会自动下载 Whisper 模型（medium 约 1.5GB）。

## 运行

```bash
python main.py
```

## 配置

点击悬浮窗齿轮按钮打开设置：

- **LLM 配置**：支持阿里 Qwen API（dashscope）和本地 vllm
- **Whisper 模型**：可选 tiny/base/small/medium/large-v3
- **Cursor 快捷键**：自定义驱动 Cursor 的键盘快捷键

配置文件保存在 `~/.voice_cursor/config.json`。

## 使用流程

1. 点击麦克风按钮开始录音
2. 多人自由讨论需求
3. 点击停止按钮结束录音
4. 工具自动完成：语音转文字 → AI 需求整理 → 发送到 Cursor
