"""
Open-LLM-VTuber 启动器 v2.6
- 自动发现项目根目录
- 读取/保存 conf.yaml
- 切换默认角色 / 语言模型 / TTS 模型
- 右侧参数面板跟随左侧选择动态切换：
    · 选中 ollama_llm  → 显示专用参数面板 + 模型信息
    · 选中其他 LLM     → 显示该 provider 的通用参数编辑器
    · 选中 gpt_sovits_tts → 显示 GPT-SoVITS 面板
    · 选中其他 TTS      → 显示该 TTS 后端的通用参数编辑器
- Ollama 模型列表 + 模型信息 + GPU 状态
- 配置预设 / 角色头像卡片
- GPT-SoVITS 声音模型切换
- 启动 / 停止 / 一键启动 / 一键停止
- 关闭窗口安全检查 + 窗口强制前置

标签页顺序：服务 → 模型 → 角色 → LLM → TTS → ASR / VAD

v2.6 新增：
- 角色下拉决定 Web UI 默认角色：写入 system_config.default_character 指针，
  由后端启动时 merge（不再把角色内容写进 conf.yaml，避免切换角色累积残留）
- 角色下拉首项「（使用 conf.yaml 基础配置）」= 不指定默认角色
- 角色编辑器新增「语言」下拉（纯选择，不可手写），驱动 LLM 回答语言与 TTS 语音语言
- 应用声音时若声音语言与角色语言不一致，提示同步

v2.5：
- 角色标识改用 conf_uid；删除 conf_name；角色名统一为 character_name
- 启动器与 Web UI 显示同一个 character_name（Web UI 只能显示该字段，故以此统一）
- 角色编辑器「内部标识」只剩 conf_uid；新建角色模板同步

v2.4：
- 「形象」分组加「📂 打开保存目录」与「导入...」按钮
- 导入 Live2D 模型：支持单个文件夹、包含多模型的总目录、多选 zip 压缩包；
  自动查找入口文件（.model3.json 优先取最浅层）并写入 model_dict.json（自动备份）
- 导入时拒绝 Cubism 2.1（.model.json）模型，因前端只支持 .model3.json
- Live2D 预览下方提示模型格式兼容性（✔ Cubism 3/4 / ⚠ Cubism 2.1 不支持）

v2.3：
- 移除 Live2D 模型管理模块（下拉已自动列出 model_dict.json ∪ live2d-models/ 全部模型）
- TTS 显示「当前使用」的声音（由 conf.yaml 的 ref_audio_path 反查）
- 启动完成后自动用默认浏览器打开 http://localhost:12393（可关闭，也可手动点击打开）

v2.2：
- 参考音频试听（winsound 播 WAV，其他格式交给系统播放器）
- GPT/SoVITS 权重选择移入「新建/编辑声音」对话框；声音模型支持增删改查，即 TTS 预设
- Live2D 并入「角色」页（左列：角色列表/头像 → Live2D 预览）
- 贴图预览修复：排除 images/ 等 UI 目录，支持 Cubism 2.1 的 zip 内贴图
- 模型目录定位带回退（'shizuku-local' → live2d-models/shizuku）

v2.1：
- Live2D 独立标签页（放在「角色」之后）+ 模型贴图静态预览
- 角色编辑器字段分组（显示信息 / 形象 / 人设 / 内部标识），头像支持「导入...」
- GPT-SoVITS 权重扫描全部 GPT_weights* / SoVITS_weights* 目录，带版本标签与跨版本警告
- voices/ 声音模型体系：权重对 + 参考音频一一对应，「应用声音」一键写配置并切权重

v2.0：
- 「预设」标签页改名「模型」并移到「服务」之后
- 「模型」页新增 Live2D 模型管理（model_dict.json 浏览 / 扫描补录 / 删除 / 保存）
- 角色编辑器中 Live2D 模型、头像改为下拉选择（自动扫描，无需手填）

v1.9：
- 角色配置编辑器（新建 / 编辑 / 删除角色 YAML）
- ASR 参数面板（动态切换引擎 + 专用参数）
- VAD 参数面板（silero_vad 参数）
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from typing import NamedTuple

try:
    import winsound
except ImportError:  # 非 Windows 平台
    winsound = None

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QTextEdit, QFormLayout,
    QGroupBox, QMessageBox, QFileDialog, QLineEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QInputDialog, QListWidget,
    QListWidgetItem, QSplitter, QScrollArea, QSizePolicy,
    QDialog, QDialogButtonBox, QPlainTextEdit, QTabWidget
)

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import SingleQuotedScalarString


# ----------------------------------------------------------------------
# 常量
# ----------------------------------------------------------------------

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_API_TAGS = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags"
OLLAMA_API_SHOW = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/show"
OLLAMA_API_GENERATE = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
GPT_SOVITS_HOST = "127.0.0.1"
GPT_SOVITS_PORT = 9880
GPT_SOVITS_BASE = f"http://{GPT_SOVITS_HOST}:{GPT_SOVITS_PORT}"
LLM_HOST = "127.0.0.1"
LLM_PORT = 12393
WEB_UI_URL = f"http://localhost:{LLM_PORT}"

DEFAULT_GPT_BAT = "start_v4_dpo.bat"
OLLAMA_PROVIDER_KEY = "ollama_llm"
GPT_SOVITS_TTS_KEY = "gpt_sovits_tts"

GPT_WEIGHTS_PREFIX = "GPT_weights"
SOVITS_WEIGHTS_PREFIX = "SoVITS_weights"
# API 以 v4 DPO 启动（start_v4_dpo.py），应用非 v4 权重时给出警告
CURRENT_GSV_VERSION_DIR = "GPT_weights_v4"

AVATAR_DIR_CANDIDATES = ["avatars", "avatar"]

ASR_ENGINE_KEY = "asr_model"
ASR_ENGINES = [
    "faster_whisper", "whisper_cpp", "whisper", "fun_asr",
    "azure_asr", "groq_whisper_asr", "sherpa_onnx_asr"
]

VAD_ENGINE_KEY = "vad_model"
VAD_ENGINES = [None, "silero_vad"]

# 角色回答语言：显示名 -> 后端白名单取值（见 CharacterConfig.check_language）
LANGUAGE_CHOICES = [
    ("（不限制）", ""),
    ("中文", "zh"),
    ("日本語", "ja"),
    ("English", "en"),
    ("한국어", "ko"),
    ("粤语", "yue"),
    ("自动检测", "auto"),
]
LANGUAGE_CODE_TO_LABEL = {code: label for label, code in LANGUAGE_CHOICES}
# 后端语言代码 -> 该语言自称，用于提示文案
LANGUAGE_NATIVE_NAMES = {
    "zh": "中文", "ja": "日本語", "en": "English",
    "ko": "한국어", "yue": "粤语",
}

# 角色下拉框首项：不指定默认角色，直接用 conf.yaml 自身的 character_config
BASE_CONFIG_ENTRY = "（使用 conf.yaml 基础配置）"


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------

def find_project_root(start: Path):
    for p in [start] + list(start.parents):
        if (p / "conf.yaml").exists() and (p / "run_server.py").exists():
            return p
    return None


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def query_ollama_models(timeout: float = 3.0):
    try:
        with urllib.request.urlopen(OLLAMA_API_TAGS, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        return sorted([m.get("name", "") for m in data.get("models", []) if m.get("name")])
    except Exception:
        return None


def query_ollama_show(model_name: str, timeout: float = 4.0):
    try:
        req = urllib.request.Request(
            OLLAMA_API_SHOW,
            data=json.dumps({"model": model_name}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def unload_ollama_model(model_name: str, timeout: float = 20.0):
    """卸载 Ollama 中驻留的模型。返回 (是否成功, 说明)。

    用 Ollama 官方做法：POST /api/generate，prompt 为空且 keep_alive=0。
    与后端 ollama_llm.cleanup() 用的是同一接口，行为一致。
    内部吞掉所有异常，调用方不需要 try。
    """
    if not model_name:
        return False, "模型名为空，跳过"
    if not is_port_open(OLLAMA_HOST, OLLAMA_PORT):
        return False, "Ollama 未运行，跳过"
    try:
        req = urllib.request.Request(
            OLLAMA_API_GENERATE,
            data=json.dumps(
                {
                    "model": model_name,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": 0,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, f"HTTP {r.status}"
    except Exception as e:
        return False, str(e)


def format_size_bytes(n):
    try:
        n = float(n)
    except Exception:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"


def query_gpu_info() -> str:
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        result = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            return "N/A"
        out = result.stdout.strip()
        if not out:
            return "N/A"
        line = out.splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            return "N/A"
        mem_used, mem_total, util, temp = parts[:4]
        try:
            mu = int(mem_used)
            mt = int(mem_total)
            pct = int(round(mu * 100 / mt)) if mt > 0 else 0
        except Exception:
            return "N/A"
        return f"GPU: {mu}/{mt} MiB ({pct}%)  |  Util {util}%  |  {temp}°C"
    except Exception:
        return "N/A"


def discover_weight_dirs(root: Path, prefix: str):
    """发现 root 下所有权重目录（如 GPT_weights / GPT_weights_v2 / v4 ...）。"""
    if not root:
        return []
    dirs = [d for d in root.iterdir() if d.is_dir() and d.name.startswith(prefix)]
    # 空（无后缀）目录排最前，其余按版本名排序
    dirs.sort(key=lambda d: (d.name == prefix, d.name))
    return dirs


def list_weight_files(root: Path, prefix: str, suffix: str):
    """扫描所有版本目录，返回 '文件名 [目录名]' 形式的列表。"""
    if not root:
        return []
    entries = []
    for d in discover_weight_dirs(root, prefix):
        for f in sorted(d.glob(f"*{suffix}")):
            if f.is_file():
                entries.append(f"{f.name}  [{d.name}]")
    return entries


def split_weight_text(text: str):
    """把 '文件名  [目录名]' 拆回 (文件名, 目录名)。"""
    m = re.match(r"^(.*?)\s+\[(.+)\]$", text.strip())
    if m:
        return m.group(1), m.group(2)
    return text.strip(), None


def find_weight_path(root: Path, prefix: str, weight_text: str):
    """根据权重标识定位文件实际路径。

    支持两种写法：
      · 显示式：'xxx.ckpt  [GPT_weights_v4]'
      · 路径式：'GPT_weights_v4/xxx.ckpt'（voices/voice.json 里手写的形式）
    """
    if not root or not weight_text:
        return None
    weight_text = weight_text.strip()
    # 路径式：相对于 GPT-SoVITS 根目录
    if "/" in weight_text or "\\" in weight_text:
        p = root / weight_text.replace("\\", "/")
        if p.exists():
            return p
    filename, subdir = split_weight_text(weight_text)
    if not filename:
        return None
    if subdir:
        p = root / subdir / filename
        if p.exists():
            return p
    for d in discover_weight_dirs(root, prefix):
        p = d / filename
        if p.exists():
            return p
    return None


def gpt_sovits_set_weights(endpoint: str, weights_path: Path, timeout: float = 15.0):
    try:
        params = urllib.parse.urlencode({"weights_path": str(weights_path)})
        url = f"{GPT_SOVITS_BASE}/{endpoint}?{params}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status == 200, body
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(e)
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def play_audio(path: Path):
    """试听音频。返回 (是否成功, 说明)。

    PySide6-Essentials 不含 QtMultimedia 二进制，所以用标准库：
    WAV 走 winsound 异步播放，其他格式交给系统默认播放器。
    """
    if not path or not Path(path).exists():
        return False, "文件不存在"
    suffix = Path(path).suffix.lower()
    if winsound is not None and suffix == ".wav":
        try:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True, "正在播放"
        except Exception as e:
            return False, f"播放失败：{e}"
    # 非 WAV 或非 Windows：交给系统默认播放器
    try:
        os.startfile(str(path))
        return True, "已交给系统播放器打开"
    except AttributeError:
        return False, "当前平台不支持直接播放，请手动打开该文件"
    except Exception as e:
        return False, f"打开失败：{e}"


def stop_audio():
    """停止 winsound 正在播放的音频。"""
    if winsound is None:
        return
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass


def _safe_extract(zf: zipfile.ZipFile, target: Path):
    """解压 zip 到 target，拒绝越出目标目录的条目（zip slip 防护）。"""
    base = target.resolve()
    for member in zf.infolist():
        dest = (target / member.filename).resolve()
        if not str(dest).startswith(str(base)):
            raise ValueError(f"压缩包内含非法路径：{member.filename}")
    zf.extractall(target)


def clear_layout(layout):
    """递归清空 layout 中的所有控件和子布局"""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.deleteLater()
        child = item.layout()
        if child is not None:
            clear_layout(child)


def coerce_back(original, text: str):
    """把编辑框里的字符串转回原始类型"""
    if isinstance(original, bool):
        # 不走这里，bool 用 checkbox
        return bool(text)
    if isinstance(original, int) and not isinstance(original, bool):
        try:
            return int(text)
        except Exception:
            return original
    if isinstance(original, float):
        try:
            return float(text)
        except Exception:
            return original
    if original is None:
        return None if text == "" else text
    return text


# ----------------------------------------------------------------------
# 主窗口
# ----------------------------------------------------------------------

class CharEntry(NamedTuple):
    """角色列表中的一项。"""
    display: str    # 下拉框显示文本："{角色名} ({文件名})"
    stem: str       # 角色 YAML 的文件名（不含扩展名）
    name: str       # character_name —— 与 Web UI 显示的一致
    avatar: str     # 头像文件名
    uid: str        # conf_uid —— 唯一标识，聊天记录按它分目录


class CodeCombo(QComboBox):
    """固定选项下拉框：界面显示友好名称，text()/setText() 读写的是「代码」值。

    这样它就能和 QLineEdit 走同一套读写逻辑（见 char_edit_fields 的遍历），
    同时保证用户只能从下拉里选择、无法手写。
    """

    def __init__(self, choices, parent=None):
        """choices: [(显示名, 代码值), ...]"""
        super().__init__(parent)
        for label, code in choices:
            self.addItem(label, code)

    def text(self) -> str:
        data = self.currentData()
        return "" if data is None else str(data)

    def setText(self, value: str):
        value = "" if value is None else str(value).strip()
        idx = self.findData(value)
        self.setCurrentIndex(idx if idx >= 0 else 0)


class EditableCombo(QComboBox):
    """可编辑下拉框，提供 QLineEdit 风格的 text()/setText() 接口，
    使角色编辑器中下拉字段与普通输入框走同一套读写逻辑。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)

    def text(self) -> str:
        return self.currentText()

    def setText(self, value: str):
        value = "" if value is None else str(value)
        idx = self.findText(value)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setEditText(value)


def _copy_in_ref(src_path: str, target_dir: Path):
    """把参考音频复制为 target_dir/ref.<ext>。"""
    src = Path(src_path)
    if src.resolve().parent == target_dir.resolve():
        return  # 已在目标目录（编辑时未更换音频）
    ext = src.suffix or ".wav"
    target = target_dir / f"ref{ext}"
    shutil.copy2(src, target)
    # 换过格式时清掉旧的 ref.*
    for old in target_dir.glob("ref.*"):
        if old.resolve() != target.resolve():
            old.unlink(missing_ok=True)


def _write_voice_json(target_dir: Path, data: dict):
    meta = {
        "prompt_text": data["prompt_text"],
        "prompt_lang": data["prompt_lang"],
        "text_lang": data["text_lang"],
        "gpt_weight": data["gpt_weight"],
        "sovits_weight": data["sovits_weight"],
    }
    (target_dir / "voice.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class VoiceDialog(QDialog):
    """新建 / 编辑声音模型：权重对 + 参考音频 + 提示文本。"""

    def __init__(self, parent, gpt_items: list, sovits_items: list, initial: dict = None):
        super().__init__(parent)
        self._editing = initial is not None
        self.setWindowTitle("编辑声音模型" if self._editing else "新建声音模型")
        self.resize(660, 400)

        form = QFormLayout(self)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("如 加藤惠（将作为 voices/ 下的文件夹名）")
        form.addRow("名称：", self.edit_name)

        self.combo_gpt = QComboBox()
        self.combo_gpt.addItems(gpt_items)
        form.addRow("GPT 权重(.ckpt)：", self.combo_gpt)

        self.combo_sovits = QComboBox()
        self.combo_sovits.addItems(sovits_items)
        form.addRow("SoVITS 权重(.pth)：", self.combo_sovits)

        audio_row = QHBoxLayout()
        self.edit_audio = QLineEdit()
        self.edit_audio.setPlaceholderText("参考音频文件路径")
        btn_pick = QPushButton("选择...")
        btn_pick.clicked.connect(self._pick_audio)
        btn_play = QPushButton("▶ 试听")
        btn_play.setToolTip("播放当前选择的参考音频")
        btn_play.clicked.connect(self._audition)
        audio_row.addWidget(self.edit_audio, stretch=1)
        audio_row.addWidget(btn_pick)
        audio_row.addWidget(btn_play)
        form.addRow("参考音频：", audio_row)

        self.edit_prompt = QPlainTextEdit()
        self.edit_prompt.setPlaceholderText("参考音频中说的原话（GPT-SoVITS 需要它来对齐音色）")
        self.edit_prompt.setMaximumHeight(90)
        form.addRow("参考文本：", self.edit_prompt)

        self.combo_prompt_lang = QComboBox()
        self.combo_prompt_lang.addItems(["zh", "ja", "en", "ko", "yue", "auto"])
        self.combo_text_lang = QComboBox()
        self.combo_text_lang.addItems(["zh", "ja", "en", "ko", "yue", "auto"])
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("参考音频语言:"))
        lang_row.addWidget(self.combo_prompt_lang)
        lang_row.addSpacing(20)
        lang_row.addWidget(QLabel("合成语言:"))
        lang_row.addWidget(self.combo_text_lang)
        lang_row.addStretch(1)
        form.addRow("语言：", lang_row)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

        if initial:
            self._apply_initial(initial)

    def _apply_initial(self, initial: dict):
        """编辑模式：把已有 voice.json 填进控件。"""
        self.edit_name.setText(initial.get("name", ""))
        self.edit_audio.setText(initial.get("ref_audio", ""))
        self.edit_prompt.setPlainText(initial.get("prompt_text", ""))
        for combo, key, default in (
            (self.combo_prompt_lang, "prompt_lang", "ja"),
            (self.combo_text_lang, "text_lang", "ja"),
        ):
            idx = combo.findText(initial.get(key, default))
            if idx >= 0:
                combo.setCurrentIndex(idx)
        for combo, key in (
            (self.combo_gpt, "gpt_weight"),
            (self.combo_sovits, "sovits_weight"),
        ):
            value = initial.get(key, "")
            idx = LauncherWindow._item_index(
                [combo.itemText(i) for i in range(combo.count())], value
            )
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _pick_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择参考音频", "",
            "音频文件 (*.wav *.mp3 *.flac *.ogg *.m4a);;所有文件 (*)"
        )
        if path:
            self.edit_audio.setText(path)

    def _audition(self):
        stop_audio()
        path = self.edit_audio.text().strip()
        if not path:
            QMessageBox.warning(self, "未选择音频", "请先选择参考音频文件。")
            return
        ok, msg = play_audio(Path(path))
        if not ok:
            QMessageBox.warning(self, "试听失败", msg)

    def _on_ok(self):
        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "缺少名称", "请填写声音模型名称。")
            return
        if not self.edit_audio.text().strip():
            QMessageBox.warning(self, "缺少参考音频", "请选择参考音频文件。")
            return
        if not Path(self.edit_audio.text().strip()).exists():
            QMessageBox.warning(self, "文件不存在", "参考音频文件不存在。")
            return
        if not self.edit_prompt.toPlainText().strip():
            reply = QMessageBox.question(
                self, "参考文本为空",
                "参考文本为空会导致音色对齐效果变差，仍要继续吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.accept()

    def result_data(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "gpt_weight": self.combo_gpt.currentText().strip(),
            "sovits_weight": self.combo_sovits.currentText().strip(),
            "ref_audio": self.edit_audio.text().strip(),
            "prompt_text": self.edit_prompt.toPlainText().strip(),
            "prompt_lang": self.combo_prompt_lang.currentText(),
            "text_lang": self.combo_text_lang.currentText(),
        }


class LauncherWindow(QMainWindow):
    log_signal = Signal(str)
    llm_finished_signal = Signal(int)
    gsv_finished_signal = Signal(int)
    status_signal = Signal(bool, bool, bool)
    gpu_signal = Signal(str)
    model_info_signal = Signal(str)
    oneclick_progress_signal = Signal(str)
    oneclick_done_signal = Signal()
    web_ready_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Open-LLM-VTuber 启动器 v2.6")
        self.resize(1220, 980)

        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

        self.project_root = None
        self.config = None
        self.launcher_cfg = {}

        self.llm_process = None
        self.gsv_process = None
        self._llm_reader_thread = None
        self._gsv_reader_thread = None

        self._character_entries = []
        self._loading_config = False

        # 通用编辑器状态
        #   {key: widget}  widget 是 QLineEdit 或 QCheckBox
        self._generic_llm_editors = {}
        self._generic_tts_editors = {}
        self._generic_asr_editors = {}
        self._generic_vad_editors = {}
        # 记录原始值，用于类型转换
        self._generic_llm_originals = {}
        self._generic_tts_originals = {}
        self._generic_asr_originals = {}
        self._generic_vad_originals = {}

        self.log_signal.connect(self._log)
        self.llm_finished_signal.connect(self._on_llm_finished)
        self.gsv_finished_signal.connect(self._on_gsv_finished)
        self.status_signal.connect(self._on_status_update)
        self.gpu_signal.connect(self._on_gpu_update)
        self.model_info_signal.connect(self._on_model_info_update)
        self.oneclick_progress_signal.connect(self._log)
        self.oneclick_done_signal.connect(self._on_oneclick_done)
        self.web_ready_signal.connect(self._on_web_ready)

        # 避免重复打开浏览器的令牌（每次启动递增，旧轮询线程据此失效）
        self._web_open_token = 0

        self._build_ui()
        self._discover_and_load()

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(2000)
        self._status_timer.timeout.connect(self._poll_status)
        self._status_timer.start()

        QTimer.singleShot(500, self._auto_refresh_models_if_online)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(6, 6, 6, 6)

        # ── 顶部状态条（始终可见）──
        status_bar = QHBoxLayout()
        self.lbl_ollama = QLabel("● Ollama")
        self.lbl_gsv = QLabel("● GPT-SoVITS")
        self.lbl_llm = QLabel("● Open-LLM-VTuber")
        for lbl in (self.lbl_ollama, self.lbl_gsv, self.lbl_llm):
            lbl.setStyleSheet("color: gray; font-weight: bold;")
            status_bar.addWidget(lbl)
        status_bar.addStretch(1)
        self.lbl_gpu = QLabel("GPU: N/A")
        self.lbl_gpu.setStyleSheet("color: #555; font-weight: bold;")
        status_bar.addWidget(self.lbl_gpu)
        root_layout.addLayout(status_bar)

        # ── 项目目录（始终可见）──
        path_row = QHBoxLayout()
        self.path_label = QLabel("（未发现项目目录）")
        self.path_label.setWordWrap(True)
        btn_pick = QPushButton("选择项目目录...")
        btn_pick.clicked.connect(self._pick_project)
        path_row.addWidget(self.path_label, stretch=1)
        path_row.addWidget(btn_pick)
        root_layout.addLayout(path_row)

        # ══════════════════════════════════════════════════════════════
        # QTabWidget：6 个标签页（服务 → 模型 → 角色 → LLM → TTS → ASR/VAD）
        # ══════════════════════════════════════════════════════════════
        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, stretch=1)

        # ── Tab 1: 服务 ──
        tab_service = QWidget()
        tab_service_layout = QVBoxLayout(tab_service)

        svc_btn_row = QHBoxLayout()
        self.btn_oneclick = QPushButton("★ 一键启动全部")
        self.btn_start_llm = QPushButton("启动 Open-LLM-VTuber")
        self.btn_stop_llm = QPushButton("停止 Open-LLM-VTuber")
        self.btn_stop_all = QPushButton("■ 全部停止")
        self.btn_stop_llm.setEnabled(False)
        self.btn_oneclick.clicked.connect(self._oneclick_start)
        self.btn_start_llm.clicked.connect(self._start_llm)
        self.btn_stop_llm.clicked.connect(self._stop_llm)
        self.btn_stop_all.clicked.connect(self._stop_all)
        svc_btn_row.addWidget(self.btn_oneclick)
        svc_btn_row.addWidget(self.btn_start_llm)
        svc_btn_row.addWidget(self.btn_stop_llm)
        svc_btn_row.addWidget(self.btn_stop_all)
        tab_service_layout.addLayout(svc_btn_row)

        # 启动完成后的行为
        svc_opt_row = QHBoxLayout()
        self.chk_open_browser = QCheckBox("启动完成后自动打开浏览器")
        self.chk_open_browser.setToolTip(f"服务就绪后自动访问 {WEB_UI_URL}")
        self.chk_open_browser.setChecked(True)
        self.chk_open_browser.toggled.connect(self._on_open_browser_toggled)
        self.btn_open_browser = QPushButton("立即打开界面")
        self.btn_open_browser.clicked.connect(self._open_web_ui)
        svc_opt_row.addWidget(self.chk_open_browser)
        svc_opt_row.addWidget(self.btn_open_browser)
        svc_opt_row.addStretch(1)
        tab_service_layout.addLayout(svc_opt_row)

        log_box = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_view)
        tab_service_layout.addWidget(log_box)

        self.tabs.addTab(tab_service, "服务")

        # ── Tab 2: 模型（原「预设」，放在服务之后）──
        tab_preset = QWidget()
        tab_preset_layout = QVBoxLayout(tab_preset)

        # 模型选择区
        sel_box = QGroupBox("模型选择")
        sel_form = QFormLayout(sel_box)
        self.combo_llm = QComboBox()
        self.combo_tts = QComboBox()
        self.combo_asr_model = QComboBox()
        self.combo_asr_model.addItems(["（禁用）"] + ASR_ENGINES)
        self.combo_vad_model = QComboBox()
        self.combo_vad_model.addItems(["（禁用）", "silero_vad"])
        sel_form.addRow("语言模型：", self.combo_llm)
        sel_form.addRow("TTS 模型：", self.combo_tts)
        sel_form.addRow("ASR 引擎：", self.combo_asr_model)
        sel_form.addRow("VAD 引擎：", self.combo_vad_model)
        # 改了模型选择后需要点这里才写入 conf.yaml（下面预设区的「载入到界面」只改界面）
        sel_btn_row = QHBoxLayout()
        sel_btn_row.addStretch(1)
        btn_apply_models = QPushButton("应用并保存")
        btn_apply_models.setToolTip("把以上模型选择立即写入 conf.yaml（不含此处未列出的其他参数）")
        btn_apply_models.clicked.connect(self._save_config)
        sel_btn_row.addWidget(btn_apply_models)
        sel_form.addRow("", sel_btn_row)
        tab_preset_layout.addWidget(sel_box)

        # 预设区
        preset_box = QGroupBox("配置预设")
        preset_inner = QVBoxLayout(preset_box)
        self.preset_list = QListWidget()
        self.preset_list.itemDoubleClicked.connect(self._apply_preset)
        preset_inner.addWidget(self.preset_list)
        preset_btn_row = QHBoxLayout()
        btn_save_preset = QPushButton("保存当前为预设")
        # 「载入到界面」只把预设填进界面控件，不写 conf.yaml。
        # 写盘请用上面的「应用并保存」或底部的「保存配置」。
        btn_load_preset = QPushButton("载入到界面")
        btn_load_preset.setToolTip("把选中的预设填入界面（不会写入 conf.yaml）")
        btn_delete_preset = QPushButton("删除")
        btn_save_preset.clicked.connect(self._save_preset)
        btn_load_preset.clicked.connect(
            lambda: self._apply_preset(self.preset_list.currentItem())
        )
        btn_delete_preset.clicked.connect(self._delete_preset)
        preset_btn_row.addWidget(btn_save_preset)
        preset_btn_row.addWidget(btn_load_preset)
        preset_btn_row.addWidget(btn_delete_preset)
        preset_inner.addLayout(preset_btn_row)
        tab_preset_layout.addWidget(preset_box)

        tab_preset_layout.addStretch(1)

        self.tabs.addTab(tab_preset, "模型")

        # ── Tab 3: 角色 ──
        tab_char = QWidget()
        tab_char_layout = QHBoxLayout(tab_char)

        # 左：角色列表 + 头像 + Live2D 预览 + Live2D 模型管理
        char_left = QVBoxLayout()

        char_list_box = QGroupBox("角色列表")
        char_list_layout = QVBoxLayout(char_list_box)

        self.combo_character = QComboBox()
        self.combo_character.currentIndexChanged.connect(self._on_character_changed)
        char_list_layout.addWidget(self.combo_character)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(96, 96)
        self.avatar_label.setStyleSheet("border: 1px solid #ccc; background: #fafafa;")
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setText("无头像")
        char_list_layout.addWidget(self.avatar_label, alignment=Qt.AlignCenter)

        char_btn_row = QHBoxLayout()
        btn_new_char = QPushButton("新建")
        btn_del_char = QPushButton("删除")
        btn_new_char.clicked.connect(self._new_character)
        btn_del_char.clicked.connect(self._delete_character)
        char_btn_row.addWidget(btn_new_char)
        char_btn_row.addWidget(btn_del_char)
        char_list_layout.addLayout(char_btn_row)

        char_left.addWidget(char_list_box)

        # Live2D 预览（跟随所选角色自动刷新）
        preview_box = QGroupBox("Live2D 预览")
        preview_layout = QVBoxLayout(preview_box)
        self.l2d_preview = QLabel("（未选择模型）")
        self.l2d_preview.setFixedSize(210, 210)
        self.l2d_preview.setAlignment(Qt.AlignCenter)
        self.l2d_preview.setStyleSheet("border: 1px solid #ccc; background: #fafafa;")
        preview_layout.addWidget(self.l2d_preview, alignment=Qt.AlignCenter)
        self.l2d_preview_tip = QLabel("模型贴图静态预览，实际动画以前端为准")
        self.l2d_preview_tip.setStyleSheet("color: #888; font-size: 11px;")
        self.l2d_preview_tip.setAlignment(Qt.AlignCenter)
        self.l2d_preview_tip.setWordWrap(True)
        preview_layout.addWidget(self.l2d_preview_tip)
        char_left.addWidget(preview_box)

        char_left.addStretch(1)
        tab_char_layout.addLayout(char_left, stretch=1)

        # 右：角色编辑器（内嵌，不需要弹窗）
        char_edit_scroll = QScrollArea()
        char_edit_scroll.setWidgetResizable(True)
        char_edit_scroll.setFrameShape(QScrollArea.NoFrame)
        char_edit_inner = QWidget()
        char_edit_vbox = QVBoxLayout(char_edit_inner)

        self.char_edit_fields = {}

        # ── 显示信息 ──
        info_box = QGroupBox("显示信息")
        info_form = QFormLayout(info_box)
        for key, label, tip in [
            ("character_name", "角色名", "界面（含 Web UI 角色列表）显示的名字，需保持唯一。\n留空保存时会用 conf_uid 兜底"),
            ("human_name", "对用户的称呼", "角色对话时对你的称呼。留空表示不作要求"),
        ]:
            w = QLineEdit()
            w.setMinimumWidth(200)
            w.setToolTip(tip)
            info_form.addRow(f"{label}：", w)
            self.char_edit_fields[key] = w

        # 语言：纯下拉，不接受手写（后端同样只放行白名单取值）
        w_lang = CodeCombo(LANGUAGE_CHOICES)
        w_lang.setToolTip(
            "该角色的回答语言：无论用户说什么语言都只用该语言回答，TTS 也按该语言合成。\n"
            "留空或选「自动」表示不限制。"
        )
        info_form.addRow("语言：", w_lang)
        self.char_edit_fields["language"] = w_lang
        char_edit_vbox.addWidget(info_box)

        # ── 形象 ──（头像在 Live2D 模型上方）
        look_box = QGroupBox("形象")
        look_form = QFormLayout(look_box)

        # 头像：下拉 + 刷新 + 导入
        w_avatar = EditableCombo()
        w_avatar.setToolTip("从 avatars/ 目录自动扫描，或点「导入」添加图片。留空表示不使用头像")
        row_avatar = QHBoxLayout()
        row_avatar.addWidget(w_avatar, stretch=1)
        btn_refresh_avatar = QPushButton("↻")
        btn_refresh_avatar.setFixedWidth(32)
        btn_refresh_avatar.setToolTip("刷新头像列表")
        btn_refresh_avatar.clicked.connect(self._populate_avatar_combo)
        btn_import_avatar = QPushButton("导入...")
        btn_import_avatar.setToolTip("从本地选择图片并复制到 avatars/ 目录")
        btn_import_avatar.clicked.connect(self._import_avatar)
        row_avatar.addWidget(btn_refresh_avatar)
        row_avatar.addWidget(btn_import_avatar)
        look_form.addRow("头像：", row_avatar)
        self.char_edit_fields["avatar"] = w_avatar

        # Live2D 模型：下拉 + 刷新 + 打开目录 + 导入
        w_l2d = EditableCombo()
        w_l2d.setToolTip(
            "从 live2d-models/ 与 model_dict.json 自动扫描。留空表示该角色不使用 Live2D"
        )
        row_l2d = QHBoxLayout()
        row_l2d.addWidget(w_l2d, stretch=1)
        btn_refresh_l2d = QPushButton("↻")
        btn_refresh_l2d.setFixedWidth(32)
        btn_refresh_l2d.setToolTip("刷新 Live2D 模型列表")
        btn_refresh_l2d.clicked.connect(self._populate_live2d_combo)
        btn_open_l2d_dir = QPushButton("📂")
        btn_open_l2d_dir.setFixedWidth(32)
        btn_open_l2d_dir.setToolTip("在资源管理器中打开 live2d-models/ 保存目录")
        btn_open_l2d_dir.clicked.connect(self._open_live2d_dir)
        btn_import_l2d = QPushButton("导入...")
        btn_import_l2d.setToolTip("从其他目录导入 Live2D 模型（文件夹或 zip 压缩包）")
        btn_import_l2d.clicked.connect(self._import_live2d_menu)
        row_l2d.addWidget(btn_refresh_l2d)
        row_l2d.addWidget(btn_open_l2d_dir)
        row_l2d.addWidget(btn_import_l2d)
        look_form.addRow("Live2D 模型：", row_l2d)
        self.char_edit_fields["live2d_model_name"] = w_l2d

        char_edit_vbox.addWidget(look_box)

        # ── 人设 ──
        persona_box = QGroupBox("人设")
        persona_form = QFormLayout(persona_box)
        self.char_edit_persona = QPlainTextEdit()
        self.char_edit_persona.setMinimumHeight(110)
        self.char_edit_persona.setPlaceholderText("角色的人设提示词...")
        persona_form.addRow(self.char_edit_persona)
        char_edit_vbox.addWidget(persona_box)

        # ── 内部标识（一般无需修改）──
        id_box = QGroupBox("内部标识（一般无需修改）")
        id_form = QFormLayout(id_box)
        for key, label, tip in [
            ("conf_uid", "conf_uid", "角色唯一标识；同时用作 chat_history/<conf_uid>/ 的目录名，需唯一"),
        ]:
            w = QLineEdit()
            w.setMinimumWidth(200)
            w.setToolTip(tip)
            id_form.addRow(f"{label}：", w)
            self.char_edit_fields[key] = w
        char_edit_vbox.addWidget(id_box)

        btn_save_char = QPushButton("保存角色")
        btn_save_char.clicked.connect(self._save_character_inline)
        char_edit_vbox.addWidget(btn_save_char)
        char_edit_vbox.addStretch(1)

        char_edit_scroll.setWidget(char_edit_inner)
        tab_char_layout.addWidget(char_edit_scroll, stretch=2)

        self.tabs.addTab(tab_char, "角色")

        # ── Tab 4: LLM ──
        tab_llm = QWidget()
        tab_llm_scroll = QScrollArea()
        tab_llm_scroll.setWidgetResizable(True)
        tab_llm_scroll.setFrameShape(QScrollArea.NoFrame)
        tab_llm_inner = QWidget()
        tab_llm_layout = QVBoxLayout(tab_llm_inner)

        # Ollama 专用面板
        self.llm_param_box = QGroupBox("Ollama LLM 参数")
        llm_param_layout = QFormLayout(self.llm_param_box)

        model_row = QHBoxLayout()
        self.combo_model = QComboBox()
        self.combo_model.setEditable(True)
        self.combo_model.setInsertPolicy(QComboBox.NoInsert)
        self.combo_model.setMinimumWidth(240)
        self.combo_model.currentTextChanged.connect(self._on_model_text_changed)
        btn_refresh_models = QPushButton("↻")
        btn_refresh_models.setToolTip("从 Ollama 刷新已安装模型列表")
        btn_refresh_models.setFixedWidth(32)
        btn_refresh_models.clicked.connect(self._refresh_ollama_models)
        model_row.addWidget(self.combo_model, stretch=1)
        model_row.addWidget(btn_refresh_models)
        llm_param_layout.addRow("模型名称：", model_row)

        self.spin_temperature = QDoubleSpinBox()
        self.spin_temperature.setRange(0.0, 2.0)
        self.spin_temperature.setSingleStep(0.1)
        self.spin_temperature.setDecimals(2)
        self.spin_temperature.setValue(0.7)

        self.spin_num_gpu = QSpinBox()
        self.spin_num_gpu.setRange(-1, 256)
        self.spin_num_gpu.setSpecialValueText("自动 (-1)")
        self.spin_num_gpu.setValue(16)

        self.spin_num_ctx = QSpinBox()
        self.spin_num_ctx.setRange(512, 131072)
        self.spin_num_ctx.setSingleStep(512)
        self.spin_num_ctx.setValue(4096)

        self.chk_think = QCheckBox("启用 thinking（Qwen 等模型）")

        self.combo_keep_alive = QComboBox()
        self.combo_keep_alive.addItems([
            "-1（永久驻留）",
            "0（立即卸载）",
            "60（1 分钟）",
            "300（5 分钟）",
            "600（10 分钟）",
        ])
        self.combo_keep_alive.setEditable(True)

        llm_param_layout.addRow("Temperature：", self.spin_temperature)
        llm_param_layout.addRow("GPU 层数：", self.spin_num_gpu)
        llm_param_layout.addRow("上下文长度：", self.spin_num_ctx)
        llm_param_layout.addRow("", self.chk_think)
        llm_param_layout.addRow("Keep Alive：", self.combo_keep_alive)
        tab_llm_layout.addWidget(self.llm_param_box)

        # 通用 LLM 面板
        self.llm_generic_box = QGroupBox("LLM 参数")
        self.llm_generic_form = QFormLayout(self.llm_generic_box)
        self.llm_generic_box.setVisible(False)
        tab_llm_layout.addWidget(self.llm_generic_box)

        # 模型信息
        self.model_info_box = QGroupBox("模型信息")
        mi_layout = QVBoxLayout(self.model_info_box)
        self.model_info_label = QLabel("（选择模型后显示）")
        self.model_info_label.setWordWrap(True)
        self.model_info_label.setStyleSheet("font-family: Consolas, monospace; color: #333;")
        mi_layout.addWidget(self.model_info_label)
        tab_llm_layout.addWidget(self.model_info_box)

        tab_llm_layout.addStretch(1)
        tab_llm_scroll.setWidget(tab_llm_inner)
        tab_llm_layout_final = QVBoxLayout(tab_llm)
        tab_llm_layout_final.setContentsMargins(0, 0, 0, 0)
        tab_llm_layout_final.addWidget(tab_llm_scroll)
        self.tabs.addTab(tab_llm, "语言模型")

        # ── Tab 4: TTS ──
        tab_tts = QWidget()
        tab_tts_scroll = QScrollArea()
        tab_tts_scroll.setWidgetResizable(True)
        tab_tts_scroll.setFrameShape(QScrollArea.NoFrame)
        tab_tts_inner = QWidget()
        tab_tts_layout = QVBoxLayout(tab_tts_inner)

        # GPT-SoVITS 面板
        self.gsv_box = QGroupBox("GPT-SoVITS")
        gsv_layout = QFormLayout(self.gsv_box)

        # 声音模型 = 权重对 + 参考音频，一一对应（voices/ 目录）
        voice_row = QHBoxLayout()
        self.combo_voice = QComboBox()
        self.combo_voice.setMinimumWidth(220)
        btn_refresh_voice = QPushButton("↻")
        btn_refresh_voice.setFixedWidth(32)
        btn_refresh_voice.setToolTip("刷新 voices/ 目录中的声音模型")
        btn_refresh_voice.clicked.connect(self._populate_voice_models)
        voice_row.addWidget(self.combo_voice, stretch=1)
        voice_row.addWidget(btn_refresh_voice)
        gsv_layout.addRow("声音模型：", voice_row)

        # 当前实际生效的声音（由 conf.yaml 的 ref_audio_path 反查）
        self.lbl_active_voice = QLabel("当前使用：（未知）")
        self.lbl_active_voice.setWordWrap(True)
        self.lbl_active_voice.setStyleSheet("color: #b8860b; font-weight: bold;")
        gsv_layout.addRow("", self.lbl_active_voice)

        voice_btn_row = QHBoxLayout()
        self.btn_apply_voice = QPushButton("应用声音")
        self.btn_apply_voice.setToolTip("把该声音的参考音频写入 conf.yaml，并切换对应权重")
        self.btn_apply_voice.clicked.connect(self._apply_voice_model)
        btn_new_voice = QPushButton("新建...")
        btn_new_voice.setToolTip("选择权重对 + 参考音频，创建新的声音模型")
        btn_new_voice.clicked.connect(self._new_voice_model)
        btn_edit_voice = QPushButton("编辑...")
        btn_edit_voice.setToolTip("修改该声音的权重、参考音频、提示文本")
        btn_edit_voice.clicked.connect(self._edit_voice_model)
        btn_del_voice = QPushButton("删除")
        btn_del_voice.setToolTip("删除该声音模型（移除 voices/ 下的文件夹）")
        btn_del_voice.clicked.connect(self._delete_voice_model)
        for b in (self.btn_apply_voice, btn_new_voice, btn_edit_voice, btn_del_voice):
            voice_btn_row.addWidget(b)
        gsv_layout.addRow("", voice_btn_row)

        # 参考音频试听
        audition_row = QHBoxLayout()
        self.btn_audition = QPushButton("▶ 试听参考音频")
        self.btn_audition.setToolTip("播放所选声音模型的参考音频")
        self.btn_audition.clicked.connect(self._audition_ref_audio)
        self.btn_stop_audition = QPushButton("■ 停止")
        self.btn_stop_audition.setFixedWidth(72)
        self.btn_stop_audition.setToolTip("停止播放")
        self.btn_stop_audition.clicked.connect(stop_audio)
        self.lbl_ref_audio = QLabel("（未选择）")
        self.lbl_ref_audio.setStyleSheet("color: #666;")
        audition_row.addWidget(self.btn_audition)
        audition_row.addWidget(self.btn_stop_audition)
        audition_row.addWidget(self.lbl_ref_audio, stretch=1)
        gsv_layout.addRow("", audition_row)

        gsv_dir_row = QHBoxLayout()
        self.gsv_dir_label = QLabel("（未设置）")
        self.gsv_dir_label.setWordWrap(True)
        btn_pick_gsv = QPushButton("选择目录...")
        btn_pick_gsv.clicked.connect(self._pick_gsv_dir)
        gsv_dir_row.addWidget(self.gsv_dir_label, stretch=1)
        gsv_dir_row.addWidget(btn_pick_gsv)
        gsv_layout.addRow("根目录：", gsv_dir_row)

        self.gsv_bat_label = QLabel(DEFAULT_GPT_BAT)
        gsv_layout.addRow("启动脚本：", self.gsv_bat_label)

        # 当前权重（只读）：权重在「新建/编辑声音」里选择
        self.lbl_current_weights = QLabel("当前：（未知）")
        self.lbl_current_weights.setWordWrap(True)
        self.lbl_current_weights.setStyleSheet("color: #666;")
        gsv_layout.addRow("当前权重：", self.lbl_current_weights)

        gsv_btn_row = QHBoxLayout()
        self.btn_start_gsv = QPushButton("启动 GPT-SoVITS")
        self.btn_stop_gsv = QPushButton("停止 GPT-SoVITS")
        self.btn_stop_gsv.setEnabled(False)
        self.btn_start_gsv.clicked.connect(self._start_gsv)
        self.btn_stop_gsv.clicked.connect(self._stop_gsv)
        gsv_btn_row.addWidget(self.btn_start_gsv)
        gsv_btn_row.addWidget(self.btn_stop_gsv)
        gsv_layout.addRow("", gsv_btn_row)

        tab_tts_layout.addWidget(self.gsv_box)

        # 通用 TTS 面板
        self.tts_generic_box = QGroupBox("TTS 参数")
        self.tts_generic_form = QFormLayout(self.tts_generic_box)
        self.tts_generic_box.setVisible(False)
        tab_tts_layout.addWidget(self.tts_generic_box)

        tab_tts_layout.addStretch(1)
        tab_tts_scroll.setWidget(tab_tts_inner)
        tab_tts_layout_final = QVBoxLayout(tab_tts)
        tab_tts_layout_final.setContentsMargins(0, 0, 0, 0)
        tab_tts_layout_final.addWidget(tab_tts_scroll)
        self.tabs.addTab(tab_tts, "TTS")

        # ── Tab 5: ASR/VAD ──
        tab_asr_vad = QWidget()
        tab_av_layout = QHBoxLayout(tab_asr_vad)

        # ASR 面板（左半）
        asr_group = QGroupBox("ASR 参数")
        asr_vbox = QVBoxLayout(asr_group)
        self.asr_generic_form = QFormLayout()
        asr_vbox.addLayout(self.asr_generic_form)
        tab_av_layout.addWidget(asr_group, stretch=1)

        # VAD 面板（右半）
        vad_group = QGroupBox("VAD 参数")
        vad_vbox = QVBoxLayout(vad_group)
        self.vad_generic_form = QFormLayout()
        vad_vbox.addLayout(self.vad_generic_form)
        tab_av_layout.addWidget(vad_group, stretch=1)

        self.tabs.addTab(tab_asr_vad, "ASR / VAD")

        # ── 底部操作栏（始终可见）──
        bottom_bar = QHBoxLayout()
        self.btn_save = QPushButton("保存配置")
        self.btn_save.clicked.connect(self._save_config)
        bottom_bar.addWidget(self.btn_save)
        bottom_bar.addStretch(1)
        root_layout.addLayout(bottom_bar)

        # ── 信号连接 ──
        self.combo_llm.currentTextChanged.connect(self._on_llm_provider_changed)
        self.combo_voice.currentTextChanged.connect(lambda _: self._on_voice_changed())
        self.combo_tts.currentTextChanged.connect(self._on_tts_model_changed)
        self.combo_asr_model.currentTextChanged.connect(self._on_asr_model_changed)
        self.combo_vad_model.currentTextChanged.connect(self._on_vad_model_changed)

        # 未保存改动检测的基线刷新。
        # 这些槽在对应的处理函数**之后**执行（Qt 按连接顺序调用），
        # 用来把"面板重新填充带来的值变化"从"用户改动"里排除掉。
        # 每个槽只刷新该处理函数会重新填充的区块，不含承载该下拉本身的区块——
        # 否则用户刚改的选择会被一并当成已保存而漏报。
        self.combo_character.currentIndexChanged.connect(
            lambda _: self._mark_sections_saved("_角色字段")
        )
        self.combo_llm.currentTextChanged.connect(
            lambda _: self._mark_sections_saved("语言模型")
        )
        self.combo_tts.currentTextChanged.connect(
            lambda _: self._mark_sections_saved("TTS")
        )
        self.combo_asr_model.currentTextChanged.connect(
            lambda _: self._mark_sections_saved("ASR / VAD")
        )
        self.combo_vad_model.currentTextChanged.connect(
            lambda _: self._mark_sections_saved("ASR / VAD")
        )

    # ------------------------------------------------------------------
    # 项目目录 & 配置加载
    # ------------------------------------------------------------------

    def _discover_and_load(self):
        script_dir = Path(__file__).resolve().parent
        root = find_project_root(script_dir)
        if root is None:
            self._log("[启动器] 未自动发现项目目录，请点击「手动选择...」。")
            return
        self._set_project_root(root)

    def _pick_project(self):
        folder = QFileDialog.getExistingDirectory(self, "选择 Open-LLM-VTuber 项目根目录")
        if not folder:
            return
        p = Path(folder)
        if not (p / "conf.yaml").exists() or not (p / "run_server.py").exists():
            QMessageBox.warning(self, "路径无效",
                                "该目录下没有同时找到 conf.yaml 和 run_server.py。")
            return
        self._set_project_root(p)

    def _set_project_root(self, root: Path):
        self.project_root = root
        self.path_label.setText(str(root))
        self._log(f"[启动器] 项目目录：{root}")
        self._load_launcher_config()
        self._load_config()

    def _launcher_config_path(self) -> Path:
        return Path(__file__).resolve().parent / "launcher_config.json"

    def _load_launcher_config(self):
        p = self._launcher_config_path()
        if p.exists():
            try:
                self.launcher_cfg = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                self._log(f"[启动器] ⚠ 读取 launcher_config.json 失败：{e}")
                self.launcher_cfg = {}
        else:
            self.launcher_cfg = {}
        self.launcher_cfg.setdefault("presets", {})
        self.launcher_cfg.setdefault("gpt_sovits_model", {})
        # 恢复「自动打开浏览器」勾选状态（默认开）
        self.chk_open_browser.blockSignals(True)
        self.chk_open_browser.setChecked(
            bool(self.launcher_cfg.get("auto_open_browser", True))
        )
        self.chk_open_browser.blockSignals(False)

    def _save_launcher_config(self):
        try:
            self._launcher_config_path().write_text(
                json.dumps(self.launcher_cfg, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            self._log(f"[启动器] ⚠ 保存 launcher_config.json 失败：{e}")

    def _pick_gsv_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择 GPT-SoVITS 根目录")
        if not folder:
            return
        self._set_gsv_dir(Path(folder), save=True)

    def _set_gsv_dir(self, gsv_dir: Path, save: bool = False):
        self.launcher_cfg["gpt_sovits_root"] = str(gsv_dir)
        self.gsv_dir_label.setText(str(gsv_dir))
        if save:
            self._save_launcher_config()
            self._log(f"[启动器] ✔ GPT-SoVITS 根目录已设为：{gsv_dir}")
        self._update_current_weights_label()

    def _infer_gsv_dir_from_conf(self):
        if not self.config:
            return None
        ref = (
            self.config.get("character_config", {})
            .get("tts_config", {})
            .get("gpt_sovits_tts", {})
            .get("ref_audio_path")
        )
        if not ref:
            return None
        try:
            ref_path = Path(str(ref))
        except Exception:
            return None
        # 参考音频若放在项目内的 voices/ 下，它不指示 GPT-SoVITS 安装位置
        try:
            ref_path.resolve().relative_to(self._voices_dir().resolve())
            return None
        except (ValueError, OSError):
            pass
        return ref_path.parent

    def _load_config(self):
        conf_path = self.project_root / "conf.yaml"
        self._loading_config = True
        try:
            with open(conf_path, "r", encoding="utf-8") as f:
                self.config = self.yaml.load(f)
            self._log("[启动器] 已读取 conf.yaml")
        except Exception as e:
            QMessageBox.critical(self, "读取失败", f"无法读取 conf.yaml：\n{e}")
            self._loading_config = False
            return

        self._populate_characters()
        self._populate_llms()
        self._populate_tts()
        self._populate_asr()
        self._populate_vad()
        self._refresh_preset_list()
        self._populate_live2d_combo()
        self._populate_avatar_combo()
        self._populate_voice_models()

        gsv_dir = self.launcher_cfg.get("gpt_sovits_root")
        if gsv_dir and Path(gsv_dir).is_dir():
            self._set_gsv_dir(Path(gsv_dir))
        else:
            inferred = self._infer_gsv_dir_from_conf()
            if inferred and inferred.is_dir():
                self._set_gsv_dir(inferred, save=True)
                self._log("[启动器] 已从 conf.yaml 的 ref_audio_path 推断 GPT-SoVITS 根目录")
            else:
                self._log("[启动器] ⚠ 未自动找到 GPT-SoVITS 根目录，请点击「选择目录...」")

        self._loading_config = False
        # 触发一次面板切换
        self._on_llm_provider_changed(self.combo_llm.currentText())
        self._on_tts_model_changed(self.combo_tts.currentText())
        self._on_asr_model_changed(self.combo_asr_model.currentText())
        self._on_vad_model_changed(self.combo_vad_model.currentText())

        # 界面已与 conf.yaml 同步，重设未保存改动检测的基线
        self._reset_dirty_baseline()

    # ------------------------------------------------------------------
    # 角色
    # ------------------------------------------------------------------

    def _populate_characters(self):
        self.combo_character.clear()
        self._character_entries = []

        alts_dir = self.config.get("system_config", {}).get("config_alts_dir", "characters")
        chars_dir = self.project_root / alts_dir

        if chars_dir.is_dir():
            files = sorted(list(chars_dir.glob("*.yaml")) + list(chars_dir.glob("*.yml")))
            for f in files:
                stem = f.stem
                char_name = stem
                avatar = ""
                conf_uid = ""
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        c = self.yaml.load(fp) or {}
                    cc = c.get("character_config", c)
                    # 显示名与 Web UI 保持一致：character_name（回退 conf_uid/文件名）
                    char_name = cc.get("character_name") or cc.get("conf_uid") or stem
                    conf_uid = cc.get("conf_uid") or ""
                    avatar = cc.get("avatar") or ""
                except Exception:
                    pass
                display = f"{char_name} ({stem})"
                self._character_entries.append(
                    CharEntry(display, stem, char_name, avatar, conf_uid)
                )

        for entry in self._character_entries:
            self.combo_character.addItem(entry.display)

        # 首位固定为「使用 conf.yaml 基础配置」——此时不指定默认角色
        self.combo_character.insertItem(0, BASE_CONFIG_ENTRY)
        self._character_entries.insert(
            0, CharEntry(BASE_CONFIG_ENTRY, "", "", "", "")
        )

        # default_character 指针是"应用了哪个角色文件"的唯一依据。
        # 指针为空 → 基础配置项；指针缺失/指向不存在的文件 → 同样回落基础配置项，
        # 而不是去匹配 conf.yaml 自身的角色身份（那会导致保存时把坏指针静默改写掉）。
        pointer = str(
            self.config.get("system_config", {}).get("default_character") or ""
        ).strip()
        self.combo_character.setCurrentIndex(0)
        if pointer:
            for i, entry in enumerate(self._character_entries):
                if entry.stem and f"{entry.stem}.yaml" == pointer:
                    self.combo_character.setCurrentIndex(i)
                    break
            else:
                self._log(
                    f"[启动器] ⚠ default_character='{pointer}' 未在 {alts_dir}/ 中找到对应文件，"
                    f"已回落为「{BASE_CONFIG_ENTRY}」（后端启动时同样会忽略该指针）"
                )

        self._log(f"[启动器] 发现角色 {len(self._character_entries) - 1} 个")

        self._on_character_changed(self.combo_character.currentIndex())

    def _on_character_changed(self, idx):
        if idx < 0 or idx >= len(self._character_entries):
            self.avatar_label.setPixmap(QPixmap())
            self.avatar_label.setText("无头像")
            for w in self.char_edit_fields.values():
                w.setText("")
            self.char_edit_persona.setPlainText("")
            return

        entry = self._character_entries[idx]
        stem, avatar = entry.stem, entry.avatar

        pix = self._find_avatar_pixmap(avatar)
        if pix is not None and not pix.isNull():
            self.avatar_label.setPixmap(
                pix.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.avatar_label.setText("")
        else:
            self.avatar_label.setPixmap(QPixmap())
            self.avatar_label.setText("无头像")

        # 加载角色文件到右侧编辑器
        # 首项「使用 conf.yaml 基础配置」没有独立文件，直接编辑 conf.yaml 自身的角色
        if stem:
            char_file = self._get_alts_dir() / f"{stem}.yaml"
        else:
            char_file = self.project_root / "conf.yaml"
        cc = {}
        try:
            with open(char_file, "r", encoding="utf-8") as f:
                char_data = self.yaml.load(f) or {}
            cc = char_data.get("character_config", char_data)
        except Exception:
            pass

        for key, w in self.char_edit_fields.items():
            w.setText(str(cc.get(key, "")))
        self.char_edit_persona.setPlainText(str(cc.get("persona_prompt", "")))

        # 预览跟随当前角色的 Live2D 模型
        self._preview_current_character_l2d()

    def _find_avatar_pixmap(self, avatar_name):
        if not avatar_name:
            return None
        for d in AVATAR_DIR_CANDIDATES:
            p = self.project_root / d / avatar_name
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    return pix
        return None

    # ------------------------------------------------------------------
    # 角色配置编辑器
    # ------------------------------------------------------------------

    def _get_alts_dir(self) -> Path:
        alts = (
            self.config.get("system_config", {})
            .get("config_alts_dir", "characters")
        )
        return self.project_root / alts

    def _new_character(self):
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        name, ok = QInputDialog.getText(
            self, "新建角色",
            "角色文件名（英文标识，将生成 <名称>.yaml）："
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if re.search(r'[\\/:*?"<>|]', name):
            QMessageBox.warning(self, "名称无效", "文件名不能包含 \\ / : * ? \" < > |")
            return
        chars_dir = self._get_alts_dir()
        target = chars_dir / f"{name}.yaml"
        if target.exists():
            QMessageBox.warning(self, "已存在", f"角色文件已存在：{target.name}")
            return

        template = {
            "character_config": {
                # 唯一标识：同时用作 chat_history/<conf_uid>/ 目录名
                "conf_uid": f"{name}_001",
                # 以下显示相关字段一律留空，由用户自己填
                "live2d_model_name": "",
                "character_name": "",
                "human_name": "",
                "avatar": "",
                # 回答语言（可在启动器下拉里改）
                "language": "",
                "persona_prompt": f"You are {name}, a friendly AI assistant.",
            }
        }
        try:
            chars_dir.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                self.yaml.dump(template, f)
            self._log(f"[启动器] ✔ 已创建角色文件：{target.name}")
            self._populate_characters()
            # 选中新角色
            for i, entry in enumerate(self._character_entries):
                if entry.stem == name:
                    self.combo_character.setCurrentIndex(i)
                    break
        except Exception as e:
            QMessageBox.critical(self, "创建失败", f"写入文件时出错：\n{e}")

    def _save_character_inline(self):
        if not self.project_root:
            return
        idx = self.combo_character.currentIndex()
        if idx < 0 or idx >= len(self._character_entries):
            QMessageBox.warning(self, "未选择角色", "请先在左侧选择一个角色。")
            return

        stem = self._character_entries[idx].stem
        # 首项「使用 conf.yaml 基础配置」没有独立文件，直接写回 conf.yaml
        if stem:
            char_file = self._get_alts_dir() / f"{stem}.yaml"
        else:
            char_file = self.project_root / "conf.yaml"

        try:
            with open(char_file, "r", encoding="utf-8") as f:
                char_data = self.yaml.load(f) or {}
        except Exception:
            char_data = {}

        cc = char_data.get("character_config", char_data)
        for key, w in self.char_edit_fields.items():
            value = w.text().strip()
            # 原本没有的空可选字段不写，避免往角色 YAML 里添加空行噪声；
            # 但字段已存在时按当前值写回（这样清空操作才能真正生效）
            if not value and key not in cc:
                continue
            cc[key] = value

        # 唯一标识留空时自动补全，避免写出空值导致启动失败
        if not cc.get("conf_uid"):
            cc["conf_uid"] = f"{cc.get('character_name') or stem}_001"
        # 角色名是后端必填项，留空会让服务起不来。按约定用 conf_uid 兜底。
        if not cc.get("character_name"):
            cc["character_name"] = cc["conf_uid"]
            self._log(
                f"[启动器] ⚠ 角色名为空，已用 conf_uid「{cc['conf_uid']}」兜底"
            )

        cc["persona_prompt"] = self.char_edit_persona.toPlainText()
        char_data["character_config"] = cc

        try:
            with open(char_file, "w", encoding="utf-8") as f:
                self.yaml.dump(char_data, f)
            self._log(
                f"[启动器] ✔ 已保存角色：{stem}" if stem else "[启动器] ✔ 已保存基础配置角色"
            )
            # 刷新列表但保持选中
            old_stem = stem
            self._populate_characters()
            for i, entry in enumerate(self._character_entries):
                if entry.stem == old_stem:
                    self.combo_character.setCurrentIndex(i)
                    break
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入文件时出错：\n{e}")

    def _delete_character(self):
        if not self.project_root:
            return
        idx = self.combo_character.currentIndex()
        if idx < 0 or idx >= len(self._character_entries):
            return

        entry = self._character_entries[idx]
        stem, char_name = entry.stem, entry.name
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除角色「{char_name}」（{stem}.yaml）吗？\n\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        chars_dir = self._get_alts_dir()
        char_file = chars_dir / f"{stem}.yaml"
        try:
            if char_file.exists():
                char_file.unlink()
            self._log(f"[启动器] ✔ 已删除角色文件：{stem}.yaml")
            self._populate_characters()
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除文件时出错：\n{e}")

    # ------------------------------------------------------------------
    # Live2D 模型 / 头像下拉 + model_dict.json 管理
    # ------------------------------------------------------------------

    def _scan_live2d_model_names(self) -> list:
        """model_dict.json 中的模型名 ∪ live2d-models/ 子目录名。"""
        names = set()
        if not self.project_root:
            return []
        for item in self._load_model_dict():
            n = item.get("name")
            if n:
                names.add(str(n))
        models_dir = self.project_root / "live2d-models"
        if models_dir.is_dir():
            for d in models_dir.iterdir():
                if d.is_dir() and not d.name.startswith("."):
                    names.add(d.name)
        return sorted(names)

    def _populate_live2d_combo(self):
        w = self.char_edit_fields.get("live2d_model_name")
        if not isinstance(w, EditableCombo):
            return
        current = w.currentText()
        w.clear()
        # 首个空选项让「不使用 Live2D」成为可表达、可保持的状态。
        # 否则 addItems 之后 currentIndex 会变成 0，界面会显示一个其实没被选中的模型。
        w.addItem("")
        w.addItems(self._scan_live2d_model_names())
        w.setText(current if current else "")

    def _import_avatar(self):
        """从本地选择图片，复制到 avatars/ 并选中。"""
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择头像图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.gif);;所有文件 (*)"
        )
        if not path:
            return
        path = Path(path)
        # 优先 avatars/，不存在则创建
        target_dir = self.project_root / AVATAR_DIR_CANDIDATES[0]
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / path.name
            if target.exists() and target.resolve() != path.resolve():
                reply = QMessageBox.question(
                    self, "文件已存在",
                    f"avatars/ 中已存在「{path.name}」，覆盖吗？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return
            if target.resolve() != path.resolve():
                shutil.copy2(path, target)
            self._log(f"[启动器] ✔ 头像已导入：{target.name}")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"复制图片时出错：\n{e}")
            return

        self._populate_avatar_combo()
        w = self.char_edit_fields.get("avatar")
        if isinstance(w, EditableCombo):
            w.setText(path.name)

    def _populate_avatar_combo(self):
        w = self.char_edit_fields.get("avatar")
        if not isinstance(w, EditableCombo):
            return
        current = w.currentText()
        w.clear()
        names = []
        if self.project_root:
            for d in AVATAR_DIR_CANDIDATES:
                p = self.project_root / d
                if p.is_dir():
                    names += [
                        f.name for f in sorted(p.iterdir())
                        if f.is_file()
                        and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif")
                    ]
        w.addItem("")   # 空选项 = 不使用头像，避免默认选中第一个文件
        w.addItems(sorted(set(names)))
        w.setText(current if current else "")

    def _model_dict_path(self) -> Path:
        return self.project_root / "model_dict.json"

    def _load_model_dict(self) -> list:
        p = self._model_dict_path()
        if not p.exists():
            return []
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception as e:
            self._log(f"[启动器] ⚠ 读取 model_dict.json 失败：{e}")
            return []

    def _resolve_model_dir(self, name: str, url: str = ""):
        """根据模型名/URL 定位模型文件夹。

        角色配置里的 live2d_model_name 未必等于文件夹名
        （例如 'shizuku-local' 对应的目录是 'shizuku'），所以逐级回退。
        """
        if not self.project_root:
            return None
        if url:
            p = self.project_root / url.lstrip("/")
            if p.exists():
                return p.parent
        if not name:
            return None

        models_dir = self.project_root / "live2d-models"
        if not models_dir.is_dir():
            return None

        exact = models_dir / name
        if exact.is_dir():
            return exact

        # 去掉 -local / _local / -zh 之类的后缀再试
        stripped = re.sub(r"[-_](local|zh|cn|jp|en)$", "", name, flags=re.I)
        if stripped != name:
            cand = models_dir / stripped
            if cand.is_dir():
                return cand

        # 忽略大小写、忽略分隔符差异
        def norm(s: str) -> str:
            return re.sub(r"[-_\s]", "", s).lower()

        target = norm(name)
        candidates = [d for d in models_dir.iterdir() if d.is_dir()]
        for d in candidates:
            if norm(d.name) == target:
                return d
        # 最后：一方是另一方的前缀（'shizuku' vs 'shizuku2'）
        for d in candidates:
            n = norm(d.name)
            if n and (n.startswith(target) or target.startswith(n)):
                return d
        return None

    def _find_model_texture(self, model_dir: Path):
        """在模型目录里找贴图。返回 (来源, 数据)：
        来源为 'file' 时数据是 Path，为 'zip' 时数据是 (zip路径, 内部条目名) 元组。

        Live2D 模型常把 UI 素材（按钮图标等）放在 images/ 下，必须排除，
        否则会把 info.png 这种图标误当成模型贴图显示。
        """
        UI_DIRS = {"images", "css", "js", "sounds", "voice", "motions"}

        def is_texture_path(p: Path) -> bool:
            return not any(part.lower() in UI_DIRS for part in p.parts)

        # 1) Cubism 3/4：texture_00.png 等
        for p in sorted(model_dir.rglob("texture_*.png")):
            if is_texture_path(p):
                return "file", p
        # 2) 模型主目录下的直接图片
        for p in sorted(model_dir.glob("*.png")):
            if is_texture_path(p):
                return "file", p
        # 3) Cubism 2.1：贴图打包在 .zip 里
        for z in sorted(model_dir.rglob("*.zip")):
            try:
                with zipfile.ZipFile(z) as zf:
                    names = [
                        n for n in zf.namelist()
                        if n.lower().endswith((".png", ".jpg"))
                        and "texture" in n.lower()
                    ] or [
                        n for n in zf.namelist()
                        if n.lower().endswith(".png")
                    ]
                    if names:
                        return "zip", (z, sorted(names)[0])
            except Exception:
                continue
        # 4) 兜底：子目录里的图片（仍排除 UI 目录）
        for p in sorted(model_dir.rglob("*.png")):
            if is_texture_path(p):
                return "file", p
        return None, None

    def _show_l2d_preview(self, model_name: str, url: str = ""):
        """按模型名刷新左上预览，并在下方提示该模型能否被前端加载。"""
        model_dir = self._resolve_model_dir(model_name, url)
        if model_dir is None:
            self.l2d_preview.setPixmap(QPixmap())
            self.l2d_preview.setText(
                f"（未找到模型文件夹）\n{model_name}" if model_name else "（未选择模型）"
            )
            self.l2d_preview_tip.setText("模型贴图静态预览，实际动画以前端为准")
            self.l2d_preview_tip.setStyleSheet("color: #888; font-size: 11px;")
            return

        # 顺带判断格式兼容性（前端只支持 .model3.json）
        entry, entry_kind = self._find_model_entry(model_dir)
        if entry_kind == "model3":
            self.l2d_preview_tip.setText("✔ Cubism 3/4，前端可加载")
            self.l2d_preview_tip.setStyleSheet("color: #1a7f37; font-size: 11px;")
        elif entry_kind == "model2":
            self.l2d_preview_tip.setText(
                f"⚠ Cubism 2.1（{entry.name}），前端不支持\n"
                "需用 Live2D Cubism Editor 转为 .model3.json"
            )
            self.l2d_preview_tip.setStyleSheet("color: #b8860b; font-size: 11px;")
        else:
            self.l2d_preview_tip.setText("⚠ 未找到模型入口文件")
            self.l2d_preview_tip.setStyleSheet("color: #b8860b; font-size: 11px;")

        kind, data = self._find_model_texture(model_dir)
        if kind is None:
            self.l2d_preview.setPixmap(QPixmap())
            self.l2d_preview.setText("（无贴图文件）")
            return
        if kind == "file":
            pix = QPixmap(str(data))
        else:
            zip_path, zentry = data
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    pix = QPixmap()
                    pix.loadFromData(zf.read(zentry))
            except Exception:
                pix = QPixmap()
        if pix.isNull():
            self.l2d_preview.setText("（贴图无法读取）")
            return
        self.l2d_preview.setText("")
        self.l2d_preview.setPixmap(
            pix.scaled(210, 210, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.l2d_preview.setToolTip(f"{model_name}\n{model_dir}")

    def _preview_current_character_l2d(self):
        """按当前角色的 live2d_model_name 刷新预览。"""
        if not self.project_root:
            return
        idx = self.combo_character.currentIndex()
        if idx < 0 or idx >= len(self._character_entries):
            return
        w = self.char_edit_fields.get("live2d_model_name")
        model_name = w.text().strip() if w is not None else ""
        if model_name:
            self._show_l2d_preview(model_name)

    # ------------------------------------------------------------------
    # Live2D 目录 / 导入
    # ------------------------------------------------------------------

    def _open_live2d_dir(self):
        """在资源管理器中打开 live2d-models/ 目录。"""
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        d = self.project_root / "live2d-models"
        d.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(d))
            self._log(f"[启动器] 📂 已打开目录：{d}")
        except Exception as e:
            self._log(f"[启动器] ⚠ 打开目录失败：{e}（路径：{d}）")

    @staticmethod
    def _find_model_entry(model_dir: Path):
        """在模型目录中寻找前端可用的入口文件。

        返回 (entry_path, kind)：
          kind = 'model3'  → Cubism 3/4，前端可用
          kind = 'model2'  → Cubism 2.1，前端不支持
          kind = None      → 未找到入口
        优先取层级最浅的 .model3.json。
        """
        def shallow(paths):
            return sorted(paths, key=lambda p: (len(p.relative_to(model_dir).parts), str(p)))

        m3 = shallow(list(model_dir.rglob("*.model3.json")))
        if m3:
            return m3[0], "model3"
        m2 = shallow(list(model_dir.rglob("*.model.json")))
        if m2:
            return m2[0], "model2"
        return None, None

    def _model_dict_upsert(self, name: str, entry_path: Path) -> bool:
        """把模型写入 model_dict.json（存在则更新 url）。返回是否有改动。"""
        url = "/" + entry_path.relative_to(self.project_root).as_posix()
        entries = self._load_model_dict()
        for item in entries:
            if item.get("name") == name:
                if item.get("url") == url:
                    return False
                item["url"] = url
                break
        else:
            entries.append({
                "name": name,
                "description": "",
                "url": url,
                "kScale": 0.5,
                "initialXshift": 0,
                "initialYshift": 0,
                "kXOffset": 1150,
                "idleMotionGroupName": "Idle",
                "emotionMap": {},
                "tapMotions": {},
            })

        p = self._model_dict_path()
        try:
            if p.exists():
                shutil.copy2(p, p.with_suffix(".json.bak"))
            p.write_text(
                json.dumps(entries, ensure_ascii=False, indent=4), encoding="utf-8"
            )
        except Exception as e:
            self._log(f"[启动器] ⚠ 写入 model_dict.json 失败：{e}")
            return False
        return True

    def _import_live2d_menu(self):
        """导入入口：弹出菜单选择导入方式。"""
        from PySide6.QtWidgets import QMenu

        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        btn = self.sender()
        menu = QMenu(self)
        act_dir = menu.addAction("导入文件夹...")
        act_dir.setToolTip("可选单个模型文件夹，或包含多个模型的总目录")
        act_zip = menu.addAction("导入压缩包 (.zip)...")
        act_zip.setToolTip("可一次选择多个 zip，各自解压为一个模型")
        chosen = menu.exec(btn.mapToGlobal(btn.rect().bottomLeft())) if btn else None
        if chosen is act_dir:
            self._import_live2d_folder()
        elif chosen is act_zip:
            self._import_live2d_zip()

    def _import_live2d_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择 Live2D 模型文件夹（或其上级目录）"
        )
        if not folder:
            return
        src = Path(folder)
        models_dir = self.project_root / "live2d-models"
        models_dir.mkdir(parents=True, exist_ok=True)

        # 选中的目录本身是模型 → 单个导入；否则把每个子目录当一个模型
        if self._find_model_entry(src)[1]:
            candidates = [src]
        else:
            subdirs = [
                d for d in sorted(src.iterdir())
                if d.is_dir() and self._find_model_entry(d)[1]
            ]
            if not subdirs:
                QMessageBox.warning(
                    self, "未找到模型",
                    f"在 {src} 及其子目录中没有找到 .model3.json / .model.json 入口文件。"
                )
                return
            candidates = subdirs

        registered, skipped, failed = [], [], []
        for d in candidates:
            target = models_dir / d.name
            if target.exists():
                reply = QMessageBox.question(
                    self, "已存在",
                    f"live2d-models/ 中已存在「{d.name}」，覆盖吗？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    skipped.append(d.name)
                    continue
                shutil.rmtree(target, ignore_errors=True)
            try:
                shutil.copytree(d, target)
            except Exception as e:
                failed.append(f"{d.name}（{e}）")
                continue
            ok, reason = self._register_imported_model(target)
            (registered if ok else failed).append(
                target.name if ok else f"{target.name}（{reason}）"
            )

        self._finish_import(registered, skipped, failed, candidates)

    def _import_live2d_zip(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择 Live2D 模型压缩包", "",
            "压缩包 (*.zip);;所有文件 (*)"
        )
        if not files:
            return
        models_dir = self.project_root / "live2d-models"
        models_dir.mkdir(parents=True, exist_ok=True)

        registered, skipped, failed = [], [], []
        for f in files:
            z = Path(f)
            name = z.stem
            target = models_dir / name
            if target.exists():
                reply = QMessageBox.question(
                    self, "已存在",
                    f"live2d-models/ 中已存在「{name}」，覆盖吗？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    skipped.append(name)
                    continue
                shutil.rmtree(target, ignore_errors=True)
            try:
                target.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(z) as zf:
                    _safe_extract(zf, target)
            except Exception as e:
                failed.append(f"{name}（{e}）")
                continue
            ok, reason = self._register_imported_model(target)
            (registered if ok else failed).append(
                target.name if ok else f"{target.name}（{reason}）"
            )

        self._finish_import(registered, skipped, failed, [Path(f) for f in files])

    def _register_imported_model(self, target: Path):
        """登记刚导入的模型。返回 (是否登记, 原因)。"""
        entry, kind = self._find_model_entry(target)
        if kind is None:
            return False, "未找到入口文件"
        if kind == "model2":
            return False, (
                f"Cubism 2.1 格式（{entry.name}），"
                "当前前端只支持 .model3.json，需用 Live2D Cubism Editor 转换"
            )
        self._model_dict_upsert(target.name, entry)
        return True, ""

    def _finish_import(self, registered, skipped, failed, sources):
        n_src = len(sources)
        if registered:
            self._log(f"[启动器] ✔ 导入成功 {len(registered)} 个：{', '.join(registered)}")
        for name in skipped:
            self._log(f"[启动器] 已跳过（用户取消）：{name}")
        for item in failed:
            self._log(f"[启动器] ✘ 导入失败：{item}")

        self._populate_live2d_combo()

        lines = [f"共处理 {n_src} 项："]
        if registered:
            lines.append(f"✔ 成功 {len(registered)} 个：\n   " + "\n   ".join(registered))
        if skipped:
            lines.append(f"— 跳过 {len(skipped)} 个：\n   " + "\n   ".join(skipped))
        if failed:
            lines.append(f"✘ 失败 {len(failed)} 个：\n   " + "\n   ".join(failed))
        if registered:
            lines.append("\n已自动写入 model_dict.json，前端刷新后即可选择。")

        box = QMessageBox(self)
        box.setWindowTitle("导入 Live2D 模型")
        box.setText("\n".join(lines))
        box.setIcon(QMessageBox.Information if registered else QMessageBox.Warning)
        box.exec()

    # ------------------------------------------------------------------
    # LLM / TTS 下拉
    # ------------------------------------------------------------------

    def _populate_llms(self):
        self.combo_llm.clear()
        llm_configs = (
            self.config.get("character_config", {})
            .get("agent_config", {})
            .get("llm_configs", {})
        )
        names = list(llm_configs.keys())
        self.combo_llm.addItems(names)

        current = (
            self.config.get("character_config", {})
            .get("agent_config", {})
            .get("agent_settings", {})
            .get("basic_memory_agent", {})
            .get("llm_provider", "")
        )
        if current in names:
            self.combo_llm.setCurrentText(current)
        elif current:
            self._log(f"[启动器] ⚠ 当前 llm_provider='{current}' 不在 llm_configs 中")
        self._log(f"[启动器] 发现 LLM 配置 {len(names)} 个")

    def _populate_tts(self):
        self.combo_tts.clear()
        tts_config = (
            self.config.get("character_config", {})
            .get("tts_config", {})
        )
        names = [k for k in tts_config.keys() if k != "tts_model"]
        self.combo_tts.addItems(names)

        current = tts_config.get("tts_model", "")
        if current in names:
            self.combo_tts.setCurrentText(current)
        elif current:
            self._log(f"[启动器] ⚠ 当前 tts_model='{current}' 不在 tts_config 中")
        self._log(f"[启动器] 发现 TTS 后端 {len(names)} 个")

    # ------------------------------------------------------------------
    # ASR / VAD 下拉
    # ------------------------------------------------------------------

    def _populate_asr(self):
        self.combo_asr_model.blockSignals(True)
        self.combo_asr_model.clear()
        self.combo_asr_model.addItems(["（禁用）"] + ASR_ENGINES)

        asr_config = (
            self.config.get("character_config", {})
            .get("asr_config", {})
        )
        current = asr_config.get(ASR_ENGINE_KEY, "")
        if current in ASR_ENGINES:
            self.combo_asr_model.setCurrentText(current)
        else:
            self.combo_asr_model.setCurrentText("（禁用）")
        self.combo_asr_model.blockSignals(False)
        self._log(f"[启动器] ASR 引擎：{current or '禁用'}")

    def _populate_vad(self):
        self.combo_vad_model.blockSignals(True)
        self.combo_vad_model.clear()
        self.combo_vad_model.addItems(["（禁用）", "silero_vad"])

        vad_config = (
            self.config.get("character_config", {})
            .get("vad_config", {})
        )
        current = vad_config.get(VAD_ENGINE_KEY)
        if current == "silero_vad":
            self.combo_vad_model.setCurrentText("silero_vad")
        else:
            self.combo_vad_model.setCurrentText("（禁用）")
        self.combo_vad_model.blockSignals(False)
        self._log(f"[启动器] VAD 引擎：{current or '禁用'}")

    # ------------------------------------------------------------------
    # 面板切换：ASR
    # ------------------------------------------------------------------

    def _on_asr_model_changed(self, model_text: str):
        if self._loading_config or self.config is None:
            return
        clear_layout(self.asr_generic_form)
        self._generic_asr_editors.clear()
        self._generic_asr_originals.clear()

        asr_config = (
            self.config.get("character_config", {})
            .get("asr_config", {})
        )

        if model_text == "（禁用）" or not model_text:
            lbl = QLabel("ASR 已禁用")
            lbl.setStyleSheet("color: #888;")
            self.asr_generic_form.addRow(lbl)
            return

        engine_cfg = asr_config.get(model_text)
        if not isinstance(engine_cfg, dict) or not engine_cfg:
            lbl = QLabel(f"（{model_text} 没有配置）")
            lbl.setStyleSheet("color: #888;")
            self.asr_generic_form.addRow(lbl)
            return

        self._fill_generic_form(
            self.asr_generic_form,
            engine_cfg,
            self._generic_asr_editors,
            self._generic_asr_originals,
        )

    # ------------------------------------------------------------------
    # 面板切换：VAD
    # ------------------------------------------------------------------

    def _on_vad_model_changed(self, model_text: str):
        if self._loading_config or self.config is None:
            return
        clear_layout(self.vad_generic_form)
        self._generic_vad_editors.clear()
        self._generic_vad_originals.clear()

        vad_config = (
            self.config.get("character_config", {})
            .get("vad_config", {})
        )

        if model_text == "（禁用）" or not model_text:
            lbl = QLabel("VAD 已禁用")
            lbl.setStyleSheet("color: #888;")
            self.vad_generic_form.addRow(lbl)
            return

        engine_cfg = vad_config.get(model_text)
        if not isinstance(engine_cfg, dict) or not engine_cfg:
            lbl = QLabel(f"（{model_text} 没有配置）")
            lbl.setStyleSheet("color: #888;")
            self.vad_generic_form.addRow(lbl)
            return

        self._fill_generic_form(
            self.vad_generic_form,
            engine_cfg,
            self._generic_vad_editors,
            self._generic_vad_originals,
        )

    # ------------------------------------------------------------------
    # Ollama 模型列表 & 信息
    # ------------------------------------------------------------------

    def _auto_refresh_models_if_online(self):
        if is_port_open(OLLAMA_HOST, OLLAMA_PORT):
            self._refresh_ollama_models(silent=True)

    def _refresh_ollama_models(self, silent: bool = False):
        models = query_ollama_models()
        if models is None:
            if not silent:
                self._log("[启动器] ⚠ 无法从 Ollama 获取模型列表（服务可能未启动）")
            return

        current = self.combo_model.currentText()
        self.combo_model.blockSignals(True)
        self.combo_model.clear()
        self.combo_model.addItems(models)
        if current:
            self.combo_model.setEditText(current)
        self.combo_model.blockSignals(False)
        if not silent:
            self._log(f"[启动器] ✔ 发现 Ollama 已安装模型 {len(models)} 个")

        if current:
            self._refresh_model_info(current)

    def _on_model_text_changed(self, text: str):
        if not text:
            return
        QTimer.singleShot(400, lambda t=text: self._refresh_model_info(t))

    def _refresh_model_info(self, model_name: str):
        if not model_name:
            return
        if not is_port_open(OLLAMA_HOST, OLLAMA_PORT):
            return
        threading.Thread(
            target=self._refresh_model_info_worker,
            args=(model_name,),
            daemon=True,
        ).start()

    def _refresh_model_info_worker(self, model_name: str):
        # 该线程是 daemon，关窗口时可能正处在解释器终结阶段，
        # 此时模块全局或 Qt 对象可能已失效，忽略即可（不影响用户）
        try:
            self._refresh_model_info_impl(model_name)
        except Exception:
            pass

    def _refresh_model_info_impl(self, model_name: str):
        info = query_ollama_show(model_name)
        if info is None:
            self.model_info_signal.emit(f"（无法获取 {model_name} 的信息）")
            return

        lines = []
        lines.append(f"模型：{model_name}")

        details = info.get("details") or {}
        family = details.get("family") or ""
        params = details.get("parameter_size") or ""
        quant = details.get("quantization_level") or ""
        fmt = details.get("format") or ""
        if family:
            lines.append(f"架构：{family}")
        if params:
            lines.append(f"参数规模：{params}")
        if quant:
            lines.append(f"量化：{quant}")
        if fmt:
            lines.append(f"格式：{fmt}")

        model_info = info.get("model_info") or {}
        ctx = None
        for k, v in model_info.items():
            if k.endswith(".context_length") or k == "context_length":
                try:
                    ctx = int(v)
                    break
                except Exception:
                    pass
        if ctx:
            lines.append(f"最大上下文：{ctx}")

        for k, v in model_info.items():
            if k.endswith(".block_count"):
                try:
                    lines.append(f"Block 数：{int(v)}")
                except Exception:
                    pass
                break

        size = info.get("size")
        if size:
            lines.append(f"磁盘占用：{format_size_bytes(size)}")

        params_str = info.get("parameters") or ""
        if params_str:
            lines.append("")
            lines.append("默认参数：")
            for p in params_str.splitlines():
                if p.strip():
                    lines.append(f"  {p.strip()}")

        self.model_info_signal.emit("\n".join(lines))

    def _on_model_info_update(self, text: str):
        self.model_info_label.setText(text)

    # ------------------------------------------------------------------
    # 通用参数面板（LLM / TTS）
    # ------------------------------------------------------------------

    def _get_provider_config(self, provider_name: str):
        try:
            return (
                self.config.get("character_config", {})
                .get("agent_config", {})
                .get("llm_configs", {})
                .get(provider_name, {})
            )
        except Exception:
            return {}

    def _get_tts_config(self, tts_name: str):
        try:
            return (
                self.config.get("character_config", {})
                .get("tts_config", {})
                .get(tts_name, {})
            )
        except Exception:
            return {}

    def _fill_generic_form(self, form: QFormLayout, cfg: dict, editors: dict, originals: dict):
        """根据 cfg 内容动态生成 form 里的编辑控件。editors / originals 会被清空后填充"""
        clear_layout(form)
        editors.clear()
        originals.clear()

        if not isinstance(cfg, dict) or not cfg:
            empty = QLabel("（此 provider 没有可编辑参数）")
            empty.setStyleSheet("color: #888;")
            form.addRow(empty)
            return

        for key, value in cfg.items():
            originals[key] = value
            if isinstance(value, bool):
                w = QCheckBox()
                w.setChecked(value)
            else:
                w = QLineEdit()
                if value is None:
                    w.setText("")
                    w.setPlaceholderText("(null)")
                else:
                    w.setText(str(value))
            w.setMinimumWidth(320)
            form.addRow(f"{key}：", w)
            editors[key] = w

    def _collect_generic_values(self, editors: dict, originals: dict) -> dict:
        """从编辑控件收集回写值"""
        result = {}
        for key, w in editors.items():
            orig = originals.get(key)
            if isinstance(w, QCheckBox):
                result[key] = bool(w.isChecked())
            elif isinstance(w, QLineEdit):
                result[key] = coerce_back(orig, w.text().strip())
            else:
                result[key] = orig
        return result

    # ------------------------------------------------------------------
    # 面板切换：LLM
    # ------------------------------------------------------------------

    def _on_llm_provider_changed(self, provider_name: str):
        if self._loading_config or self.config is None:
            return

        if provider_name == OLLAMA_PROVIDER_KEY:
            # 显示 Ollama 专用
            self.llm_param_box.setVisible(True)
            self.model_info_box.setVisible(True)
            self.llm_generic_box.setVisible(False)
            self._load_ollama_params()
        else:
            # 显示通用
            self.llm_param_box.setVisible(False)
            self.model_info_box.setVisible(False)
            cfg = self._get_provider_config(provider_name)
            self.llm_generic_box.setTitle(f"{provider_name} 参数")
            self._fill_generic_form(
                self.llm_generic_form,
                cfg,
                self._generic_llm_editors,
                self._generic_llm_originals,
            )
            self.llm_generic_box.setVisible(True)

    def _load_ollama_params(self):
        if self.config is None:
            return
        cfg = self._get_provider_config(OLLAMA_PROVIDER_KEY)

        self.combo_model.setEditText(str(cfg.get("model", "qwen3.5:9b")))

        try:
            self.spin_temperature.setValue(float(cfg.get("temperature", 0.7)))
        except Exception:
            self.spin_temperature.setValue(0.7)

        try:
            self.spin_num_gpu.setValue(int(cfg.get("num_gpu", 16)))
        except Exception:
            self.spin_num_gpu.setValue(16)

        try:
            self.spin_num_ctx.setValue(int(cfg.get("num_ctx", 4096)))
        except Exception:
            self.spin_num_ctx.setValue(4096)

        self.chk_think.setChecked(bool(cfg.get("think", False)))

        ka = cfg.get("keep_alive", -1)
        try:
            ka_int = int(float(ka))
        except Exception:
            ka_int = -1
        ka_str = f"{ka_int}（永久驻留）" if ka_int < 0 else f"{ka_int}"
        self.combo_keep_alive.setCurrentText(ka_str)

        if self.combo_model.currentText():
            self._refresh_model_info(self.combo_model.currentText())

    def _parse_keep_alive(self) -> int:
        text = self.combo_keep_alive.currentText().strip()
        m = re.match(r"^\s*(-?\d+)", text)
        if m:
            return int(m.group(1))
        return -1

    # ------------------------------------------------------------------
    # 面板切换：TTS
    # ------------------------------------------------------------------

    def _on_tts_model_changed(self, tts_name: str):
        if self._loading_config or self.config is None:
            return

        if tts_name == GPT_SOVITS_TTS_KEY:
            self.gsv_box.setVisible(True)
            self.tts_generic_box.setVisible(False)
            self._update_current_weights_label()
            self._on_voice_changed()
        else:
            self.gsv_box.setVisible(False)
            cfg = self._get_tts_config(tts_name)
            self.tts_generic_box.setTitle(f"{tts_name} 参数")
            self._fill_generic_form(
                self.tts_generic_form,
                cfg,
                self._generic_tts_editors,
                self._generic_tts_originals,
            )
            self.tts_generic_box.setVisible(True)

    # ------------------------------------------------------------------
    # 声音模型（voices/ 目录：权重对 + 参考音频 一一对应）
    # ------------------------------------------------------------------

    def _voices_dir(self) -> Path:
        return self.project_root / "voices"

    def _list_voice_models(self) -> list:
        d = self._voices_dir()
        if not d.is_dir():
            return []
        return sorted(p.name for p in d.iterdir() if p.is_dir())

    def _load_voice(self, name: str) -> dict:
        p = self._voices_dir() / name / "voice.json"
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            self._log(f"[启动器] ⚠ 读取 {name}/voice.json 失败：{e}")
            return {}

    def _populate_voice_models(self):
        names = self._list_voice_models()
        current = self.combo_voice.currentText()
        self.combo_voice.blockSignals(True)
        self.combo_voice.clear()
        self.combo_voice.addItems(names)
        # 优先恢复当前选中，其次匹配 conf.yaml 里的参考音频
        if current and current in names:
            self.combo_voice.setCurrentText(current)
        else:
            matched = self._voice_from_conf()
            if matched:
                self.combo_voice.setCurrentText(matched)
        self.combo_voice.blockSignals(False)
        if names:
            self._log(f"[启动器] 发现声音模型 {len(names)} 个：{', '.join(names)}")
        else:
            self._log("[启动器] ⚠ voices/ 目录中没有声音模型")

    def _voice_from_conf(self):
        """根据 conf.yaml 的 ref_audio_path 反查属于哪个声音模型。"""
        if not self.config:
            return None
        ref = (
            self.config.get("character_config", {})
            .get("tts_config", {})
            .get("gpt_sovits_tts", {})
            .get("ref_audio_path")
        )
        if not ref:
            return None
        try:
            ref_path = Path(str(ref)).resolve()
        except Exception:
            return None
        for name in self._list_voice_models():
            d = self._voices_dir() / name
            for audio in d.glob("ref.*"):
                try:
                    if audio.resolve() == ref_path:
                        return name
                except Exception:
                    continue
        return None

    def _current_voice_meta(self):
        """返回当前所选声音的 (名称, 目录, 元数据, 参考音频路径)；无效时全为 None。"""
        name = self.combo_voice.currentText().strip()
        if not name:
            return None, None, None, None
        voice_dir = self._voices_dir() / name
        meta = self._load_voice(name)
        ref = next(iter(sorted(voice_dir.glob("ref.*"))), None)
        return name, voice_dir, meta, ref

    def _on_voice_changed(self):
        """切换声音模型时更新参考音频提示与「当前使用」标签。"""
        _, _, _, ref = self._current_voice_meta()
        if ref is not None:
            size_kb = ref.stat().st_size / 1024
            self.lbl_ref_audio.setText(f"{ref.name}  ({size_kb:.0f} KB)")
            self.lbl_ref_audio.setToolTip(str(ref))
        else:
            self.lbl_ref_audio.setText("（无参考音频）")
            self.lbl_ref_audio.setToolTip("")
        self._update_active_voice_label()

    def _update_active_voice_label(self):
        """显示 conf.yaml 中实际生效的声音模型。"""
        if not self.config:
            self.lbl_active_voice.setText("当前使用：（未加载配置）")
            return
        gsv = (
            self.config.get("character_config", {})
            .get("tts_config", {})
            .get("gpt_sovits_tts", {})
        )
        ref_path = gsv.get("ref_audio_path", "")
        if not ref_path:
            self.lbl_active_voice.setText("当前使用：（conf.yaml 未设置参考音频）")
            return
        matched = self._voice_from_conf()
        if matched:
            self.lbl_active_voice.setText(f"当前使用：{matched} ✓")
            self.lbl_active_voice.setStyleSheet(
                "color: #1a7f37; font-weight: bold;"
            )
            self.lbl_active_voice.setToolTip(
                f"ref_audio_path = {ref_path}\n"
                f"prompt_lang = {gsv.get('prompt_lang', '')} | "
                f"text_lang = {gsv.get('text_lang', '')}"
            )
        else:
            self.lbl_active_voice.setText(
                f"当前使用：（不在 voices/ 中）{Path(str(ref_path)).name}"
            )
            self.lbl_active_voice.setStyleSheet(
                "color: #b8860b; font-weight: bold;"
            )
            self.lbl_active_voice.setToolTip(
                f"conf.yaml 指向：{ref_path}\n"
                "该参考音频不属于 voices/ 下的任何声音模型。"
            )

    def _audition_ref_audio(self):
        """试听当前所选声音的参考音频。"""
        stop_audio()
        _, _, _, ref = self._current_voice_meta()
        if ref is None:
            QMessageBox.warning(self, "无参考音频",
                                "当前声音模型没有 ref.* 音频文件可试听。")
            return
        ok, msg = play_audio(ref)
        self._log(f"[启动器] {'♪' if ok else '⚠'} 试听 {ref.name}：{msg}")

    def _apply_voice_model(self):
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        name, voice_dir, meta, ref_audio = self._current_voice_meta()
        if not name:
            QMessageBox.warning(self, "未选择声音", "请先选择一个声音模型。")
            return
        if not meta:
            QMessageBox.warning(self, "元数据缺失",
                                f"未找到 {voice_dir / 'voice.json'}\n无法应用该声音模型。")
            return
        if ref_audio is None:
            QMessageBox.warning(self, "缺少参考音频",
                                f"{voice_dir} 中没有 ref.* 音频文件。")
            return

        # 权重若已指定，先校验版本兼容性
        gpt_text = meta.get("gpt_weight", "")
        sovits_text = meta.get("sovits_weight", "")
        if gpt_text and sovits_text:
            gpt_path, sovits_path, err = self._resolve_weights(gpt_text, sovits_text)
            if not err and not self._confirm_version_match(self, gpt_path, sovits_path):
                return

        # 写回 conf.yaml
        cc = self.config.setdefault("character_config", {})
        gsv = cc.setdefault("tts_config", {}).setdefault("gpt_sovits_tts", {})
        gsv["ref_audio_path"] = str(ref_audio)
        gsv["prompt_text"] = meta.get("prompt_text", "")
        gsv["prompt_lang"] = meta.get("prompt_lang", "zh")
        gsv["text_lang"] = meta.get("text_lang", "zh")
        gsv["streaming_mode"] = SingleQuotedScalarString("false")
        self._save_config()
        self._update_active_voice_label()
        self._log(
            f"[启动器] ✔ 声音「{name}」已应用并写入 conf.yaml："
            f"ref={ref_audio.name}, prompt_lang={gsv['prompt_lang']}, "
            f"text_lang={gsv['text_lang']}"
        )

        if gpt_text and sovits_text:
            self._switch_weights(gpt_text, sovits_text)
        else:
            self._log("[启动器] ⚠ 该声音未指定权重对，只切换了参考音频")

        # 声音的语言（text_lang）与当前角色语言不一致时，提示同步
        self._prompt_language_sync(meta.get("text_lang", ""), name)

    def _prompt_language_sync(self, voice_lang: str, voice_name: str):
        """声音语言与角色语言不一致时询问是否同步到角色。"""
        voice_lang = (voice_lang or "").strip().lower()
        if voice_lang in ("", "auto") or voice_lang not in LANGUAGE_NATIVE_NAMES:
            return

        widget = self.char_edit_fields.get("language")
        if not isinstance(widget, CodeCombo):
            return
        role_lang = widget.text().strip().lower()

        if role_lang == voice_lang:
            return

        native = LANGUAGE_NATIVE_NAMES[voice_lang]
        if role_lang:
            question = (
                f"声音「{voice_name}」是{native}语音，\n"
                f"但当前角色语言是「{LANGUAGE_CODE_TO_LABEL.get(role_lang, role_lang)}」。\n\n"
                f"要把角色语言也改成{native}吗？\n"
                f"（角色语言决定它用什么语言回答，建议与语音保持一致）"
            )
        else:
            question = (
                f"声音「{voice_name}」是{native}语音，\n"
                f"当前角色语言未设置（不限制）。\n\n"
                f"要把角色语言设为{native}吗？\n"
                f"（这样角色会只用{native}回答，与语音一致）"
            )

        reply = QMessageBox.question(
            self, "同步角色语言", question,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            self._log(
                f"[启动器] 已跳过语言同步（声音={voice_lang}, 角色={role_lang or '未设置'}）"
            )
            return

        widget.setText(voice_lang)
        # 用户的确认就是明确动作，直接保存，避免留下未生效的半成品
        self._save_character_inline()
        self._log(f"[启动器] ✔ 已将角色语言同步为{native}（{voice_lang}）并保存角色")

    # ------------------------------------------------------------------
    # 声音模型 CRUD
    # ------------------------------------------------------------------

    def _voice_weight_items(self):
        return self._gpt_weight_items(silent=True), self._sovits_weight_items(silent=True)

    def _open_voice_dialog(self, name=None):
        """打开新建/编辑声音对话框。name 为 None 表示新建。返回 True 表示已保存。"""
        gpt_items, sovits_items = self._voice_weight_items()
        if not gpt_items or not sovits_items:
            QMessageBox.warning(
                self, "未找到权重",
                "没有扫描到 GPT/SoVITS 权重文件。\n"
                "请先在 TTS 页设置 GPT-SoVITS 根目录，并确认权重目录里有模型。"
            )
            return False

        initial = None
        if name:
            voice_dir = self._voices_dir() / name
            meta = self._load_voice(name)
            ref = next(iter(sorted(voice_dir.glob("ref.*"))), None)
            initial = dict(meta)
            initial["name"] = name
            initial["ref_audio"] = str(ref) if ref else ""

        dlg = VoiceDialog(self, gpt_items, sovits_items, initial=initial)
        if dlg.exec() != QDialog.Accepted:
            return False
        data = dlg.result_data()

        new_name = data["name"]
        old_name = name
        target_dir = self._voices_dir() / new_name
        try:
            if old_name and old_name != new_name:
                # 改名：重命名目录（复制参考音频后删旧目录）
                old_dir = self._voices_dir() / old_name
                target_dir.mkdir(parents=True, exist_ok=True)
                _copy_in_ref(data["ref_audio"], target_dir)
                _write_voice_json(target_dir, data)
                shutil.rmtree(old_dir, ignore_errors=True)
                self._log(f"[启动器] ✔ 声音已重命名：{old_name} → {new_name}")
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                _copy_in_ref(data["ref_audio"], target_dir)
                _write_voice_json(target_dir, data)
                self._log(f"[启动器] ✔ 已{'更新' if old_name else '创建'}声音模型「{new_name}」")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入声音模型时出错：\n{e}")
            return False

        self._populate_voice_models()
        self.combo_voice.setCurrentText(new_name)
        self._on_voice_changed()
        return True

    def _new_voice_model(self):
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        if self._open_voice_dialog():
            self._log("[启动器] 提示：点「应用声音」可立即生效")

    def _edit_voice_model(self):
        if not self.project_root:
            return
        name, _, meta, _ = self._current_voice_meta()
        if not name:
            QMessageBox.warning(self, "未选择声音", "请先选择一个声音模型。")
            return
        if not meta:
            QMessageBox.warning(self, "元数据缺失",
                                f"voices/{name}/voice.json 不存在，无法编辑。\n"
                                f"可以改用「新建...」重新创建一个声音模型。")
            return
        self._open_voice_dialog(name)

    def _delete_voice_model(self):
        if not self.project_root:
            return
        name, voice_dir, _, _ = self._current_voice_meta()
        if not name:
            QMessageBox.warning(self, "未选择声音", "请先选择一个声音模型。")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除声音模型「{name}」吗？\n\n"
            f"将删除目录：{voice_dir}\n（不影响 GPT-SoVITS 里的权重文件）\n\n"
            f"此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            shutil.rmtree(voice_dir)
            self._log(f"[启动器] ✔ 已删除声音模型「{name}」")
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除目录时出错：\n{e}")
            return
        self._populate_voice_models()
        self._on_voice_changed()

    # ------------------------------------------------------------------
    # GPT-SoVITS 权重列表
    # ------------------------------------------------------------------

    def _current_gsv_root(self):
        gsv_root = self.launcher_cfg.get("gpt_sovits_root")
        if gsv_root and Path(gsv_root).is_dir():
            return Path(gsv_root)
        return None

    def _gpt_weight_items(self, silent: bool = False) -> list:
        """扫描 GPT 权重，返回 '文件名  [目录]' 列表。"""
        root = self._current_gsv_root()
        if not root:
            if not silent:
                self._log("[启动器] ⚠ 未设置 GPT-SoVITS 根目录")
            return []
        files = list_weight_files(root, GPT_WEIGHTS_PREFIX, ".ckpt")
        if not silent:
            self._log(f"[启动器] ✔ 发现 GPT 权重 {len(files)} 个")
        return files

    def _sovits_weight_items(self, silent: bool = False) -> list:
        """扫描 SoVITS 权重，返回 '文件名  [目录]' 列表。"""
        root = self._current_gsv_root()
        if not root:
            if not silent:
                self._log("[启动器] ⚠ 未设置 GPT-SoVITS 根目录")
            return []
        files = list_weight_files(root, SOVITS_WEIGHTS_PREFIX, ".pth")
        if not silent:
            self._log(f"[启动器] ✔ 发现 SoVITS 权重 {len(files)} 个")
        return files

    @staticmethod
    def _item_index(items: list, name: str) -> int:
        """在权重标识列表中找条目：精确匹配，或匹配其文件名部分。"""
        if not name:
            return -1
        for i, text in enumerate(items):
            if text == name or split_weight_text(text)[0] == name:
                return i
        return -1

    def _update_current_weights_label(self):
        saved = self.launcher_cfg.get("gpt_sovits_model", {})
        gpt_name = saved.get("gpt") or "（未选）"
        sovits_name = saved.get("sovits") or "（未选）"
        short = lambda s: s if len(s) <= 34 else s[:31] + "..."
        self.lbl_current_weights.setText(
            f"GPT: {short(gpt_name)}\nSoVITS: {short(sovits_name)}"
        )
        self.lbl_current_weights.setToolTip(
            f"GPT: {gpt_name}\nSoVITS: {sovits_name}"
            "\n\n（权重在「新建/编辑」声音模型里选择）"
        )

    def _resolve_weights(self, gpt_text: str, sovits_text: str):
        """把权重标识解析成路径。返回 (gpt_path, sovits_path, 错误消息)。"""
        root = self._current_gsv_root()
        if not root:
            return None, None, "未设置 GPT-SoVITS 根目录"
        if not gpt_text or not sovits_text:
            return None, None, "未指定 GPT / SoVITS 权重"
        gpt_path = find_weight_path(root, GPT_WEIGHTS_PREFIX, gpt_text)
        sovits_path = find_weight_path(root, SOVITS_WEIGHTS_PREFIX, sovits_text)
        if not gpt_path or not sovits_path:
            return None, None, (
                f"找不到权重文件：\n"
                f"GPT: {gpt_path or gpt_text}\n"
                f"SoVITS: {sovits_path or sovits_text}"
            )
        return gpt_path, sovits_path, ""

    @staticmethod
    def _confirm_version_match(parent, gpt_path: Path, sovits_path: Path) -> bool:
        """API 以 v4 启动，应用其他版本权重时警告。返回是否继续。"""
        for label, path in (("GPT", gpt_path), ("SoVITS", sovits_path)):
            if path.parent.name not in ("GPT_weights_v4", "SoVITS_weights_v4"):
                reply = QMessageBox.warning(
                    parent, "版本不匹配",
                    f"{label} 权重「{path.name}」属于 {path.parent.name}，"
                    f"但当前 API 以 v4 模式启动，混用可能导致合成失败或音质异常。\n"
                    f"仍要使用吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return False
        return True

    def _switch_weights(self, gpt_text: str, sovits_text: str):
        """记录并在 GPT-SoVITS 运行时切换权重。"""
        gpt_path, sovits_path, err = self._resolve_weights(gpt_text, sovits_text)
        if err:
            self._log(f"[启动器] ⚠ {err}")
            return
        self.launcher_cfg["gpt_sovits_model"] = {
            "gpt": gpt_path.name,
            "sovits": sovits_path.name,
        }
        self._save_launcher_config()
        self._update_current_weights_label()

        if not is_port_open(GPT_SOVITS_HOST, GPT_SOVITS_PORT):
            self._log("[启动器] ⚠ GPT-SoVITS 未运行，已记录权重；"
                      "启动时会自动切换（或启动后重新点「应用声音」）")
            return
        threading.Thread(
            target=self._apply_weights_worker,
            args=(gpt_path, sovits_path),
            daemon=True,
        ).start()

    def _apply_weights_worker(self, gpt_path: Path, sovits_path: Path):
        self.oneclick_progress_signal.emit(f"[启动器] ⏳ 正在切换 GPT 权重：{gpt_path.name}")
        ok, msg = gpt_sovits_set_weights("set_gpt_weights", gpt_path)
        if ok:
            self.oneclick_progress_signal.emit("[启动器] ✔ GPT 权重切换成功")
        else:
            self.oneclick_progress_signal.emit(f"[启动器] ✘ GPT 权重切换失败：{msg}")
            return

        self.oneclick_progress_signal.emit(f"[启动器] ⏳ 正在切换 SoVITS 权重：{sovits_path.name}")
        ok, msg = gpt_sovits_set_weights("set_sovits_weights", sovits_path)
        if ok:
            self.oneclick_progress_signal.emit("[启动器] ✔ SoVITS 权重切换成功")
        else:
            self.oneclick_progress_signal.emit(f"[启动器] ✘ SoVITS 权重切换失败：{msg}")
            return

        self.oneclick_progress_signal.emit("[启动器] ✔ 声音模型已切换完成")

    # ------------------------------------------------------------------
    # 配置预设
    # ------------------------------------------------------------------

    def _refresh_preset_list(self):
        self.preset_list.clear()
        presets = self.launcher_cfg.get("presets", {})
        for name in sorted(presets.keys()):
            self.preset_list.addItem(QListWidgetItem(name))

    def _save_preset(self):
        if not self.config:
            return
        name, ok = QInputDialog.getText(self, "保存预设", "预设名称：")
        if not ok or not name.strip():
            return
        name = name.strip()

        preset = {
            "llm_provider": self.combo_llm.currentText(),
            "tts_model": self.combo_tts.currentText(),
            "ollama": {
                "model": self.combo_model.currentText().strip(),
                "temperature": round(self.spin_temperature.value(), 2),
                "num_gpu": self.spin_num_gpu.value(),
                "num_ctx": self.spin_num_ctx.value(),
                "think": bool(self.chk_think.isChecked()),
                "keep_alive": self._parse_keep_alive(),
            },
        }
        self.launcher_cfg.setdefault("presets", {})[name] = preset
        self._save_launcher_config()
        self._refresh_preset_list()
        self._log(f"[启动器] ✔ 已保存预设「{name}」")

    def _apply_preset(self, item):
        if item is None:
            return
        name = item.text()
        presets = self.launcher_cfg.get("presets", {})
        p = presets.get(name)
        if not p:
            return

        # 恢复 provider / tts
        if p.get("llm_provider"):
            idx = self.combo_llm.findText(p["llm_provider"])
            if idx >= 0:
                self.combo_llm.setCurrentIndex(idx)
        if p.get("tts_model"):
            idx = self.combo_tts.findText(p["tts_model"])
            if idx >= 0:
                self.combo_tts.setCurrentIndex(idx)

        # 恢复 ollama 参数
        o = p.get("ollama", {})
        if o:
            self.combo_model.setEditText(str(o.get("model", "")))
            try:
                self.spin_temperature.setValue(float(o.get("temperature", 0.7)))
            except Exception:
                pass
            try:
                self.spin_num_gpu.setValue(int(o.get("num_gpu", 16)))
            except Exception:
                pass
            try:
                self.spin_num_ctx.setValue(int(o.get("num_ctx", 4096)))
            except Exception:
                pass
            self.chk_think.setChecked(bool(o.get("think", False)))
            ka = o.get("keep_alive", -1)
            try:
                ka_int = int(float(ka))
            except Exception:
                ka_int = -1
            ka_str = f"{ka_int}（永久驻留）" if ka_int < 0 else f"{ka_int}"
            self.combo_keep_alive.setCurrentText(ka_str)

        self._log(
            f"[启动器] ✔ 已把预设「{name}」载入到界面"
            "（还需点「应用并保存」或底部「保存配置」才会写入 conf.yaml）"
        )

    def _delete_preset(self):
        item = self.preset_list.currentItem()
        if item is None:
            return
        name = item.text()
        presets = self.launcher_cfg.get("presets", {})
        if name in presets:
            del presets[name]
            self._save_launcher_config()
            self._refresh_preset_list()
            self._log(f"[启动器] ✔ 已删除预设「{name}」")

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------

    # 内部分区名 -> 展示给用户的页面名（角色页拆成两段是因为它们的保存入口不同）
    SECTION_TO_PAGE = {
        "_角色选择": "角色",
        "_角色字段": "角色",
        "模型": "模型",
        "语言模型": "语言模型",
        "TTS": "TTS",
        "ASR / VAD": "ASR / VAD",
    }
    # 由 _save_config（写 conf.yaml）负责落盘的分区
    CONFIG_SECTIONS = ("_角色选择", "模型", "语言模型", "TTS", "ASR / VAD")

    @staticmethod
    def _editor_values(tag: str, editors: dict) -> list:
        out = []
        for key in sorted(editors):
            w = editors[key]
            val = w.isChecked() if isinstance(w, QCheckBox) else w.text()
            out.append(f"{tag}.{key}={val}")
        return out

    def _ui_sections(self) -> dict:
        """按页面把"参与持久化的控件取值"序列化，用于定位哪些页面有未保存改动。

        刻意只覆盖真正会被写入的控件，并且与写入条件保持一致：
        - 通用参数面板只在与当前选择相关时才计入（_save_config 也只写当前那一个），
          否则切走再切回时通用控件不会被清空，残留字段会造成假阳性
        - 角色编辑器的字段写入**角色文件**（由「保存角色」负责），与 conf.yaml 分开统计
        """
        sections = {}

        sections["_角色选择"] = f"char={self.combo_character.currentText()}"

        char_parts = [f"{k}={w.text()}" for k, w in sorted(self.char_edit_fields.items())]
        char_parts.append(f"persona={self.char_edit_persona.toPlainText()}")
        sections["_角色字段"] = "\n".join(char_parts)

        sections["模型"] = "\n".join(
            [
                f"llm={self.combo_llm.currentText()}",
                f"tts={self.combo_tts.currentText()}",
                f"asr={self.combo_asr_model.currentText()}",
                f"vad={self.combo_vad_model.currentText()}",
            ]
        )

        llm_parts = [
            f"model={self.combo_model.currentText()}",
            f"temperature={self.spin_temperature.value()}",
            f"num_gpu={self.spin_num_gpu.value()}",
            f"num_ctx={self.spin_num_ctx.value()}",
            f"think={self.chk_think.isChecked()}",
            f"keep_alive={self.combo_keep_alive.currentText()}",
        ]
        if self.combo_llm.currentText() != OLLAMA_PROVIDER_KEY:
            llm_parts += self._editor_values("gllm", self._generic_llm_editors)
        sections["语言模型"] = "\n".join(llm_parts)

        tts_parts = []
        if self.combo_tts.currentText() != GPT_SOVITS_TTS_KEY:
            tts_parts += self._editor_values("gtts", self._generic_tts_editors)
        sections["TTS"] = "\n".join(tts_parts)

        sections["ASR / VAD"] = "\n".join(
            self._editor_values("gasr", self._generic_asr_editors)
            + self._editor_values("gvad", self._generic_vad_editors)
        )
        return sections

    def _reset_dirty_baseline(self):
        """界面刚与磁盘同步过（如加载完配置）时，把全部区块的基线重设。

        对"切换角色 / 切换参数面板"这类局部重新填充，用 _mark_sections_saved(区块名)
        只刷新对应区块 —— 否则会把用户刚做的选择也一起当成"已保存"而漏报。
        """
        self._saved_sections = dict(self._ui_sections())

    def _mark_sections_saved(self, *names: str):
        """把指定分区标记为已落盘（其余分区保持原基线）。"""
        now = self._ui_sections()
        saved = dict(getattr(self, "_saved_sections", {}) or {})
        for name in names:
            saved[name] = now[name]
        self._saved_sections = saved

    def _mark_config_saved(self):
        """conf.yaml 落盘后调用。"""
        self._mark_sections_saved(*self.CONFIG_SECTIONS)

    def _mark_character_saved(self):
        """角色文件落盘后调用。"""
        self._mark_sections_saved("_角色字段")

    def _unsaved_pages(self) -> list:
        """返回存在未保存改动的页面名（去重、按固定顺序）。"""
        if not self.config or not self.project_root:
            return []
        saved = getattr(self, "_saved_sections", None)
        if not saved:
            return []
        now = self._ui_sections()
        pages = []
        for key, value in now.items():
            if value != saved.get(key, ""):
                name = self.SECTION_TO_PAGE.get(key, key)
                if name not in pages:
                    pages.append(name)
        return pages

    def _has_unsaved_changes(self) -> bool:
        return bool(self._unsaved_pages())

    def _char_fields_dirty(self) -> bool:
        saved = getattr(self, "_saved_sections", None)
        if not saved:
            return False
        return self._ui_sections()["_角色字段"] != saved.get("_角色字段", "")

    def _save_all(self):
        """把两个保存入口都走一遍：conf.yaml + 当前角色的角色文件。"""
        self._save_config()
        if self._char_fields_dirty() and self.combo_character.currentIndex() >= 0:
            self._save_character_inline()

    def _save_config(self):
        if not self.config or not self.project_root:
            return

        conf_path = self.project_root / "conf.yaml"
        backup = self.project_root / "conf.yaml.bak"

        try:
            backup.write_text(conf_path.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception as e:
            self._log(f"[启动器] ⚠ 备份失败：{e}")

        try:
            # 角色：只写"默认角色指针"，不把角色内容写进 conf.yaml。
            # 后端启动时读该文件 merge 到基础 character_config 之上，
            # 这样反复切换角色不会在 conf.yaml 里累积残留。
            idx = self.combo_character.currentIndex()
            self.config.setdefault("character_config", {})
            cc = self.config["character_config"]
            self.config.setdefault("system_config", {})
            sc = self.config["system_config"]
            if 0 <= idx < len(self._character_entries):
                entry = self._character_entries[idx]
                # 首项是「使用 conf.yaml 基础配置」→ 指针留空
                sc["default_character"] = f"{entry.stem}.yaml" if entry.stem else ""
                role_desc = (
                    f"{entry.name} ({entry.stem})" if entry.stem else BASE_CONFIG_ENTRY
                )
            else:
                sc.setdefault("default_character", "")
                role_desc = self.combo_character.currentText()

            # LLM provider
            cc.setdefault("agent_config", {})
            cc["agent_config"].setdefault("agent_settings", {})
            cc["agent_config"]["agent_settings"].setdefault("basic_memory_agent", {})
            cc["agent_config"]["agent_settings"]["basic_memory_agent"]["llm_provider"] = \
                self.combo_llm.currentText()

            # TTS model
            cc.setdefault("tts_config", {})
            cc["tts_config"]["tts_model"] = self.combo_tts.currentText()

            # LLM 参数：Ollama 用专用面板，其他用通用面板
            llm_configs = cc["agent_config"].setdefault("llm_configs", {})

            if OLLAMA_PROVIDER_KEY in llm_configs and isinstance(llm_configs[OLLAMA_PROVIDER_KEY], dict):
                ol = llm_configs[OLLAMA_PROVIDER_KEY]
                ol["model"] = self.combo_model.currentText().strip()
                ol["temperature"] = round(self.spin_temperature.value(), 2)
                ol["num_gpu"] = self.spin_num_gpu.value()
                ol["num_ctx"] = self.spin_num_ctx.value()
                ol["think"] = bool(self.chk_think.isChecked())
                ol["keep_alive"] = self._parse_keep_alive()

            current_llm = self.combo_llm.currentText()
            if current_llm != OLLAMA_PROVIDER_KEY and self._generic_llm_editors:
                target = llm_configs.get(current_llm)
                if isinstance(target, dict):
                    new_vals = self._collect_generic_values(
                        self._generic_llm_editors, self._generic_llm_originals
                    )
                    for k, v in new_vals.items():
                        target[k] = v
                    self._log(f"[启动器]   {current_llm}: 写入 {len(new_vals)} 个字段")

            # TTS 参数：GPT-SoVITS 走专用面板（其实没额外参数编辑），其他走通用
            current_tts = self.combo_tts.currentText()
            if current_tts != GPT_SOVITS_TTS_KEY and self._generic_tts_editors:
                target = cc["tts_config"].get(current_tts)
                if isinstance(target, dict):
                    new_vals = self._collect_generic_values(
                        self._generic_tts_editors, self._generic_tts_originals
                    )
                    for k, v in new_vals.items():
                        target[k] = v
                    self._log(f"[启动器]   {current_tts}: 写入 {len(new_vals)} 个字段")

            # ASR 参数
            cc.setdefault("asr_config", {})
            asr_text = self.combo_asr_model.currentText()
            if asr_text == "（禁用）":
                # 必须写 None 而不是空字符串：asr_model 是 Literal，
                # 空串不是合法取值，会让整份配置校验失败、服务起不来
                cc["asr_config"][ASR_ENGINE_KEY] = None
            else:
                cc["asr_config"][ASR_ENGINE_KEY] = asr_text
                if self._generic_asr_editors:
                    target = cc["asr_config"].get(asr_text)
                    if not isinstance(target, dict):
                        cc["asr_config"][asr_text] = {}
                        target = cc["asr_config"][asr_text]
                    new_vals = self._collect_generic_values(
                        self._generic_asr_editors, self._generic_asr_originals
                    )
                    for k, v in new_vals.items():
                        target[k] = v
                    self._log(f"[启动器]   ASR {asr_text}: 写入 {len(new_vals)} 个字段")

            # VAD 参数
            cc.setdefault("vad_config", {})
            vad_text = self.combo_vad_model.currentText()
            if vad_text == "（禁用）":
                cc["vad_config"][VAD_ENGINE_KEY] = None
            else:
                cc["vad_config"][VAD_ENGINE_KEY] = vad_text
                if self._generic_vad_editors:
                    target = cc["vad_config"].get(vad_text)
                    if not isinstance(target, dict):
                        cc["vad_config"][vad_text] = {}
                        target = cc["vad_config"][vad_text]
                    new_vals = self._collect_generic_values(
                        self._generic_vad_editors, self._generic_vad_originals
                    )
                    for k, v in new_vals.items():
                        target[k] = v
                    self._log(f"[启动器]   VAD {vad_text}: 写入 {len(new_vals)} 个字段")

            # 保护 GPT-SoVITS streaming_mode
            gsv = cc["tts_config"].get("gpt_sovits_tts")
            if isinstance(gsv, dict) and "streaming_mode" in gsv:
                gsv["streaming_mode"] = SingleQuotedScalarString("false")

            with open(conf_path, "w", encoding="utf-8") as f:
                self.yaml.dump(self.config, f)

            self._log(
                f"[启动器] ✔ 已保存 conf.yaml  "
                f"(角色={role_desc}, LLM={current_llm}, TTS={current_tts}, "
                f"ASR={asr_text}, VAD={vad_text})"
            )
            if current_llm == OLLAMA_PROVIDER_KEY:
                self._log(
                    f"[启动器]   Ollama: model={self.combo_model.currentText().strip()}, "
                    f"num_gpu={self.spin_num_gpu.value()}, "
                    f"num_ctx={self.spin_num_ctx.value()}, "
                    f"think={self.chk_think.isChecked()}, "
                    f"keep_alive={self._parse_keep_alive()}, "
                    f"temperature={round(self.spin_temperature.value(), 2)}"
                )
            self._update_active_voice_label()

            # 后端只会在进程启动时读一次 conf.yaml，正在运行的话改动不会生效
            if self.llm_process is not None and self.llm_process.poll() is None:
                self._log(
                    "[启动器] ⚠ Open-LLM-VTuber 正在运行，本次改动需"
                    "「停止」后重新启动才会生效"
                )
            # 已落盘，更新快照，关闭窗口时就不会再提示"有未保存改动"
            self._mark_config_saved()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入 conf.yaml 时出错：\n{e}")

    # ------------------------------------------------------------------
    # 启动 / 停止 Open-LLM-VTuber
    # ------------------------------------------------------------------

    def _start_llm(self):
        if self.llm_process is not None and self.llm_process.poll() is None:
            self._log("[启动器] ⚠ Open-LLM-VTuber 已经在运行")
            self._log("[启动器] ⚠ 若刚改过配置，需先「停止」再启动才会生效")
            return
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return

        # 启动前先把界面上的参数写入 conf.yaml。
        # 否则「改了模型/参数 → 直接点启动」不会生效：后端读的是磁盘上的旧配置。
        self._log("[启动器] 启动前自动保存配置...")
        self._save_config()

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["NO_COLOR"] = "1"

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            self.llm_process = subprocess.Popen(
                ["uv", "run", "run_server.py"],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                bufsize=1,
                creationflags=creationflags,
            )
        except FileNotFoundError:
            QMessageBox.critical(self, "启动失败",
                                 "找不到 `uv` 命令。请确认 uv 已安装并在 PATH 中。")
            return

        self._log(f"[启动器] ▶ 启动 Open-LLM-VTuber (PID={self.llm_process.pid})")
        self.btn_start_llm.setEnabled(False)
        self.btn_stop_llm.setEnabled(True)

        self._llm_reader_thread = threading.Thread(
            target=self._read_llm_output, daemon=True
        )
        self._llm_reader_thread.start()

        self._schedule_open_web_ui()

    # ------------------------------------------------------------------
    # 自动打开 Web 界面
    # ------------------------------------------------------------------

    def _on_open_browser_toggled(self, checked: bool):
        self.launcher_cfg["auto_open_browser"] = bool(checked)
        self._save_launcher_config()

    def _schedule_open_web_ui(self, timeout: int = 180):
        """起一个守护线程等 12393 就绪，然后通知主线程打开浏览器。"""
        if not self.chk_open_browser.isChecked():
            self._log("[启动器] （未勾选自动打开浏览器，跳过）")
            return
        self._web_open_token += 1
        token = self._web_open_token

        def _wait():
            for _ in range(timeout):
                if is_port_open(LLM_HOST, LLM_PORT):
                    if token == self._web_open_token:
                        self.web_ready_signal.emit()
                    return
                if self.llm_process is not None and self.llm_process.poll() is not None:
                    return  # 进程已退出，不再等待
                time.sleep(1)

        threading.Thread(target=_wait, daemon=True).start()

    def _on_web_ready(self):
        self._open_web_ui()

    def _open_web_ui(self):
        """用默认浏览器打开 Web 界面。"""
        if not is_port_open(LLM_HOST, LLM_PORT):
            self._log(f"[启动器] ⚠ 服务未在 {LLM_PORT} 端口运行，无法打开界面")
            return
        try:
            webbrowser.open(WEB_UI_URL)
            self._log(f"[启动器] ✔ 已用默认浏览器打开 {WEB_UI_URL}")
        except Exception as e:
            self._log(f"[启动器] ⚠ 打开浏览器失败：{e}（可手动访问 {WEB_UI_URL}）")

    def _read_llm_output(self):
        proc = self.llm_process
        if proc is None or proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                self.log_signal.emit(line.rstrip())
        except Exception as e:
            self.log_signal.emit(f"[读日志出错] {e}")
        code = proc.wait()
        self.llm_finished_signal.emit(code)

    def _ollama_model_in_use(self):
        """返回本项目当前配置的 Ollama 模型名；若当前 provider 不是 ollama 则返回空串。

        只卸载本项目自己配置的模型，不动其他程序加载的模型。
        """
        if not self.config:
            return ""
        try:
            cc = self.config.get("character_config", {})
            agent_cfg = cc.get("agent_config", {})
            provider = (
                agent_cfg.get("agent_settings", {})
                .get("basic_memory_agent", {})
                .get("llm_provider", "")
            )
            if provider != OLLAMA_PROVIDER_KEY:
                return ""
            model = (
                agent_cfg.get("llm_configs", {})
                .get(OLLAMA_PROVIDER_KEY, {})
                .get("model", "")
            )
            return str(model).strip()
        except Exception:
            return ""

    def _unload_ollama_best_effort(self, wait: bool = False):
        """让 Ollama 卸载本项目正在使用的模型。

        为什么要由启动器主动做：停止服务用的是 `taskkill /F`，Windows 强制终止不会执行
        Python 的 atexit，后端注册的 ollama_llm.cleanup() 永远不会跑；而 keep_alive=-1
        又让 Ollama 自己不过期，模型就会一直驻留显存。

        必须在进程被杀**之后**调用：否则后端仍存活，预加载或下一轮对话会立刻把它拉回来。
        `wait=True` 用于退出流程——daemon 线程会随进程结束被掐掉，必须等它把请求发出去。
        失败只记日志，绝不弹窗、绝不抛出，避免影响退出流程。
        """
        model = self._ollama_model_in_use()
        if not model:
            return  # 当前不是 ollama provider，不干预
        if not is_port_open(OLLAMA_HOST, OLLAMA_PORT):
            self._log("[启动器] Ollama 未运行，跳过卸载")
            return

        def _worker():
            self.log_signal.emit(f"[启动器] ⏏ 正在卸载 Ollama 模型：{model}")
            ok, msg = unload_ollama_model(model)
            if ok:
                self.log_signal.emit(f"[启动器] ✔ 已卸载 Ollama 模型：{model}")
            else:
                self.log_signal.emit(f"[启动器] ⚠ 卸载 Ollama 模型失败：{msg}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        if wait:
            # 关窗退出时用：不阻塞太久，但要确保请求已发出
            t.join(timeout=8.0)

    def _stop_llm(self):
        if self.llm_process is None or self.llm_process.poll() is not None:
            return
        self._web_open_token += 1   # 让等待中的自动打开线程失效
        self._log("[启动器] ⏹ 正在停止 Open-LLM-VTuber...")
        pid = self.llm_process.pid
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True)
        except Exception as e:
            self._log(f"[启动器] taskkill 失败：{e}")

        # 进程已杀，再卸载模型（顺序不能反）
        self._unload_ollama_best_effort()

    def _on_llm_finished(self, exit_code):
        self._log(f"[启动器] ■ Open-LLM-VTuber 进程结束（exit_code={exit_code}）")
        self.llm_process = None
        self.btn_start_llm.setEnabled(True)
        self.btn_stop_llm.setEnabled(False)
        # 后端自行退出（崩溃/被外部结束）时的兜底。若它是正常退出，
        # atexit 里已经卸过一次，这里重复调用是无害的。
        self._unload_ollama_best_effort()

    # ------------------------------------------------------------------
    # 启动 / 停止 GPT-SoVITS
    # ------------------------------------------------------------------

    def _start_gsv(self):
        if self.gsv_process is not None and self.gsv_process.poll() is None:
            self._log("[启动器] ⚠ GPT-SoVITS 已经在运行")
            return

        gsv_root = self.launcher_cfg.get("gpt_sovits_root")
        if not gsv_root or not Path(gsv_root).is_dir():
            QMessageBox.warning(self, "未设置 GPT-SoVITS 目录",
                                "请先在「GPT-SoVITS」区域选择根目录。")
            return

        gsv_dir = Path(gsv_root)
        bat_path = gsv_dir / DEFAULT_GPT_BAT
        if not bat_path.exists():
            QMessageBox.critical(self, "启动失败",
                                 f"找不到启动脚本：\n{bat_path}")
            return

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_CONSOLE

        try:
            self.gsv_process = subprocess.Popen(
                [str(bat_path)],
                cwd=str(gsv_dir),
                creationflags=creationflags,
            )
        except Exception as e:
            QMessageBox.critical(self, "启动失败", f"启动 GPT-SoVITS 时出错：\n{e}")
            return

        self._log(f"[启动器] ▶ 启动 GPT-SoVITS (PID={self.gsv_process.pid}) → {bat_path.name}")
        self.btn_start_gsv.setEnabled(False)
        self.btn_stop_gsv.setEnabled(True)

        def _wait():
            try:
                code = self.gsv_process.wait()
            except Exception:
                code = -1
            self.gsv_finished_signal.emit(code)

        threading.Thread(target=_wait, daemon=True).start()

    def _stop_gsv(self):
        if self.gsv_process is None or self.gsv_process.poll() is not None:
            return
        self._log("[启动器] ⏹ 正在停止 GPT-SoVITS...")
        pid = self.gsv_process.pid
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True)
        except Exception as e:
            self._log(f"[启动器] taskkill 失败：{e}")

    def _on_gsv_finished(self, exit_code):
        self._log(f"[启动器] ■ GPT-SoVITS 进程结束（exit_code={exit_code}）")
        self.gsv_process = None
        self.btn_start_gsv.setEnabled(True)
        self.btn_stop_gsv.setEnabled(False)

    # ------------------------------------------------------------------
    # 一键启动
    # ------------------------------------------------------------------

    def _oneclick_start(self):
        self.btn_oneclick.setEnabled(False)
        # 启动前先把界面上的参数写入 conf.yaml。
        # 必须在主线程做：_save_config 会读写 Qt 控件，跨线程操作不安全。
        self._log("[启动器] 一键启动：先保存当前配置...")
        self._save_config()
        threading.Thread(target=self._oneclick_worker, daemon=True).start()

    def _oneclick_worker(self):
        try:
            self.oneclick_progress_signal.emit("[启动器] ★ 一键启动：检查 Ollama...")
            if not is_port_open(OLLAMA_HOST, OLLAMA_PORT):
                self.oneclick_progress_signal.emit(
                    "[启动器] ⚠ Ollama 未运行。请手动启动 Ollama 服务后重试。"
                )
                return
            self.oneclick_progress_signal.emit("[启动器] ✔ Ollama 在线")

            gsv_root = self.launcher_cfg.get("gpt_sovits_root")
            gsv_started_now = False
            if not gsv_root or not Path(gsv_root).is_dir():
                self.oneclick_progress_signal.emit(
                    "[启动器] ⚠ 未设置 GPT-SoVITS 根目录，跳过启动 GPT-SoVITS。"
                )
            else:
                if is_port_open(GPT_SOVITS_HOST, GPT_SOVITS_PORT):
                    self.oneclick_progress_signal.emit("[启动器] ✔ GPT-SoVITS 已在线")
                else:
                    self.oneclick_progress_signal.emit("[启动器] ★ 启动 GPT-SoVITS...")
                    self._start_gsv_threadsafe()
                    gsv_started_now = True

                    self.oneclick_progress_signal.emit(
                        "[启动器] ⏳ 等待 GPT-SoVITS API 就绪（最多 120 秒）..."
                    )
                    ok = False
                    for _ in range(120):
                        if is_port_open(GPT_SOVITS_HOST, GPT_SOVITS_PORT):
                            ok = True
                            break
                        time.sleep(1)
                    if not ok:
                        self.oneclick_progress_signal.emit(
                            "[启动器] ✘ GPT-SoVITS API 在 120 秒内未就绪，中止一键启动。"
                        )
                        return
                    self.oneclick_progress_signal.emit("[启动器] ✔ GPT-SoVITS 就绪")

            if gsv_started_now:
                self._auto_apply_saved_weights()

            if self.llm_process is not None and self.llm_process.poll() is None:
                self.oneclick_progress_signal.emit(
                    "[启动器] ✔ Open-LLM-VTuber 已在运行"
                )
                self.web_ready_signal.emit()   # 已在运行也打开一次界面
            else:
                self.oneclick_progress_signal.emit("[启动器] ★ 启动 Open-LLM-VTuber...")
                self._start_llm_threadsafe()

                self.oneclick_progress_signal.emit(
                    "[启动器] ⏳ 等待 Open-LLM-VTuber 就绪（最多 120 秒）..."
                )
                ok = False
                for _ in range(120):
                    if is_port_open(LLM_HOST, LLM_PORT):
                        ok = True
                        break
                    if self.llm_process is not None and self.llm_process.poll() is not None:
                        self.oneclick_progress_signal.emit(
                            "[启动器] ✘ Open-LLM-VTuber 进程意外退出，中止一键启动。"
                        )
                        return
                    time.sleep(1)
                if not ok:
                    self.oneclick_progress_signal.emit(
                        "[启动器] ✘ Open-LLM-VTuber 在 120 秒内未就绪，中止一键启动。"
                    )
                    return
                self.oneclick_progress_signal.emit("[启动器] ✔ Open-LLM-VTuber 就绪")
                if self.chk_open_browser.isChecked():
                    self.web_ready_signal.emit()

            self.oneclick_progress_signal.emit("[启动器] ✔ 一键启动流程完成")
        finally:
            self.oneclick_done_signal.emit()

    def _auto_apply_saved_weights(self):
        saved = self.launcher_cfg.get("gpt_sovits_model", {})
        gpt_name = saved.get("gpt", "")
        sovits_name = saved.get("sovits", "")
        if not gpt_name or not sovits_name:
            return

        root = self._current_gsv_root()
        if not root:
            return

        gpt_path = find_weight_path(root, GPT_WEIGHTS_PREFIX, gpt_name)
        sovits_path = find_weight_path(root, SOVITS_WEIGHTS_PREFIX, sovits_name)
        if not gpt_path or not sovits_path:
            self.oneclick_progress_signal.emit(
                "[启动器] ⚠ 上次记录的权重文件找不到，跳过自动切换"
            )
            return

        self.oneclick_progress_signal.emit(
            f"[启动器] ⏳ 自动应用上次记录的声音模型：{gpt_name} / {sovits_name}"
        )

        ok1, msg1 = gpt_sovits_set_weights("set_gpt_weights", gpt_path)
        if not ok1:
            self.oneclick_progress_signal.emit(f"[启动器] ⚠ GPT 权重自动切换失败：{msg1}")
            return
        ok2, msg2 = gpt_sovits_set_weights("set_sovits_weights", sovits_path)
        if not ok2:
            self.oneclick_progress_signal.emit(f"[启动器] ⚠ SoVITS 权重自动切换失败：{msg2}")
            return
        self.oneclick_progress_signal.emit("[启动器] ✔ 声音模型自动切换完成")

    def _start_gsv_threadsafe(self):
        gsv_root = self.launcher_cfg.get("gpt_sovits_root")
        if not gsv_root or not Path(gsv_root).is_dir():
            return
        gsv_dir = Path(gsv_root)
        bat_path = gsv_dir / DEFAULT_GPT_BAT
        if not bat_path.exists():
            self.oneclick_progress_signal.emit(f"[启动器] ✘ 找不到 {bat_path}")
            return

        creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        try:
            self.gsv_process = subprocess.Popen(
                [str(bat_path)],
                cwd=str(gsv_dir),
                creationflags=creationflags,
            )
            self.oneclick_progress_signal.emit(
                f"[启动器] ▶ GPT-SoVITS 进程已启动 (PID={self.gsv_process.pid})"
            )

            def _wait():
                try:
                    code = self.gsv_process.wait()
                except Exception:
                    code = -1
                self.gsv_finished_signal.emit(code)
            threading.Thread(target=_wait, daemon=True).start()
        except Exception as e:
            self.oneclick_progress_signal.emit(f"[启动器] ✘ 启动 GPT-SoVITS 失败：{e}")

    def _start_llm_threadsafe(self):
        if not self.project_root:
            return
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["NO_COLOR"] = "1"
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self.llm_process = subprocess.Popen(
                ["uv", "run", "run_server.py"],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                bufsize=1,
                creationflags=creationflags,
            )
            self.oneclick_progress_signal.emit(
                f"[启动器] ▶ Open-LLM-VTuber 进程已启动 (PID={self.llm_process.pid})"
            )
            self._llm_reader_thread = threading.Thread(
                target=self._read_llm_output, daemon=True
            )
            self._llm_reader_thread.start()
        except Exception as e:
            self.oneclick_progress_signal.emit(f"[启动器] ✘ 启动 Open-LLM-VTuber 失败：{e}")

    # ------------------------------------------------------------------
    # 全部停止
    # ------------------------------------------------------------------

    def _stop_all(self):
        llm_running = self.llm_process is not None and self.llm_process.poll() is None
        gsv_running = self.gsv_process is not None and self.gsv_process.poll() is None

        if not llm_running and not gsv_running:
            self._log("[启动器] （当前没有运行中的服务）")
            return

        running_list = []
        if llm_running:
            running_list.append("Open-LLM-VTuber")
        if gsv_running:
            running_list.append("GPT-SoVITS")
        reply = QMessageBox.question(
            self, "确认全部停止",
            "确定要停止以下服务吗？\n\n  · " + "\n  · ".join(running_list),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            self._log("[启动器] （已取消全部停止）")
            return

        self._log("[启动器] ■ 全部停止...")
        if llm_running:
            self._stop_llm()
        if gsv_running:
            self._stop_gsv()

    # ------------------------------------------------------------------
    # 关闭窗口
    # ------------------------------------------------------------------

    def _terminate_sync(self, proc):
        if proc is None:
            return
        try:
            if proc.poll() is not None:
                return
        except Exception:
            return
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True, timeout=10
            )
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _ask_unsaved_changes(self) -> str:
        """有未保存改动时询问。返回 'save' / 'discard' / 'cancel'。

        QMessageBox 的标准按钮在中文系统上仍可能显示英文，所以显式加中文按钮。
        """
        pages = self._unsaved_pages()
        detail = "\n".join(f"  · {p}" for p in pages)
        box = QMessageBox(self)
        box.setWindowTitle("有未保存的改动")
        box.setIcon(QMessageBox.Warning)
        box.setText("以下页面还有改动没有保存：")
        box.setInformativeText(f"{detail}\n\n要保存后再退出吗？")
        btn_save = box.addButton("保存并退出", QMessageBox.AcceptRole)
        box.addButton("丢弃退出", QMessageBox.DestructiveRole)
        btn_cancel = box.addButton("取消", QMessageBox.RejectRole)
        box.setDefaultButton(btn_save)
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_save:
            return "save"
        if clicked is btn_cancel:
            return "cancel"
        return "discard"

    def closeEvent(self, event):
        # 先处理未保存的改动（与是否有服务在运行无关）
        if self._has_unsaved_changes():
            choice = self._ask_unsaved_changes()
            if choice == "cancel":
                event.ignore()
                return
            if choice == "save":
                self._save_all()
                if self._has_unsaved_changes():
                    # 保存失败（例如写文件出错），不要静默退出把改动丢掉
                    event.ignore()
                    return

        llm_running = self.llm_process is not None and self.llm_process.poll() is None
        gsv_running = self.gsv_process is not None and self.gsv_process.poll() is None

        if not llm_running and not gsv_running:
            event.accept()
            return

        running_list = []
        if llm_running:
            running_list.append("Open-LLM-VTuber")
        if gsv_running:
            running_list.append("GPT-SoVITS")

        reply = QMessageBox.question(
            self, "确认退出",
            "以下服务仍在运行：\n\n  · " + "\n  · ".join(running_list) +
            "\n\n退出前会自动停止它们。是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            event.ignore()
            return

        self._log("[启动器] ■ 退出前停止所有服务...")
        if llm_running:
            self._terminate_sync(self.llm_process)
            self.llm_process = None
            # 强杀不会触发后端的 atexit 卸载，这里同步补一次（wait=True：
            # 窗口关闭后进程结束会掐掉 daemon 线程，必须等请求发出去）
            self._unload_ollama_best_effort(wait=True)
        if gsv_running:
            self._terminate_sync(self.gsv_process)
            self.gsv_process = None

        event.accept()

    # ------------------------------------------------------------------
    # 状态轮询
    # ------------------------------------------------------------------

    def _poll_status(self):
        ollama_up = is_port_open(OLLAMA_HOST, OLLAMA_PORT)
        gsv_up = is_port_open(GPT_SOVITS_HOST, GPT_SOVITS_PORT)
        llm_up = self.llm_process is not None and self.llm_process.poll() is None
        self.status_signal.emit(ollama_up, gsv_up, llm_up)
        self.gpu_signal.emit(query_gpu_info())

    def _on_status_update(self, ollama_up: bool, gsv_up: bool, llm_up: bool):
        def style(lbl: QLabel, up: bool, text: str):
            color = "#2ecc71" if up else "#888888"
            lbl.setText(f"● {text}")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")

        style(self.lbl_ollama, ollama_up, "Ollama")
        style(self.lbl_gsv, gsv_up, "GPT-SoVITS")
        style(self.lbl_llm, llm_up, "Open-LLM-VTuber")

    def _on_gpu_update(self, text: str):
        self.lbl_gpu.setText(text)

    def _on_oneclick_done(self):
        self.btn_oneclick.setEnabled(True)
        gsv_running = self.gsv_process is not None and self.gsv_process.poll() is None
        llm_running = self.llm_process is not None and self.llm_process.poll() is None
        self.btn_start_gsv.setEnabled(not gsv_running)
        self.btn_stop_gsv.setEnabled(gsv_running)
        self.btn_start_llm.setEnabled(not llm_running)
        self.btn_stop_llm.setEnabled(llm_running)

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------

    def _log(self, text: str):
        clean = strip_ansi(text)
        if clean.startswith("[需要主线程启动 GPT-SoVITS]"):
            return
        self.log_view.append(clean)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())


# ----------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------

def _force_foreground(win: "LauncherWindow"):
    try:
        win.raise_()
        win.activateWindow()
        if sys.platform == "win32":
            import ctypes
            hwnd = int(win.winId())
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    QTimer.singleShot(150, lambda: (win.raise_(), win.activateWindow()))


def _report_startup_failure(message: str):
    """启动失败时给出可见提示。

    静默模式（pythonw）下没有控制台，若不弹窗用户会看到「双击没反应」。
    """
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, message, "Open-LLM-VTuber 启动器", 0x10  # MB_ICONERROR
        )
    except Exception:
        pass


def main():
    try:
        app = QApplication(sys.argv)
        win = LauncherWindow()
        win.show()
        _force_foreground(win)
    except Exception:
        import traceback
        detail = traceback.format_exc()
        # 有控制台时也打印一份，方便 debug 模式查看
        print(detail, file=sys.stderr)
        _report_startup_failure(
            "启动器启动失败：\n\n"
            + detail.strip().splitlines()[-1]
            + "\n\n完整信息：\n"
            + detail
        )
        sys.exit(1)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()