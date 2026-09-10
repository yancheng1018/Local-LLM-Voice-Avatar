"""
Open-LLM-VTuber 启动器 v2.1
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

标签页顺序：服务 → 模型 → 角色 → Live2D → LLM → TTS → ASR / VAD

v2.1 新增：
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
from pathlib import Path

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
GPT_SOVITS_HOST = "127.0.0.1"
GPT_SOVITS_PORT = 9880
GPT_SOVITS_BASE = f"http://{GPT_SOVITS_HOST}:{GPT_SOVITS_PORT}"
LLM_HOST = "127.0.0.1"
LLM_PORT = 12393

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


class VoiceDialog(QDialog):
    """新建声音模型：选权重对 + 参考音频 + 提示文本。"""

    def __init__(self, parent, gpt_items: list, sovits_items: list):
        super().__init__(parent)
        self.setWindowTitle("新建声音模型")
        self.resize(620, 340)

        form = QFormLayout(self)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("如 加藤惠（将作为 voices/ 下的文件夹名）")
        form.addRow("名称：", self.edit_name)

        self.combo_gpt = QComboBox()
        self.combo_gpt.addItems(gpt_items)
        form.addRow("GPT 权重：", self.combo_gpt)

        self.combo_sovits = QComboBox()
        self.combo_sovits.addItems(sovits_items)
        form.addRow("SoVITS 权重：", self.combo_sovits)

        audio_row = QHBoxLayout()
        self.edit_audio = QLineEdit()
        self.edit_audio.setPlaceholderText("参考音频文件路径")
        btn_pick = QPushButton("选择...")
        btn_pick.clicked.connect(self._pick_audio)
        audio_row.addWidget(self.edit_audio, stretch=1)
        audio_row.addWidget(btn_pick)
        form.addRow("参考音频：", audio_row)

        self.edit_prompt = QPlainTextEdit()
        self.edit_prompt.setPlaceholderText("参考音频中说的原话（GPT-SoVITS 需要它来对齐音色）")
        self.edit_prompt.setMaximumHeight(80)
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

    def _pick_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择参考音频", "",
            "音频文件 (*.wav *.mp3 *.flac *.ogg *.m4a);;所有文件 (*)"
        )
        if path:
            self.edit_audio.setText(path)

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

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Open-LLM-VTuber 启动器 v2.1")
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
        self._model_dict_entries = []

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
        tab_preset_layout.addWidget(sel_box)

        # 预设区
        preset_box = QGroupBox("配置预设")
        preset_inner = QVBoxLayout(preset_box)
        self.preset_list = QListWidget()
        self.preset_list.itemDoubleClicked.connect(self._apply_preset)
        preset_inner.addWidget(self.preset_list)
        preset_btn_row = QHBoxLayout()
        btn_save_preset = QPushButton("保存当前为预设")
        btn_apply_preset = QPushButton("应用")
        btn_delete_preset = QPushButton("删除")
        btn_save_preset.clicked.connect(self._save_preset)
        btn_apply_preset.clicked.connect(
            lambda: self._apply_preset(self.preset_list.currentItem())
        )
        btn_delete_preset.clicked.connect(self._delete_preset)
        preset_btn_row.addWidget(btn_save_preset)
        preset_btn_row.addWidget(btn_apply_preset)
        preset_btn_row.addWidget(btn_delete_preset)
        preset_inner.addLayout(preset_btn_row)
        tab_preset_layout.addWidget(preset_box)

        tab_preset_layout.addStretch(1)

        self.tabs.addTab(tab_preset, "模型")

        # ── Tab 3: 角色 ──
        tab_char = QWidget()
        tab_char_layout = QHBoxLayout(tab_char)

        # 左：角色列表
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

        char_list_layout.addStretch(1)
        tab_char_layout.addWidget(char_list_box, stretch=1)

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
            ("character_name", "角色名", "界面上显示的 AI 名称"),
            ("human_name", "用户名", "界面上显示的你的称呼"),
        ]:
            w = QLineEdit()
            w.setMinimumWidth(200)
            w.setToolTip(tip)
            info_form.addRow(f"{label}：", w)
            self.char_edit_fields[key] = w
        char_edit_vbox.addWidget(info_box)

        # ── 形象 ──
        look_box = QGroupBox("形象")
        look_form = QFormLayout(look_box)

        # Live2D 模型：下拉 + 刷新
        w_l2d = EditableCombo()
        w_l2d.setToolTip("从 live2d-models/ 与 model_dict.json 自动扫描")
        row_l2d = QHBoxLayout()
        row_l2d.addWidget(w_l2d, stretch=1)
        btn_refresh_l2d = QPushButton("↻")
        btn_refresh_l2d.setFixedWidth(32)
        btn_refresh_l2d.setToolTip("刷新 Live2D 模型列表")
        btn_refresh_l2d.clicked.connect(self._populate_live2d_combo)
        row_l2d.addWidget(btn_refresh_l2d)
        look_form.addRow("Live2D 模型：", row_l2d)
        self.char_edit_fields["live2d_model_name"] = w_l2d

        # 头像：下拉 + 刷新 + 导入
        w_avatar = EditableCombo()
        w_avatar.setToolTip("从 avatars/ 目录自动扫描，或点「导入」添加图片")
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
            ("conf_name", "conf_name", "角色配置文件名（不带 .yaml），启动器选中的就是它"),
            ("conf_uid", "conf_uid", "角色唯一标识，留空保存时自动填为 名称_001"),
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

        # ── Tab 4: Live2D（模型管理 + 静态预览）──
        tab_l2d = QWidget()
        tab_l2d_layout = QHBoxLayout(tab_l2d)

        # 左：模型条目管理
        l2d_box = QGroupBox("Live2D 模型（model_dict.json）")
        l2d_inner = QVBoxLayout(l2d_box)
        self.l2d_list = QListWidget()
        self.l2d_list.currentRowChanged.connect(self._on_l2d_selected)
        l2d_inner.addWidget(self.l2d_list)
        l2d_btn_row = QHBoxLayout()
        btn_l2d_scan = QPushButton("从 live2d-models/ 扫描新模型")
        btn_l2d_del = QPushButton("删除条目")
        btn_l2d_save = QPushButton("保存到 model_dict.json")
        btn_l2d_scan.clicked.connect(self._scan_new_live2d_models)
        btn_l2d_del.clicked.connect(self._delete_model_dict_entry)
        btn_l2d_save.clicked.connect(self._save_model_dict)
        l2d_btn_row.addWidget(btn_l2d_scan)
        l2d_btn_row.addWidget(btn_l2d_del)
        l2d_btn_row.addWidget(btn_l2d_save)
        l2d_inner.addLayout(l2d_btn_row)
        tab_l2d_layout.addWidget(l2d_box, stretch=1)

        # 右：静态预览（显示模型自带贴图，无渲染开销）
        preview_box = QGroupBox("预览（模型贴图静态预览）")
        preview_layout = QVBoxLayout(preview_box)
        self.l2d_preview = QLabel("（选择左侧模型查看）")
        self.l2d_preview.setFixedSize(340, 340)
        self.l2d_preview.setAlignment(Qt.AlignCenter)
        self.l2d_preview.setStyleSheet("border: 1px solid #ccc; background: #fafafa;")
        preview_layout.addWidget(self.l2d_preview, alignment=Qt.AlignCenter)
        l2d_tip = QLabel("提示：Live2D 为骨骼动画，此处显示的是模型自带贴图；\n"
                         "实际效果以前端页面渲染为准。")
        l2d_tip.setStyleSheet("color: #888;")
        preview_layout.addWidget(l2d_tip)
        preview_layout.addStretch(1)
        tab_l2d_layout.addWidget(preview_box, stretch=0)

        self.tabs.addTab(tab_l2d, "Live2D")

        # ── Tab 3: LLM ──
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
        self.tabs.addTab(tab_llm, "LLM")

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

        voice_btn_row = QHBoxLayout()
        self.btn_apply_voice = QPushButton("应用声音（切权重 + 写配置）")
        self.btn_apply_voice.clicked.connect(self._apply_voice_model)
        btn_new_voice = QPushButton("新建声音...")
        btn_new_voice.setToolTip("选择权重对 + 参考音频，创建新的声音模型")
        btn_new_voice.clicked.connect(self._new_voice_model)
        voice_btn_row.addWidget(self.btn_apply_voice)
        voice_btn_row.addWidget(btn_new_voice)
        gsv_layout.addRow("", voice_btn_row)

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

        gpt_w_row = QHBoxLayout()
        self.combo_gpt_weight = QComboBox()
        self.combo_gpt_weight.setMinimumWidth(280)
        btn_refresh_gpt = QPushButton("↻")
        btn_refresh_gpt.setFixedWidth(32)
        btn_refresh_gpt.setToolTip("刷新 GPT 权重列表")
        btn_refresh_gpt.clicked.connect(self._refresh_gpt_weights)
        gpt_w_row.addWidget(self.combo_gpt_weight, stretch=1)
        gpt_w_row.addWidget(btn_refresh_gpt)
        gsv_layout.addRow("GPT 模型(.ckpt)：", gpt_w_row)

        sovits_w_row = QHBoxLayout()
        self.combo_sovits_weight = QComboBox()
        self.combo_sovits_weight.setMinimumWidth(280)
        btn_refresh_sovits = QPushButton("↻")
        btn_refresh_sovits.setFixedWidth(32)
        btn_refresh_sovits.setToolTip("刷新 SoVITS 权重列表")
        btn_refresh_sovits.clicked.connect(self._refresh_sovits_weights)
        sovits_w_row.addWidget(self.combo_sovits_weight, stretch=1)
        sovits_w_row.addWidget(btn_refresh_sovits)
        gsv_layout.addRow("SoVITS 模型(.pth)：", sovits_w_row)

        apply_row = QHBoxLayout()
        self.btn_apply_weights = QPushButton("应用模型到 GPT-SoVITS")
        self.btn_apply_weights.clicked.connect(self._apply_weights)
        self.lbl_current_weights = QLabel("当前：(未知)")
        self.lbl_current_weights.setStyleSheet("color: #666;")
        apply_row.addWidget(self.btn_apply_weights)
        apply_row.addWidget(self.lbl_current_weights, stretch=1)
        gsv_layout.addRow("", apply_row)

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
        self.combo_tts.currentTextChanged.connect(self._on_tts_model_changed)
        self.combo_asr_model.currentTextChanged.connect(self._on_asr_model_changed)
        self.combo_vad_model.currentTextChanged.connect(self._on_vad_model_changed)

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
        self._refresh_gpt_weights(silent=True)
        self._refresh_sovits_weights(silent=True)
        self._restore_saved_weights_selection()

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
        self._populate_model_dict_list()
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
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        c = self.yaml.load(fp) or {}
                    char_name = c.get("character_name") or stem
                    avatar = c.get("avatar") or ""
                except Exception:
                    pass
                display = f"{char_name} ({stem})"
                self._character_entries.append((display, stem, char_name, avatar))

        for display, _, _, _ in self._character_entries:
            self.combo_character.addItem(display)

        current = self.config.get("character_config", {}).get("conf_name", "")
        matched = False
        for i, (_, stem, _, _) in enumerate(self._character_entries):
            if stem == current:
                self.combo_character.setCurrentIndex(i)
                matched = True
                break

        if not matched and current:
            self._log(f"[启动器] ⚠ 当前角色 conf_name='{current}' 未在 {alts_dir}/ 目录中找到对应文件")
        self._log(f"[启动器] 发现角色 {len(self._character_entries)} 个")

        self._on_character_changed(self.combo_character.currentIndex())

    def _on_character_changed(self, idx):
        if idx < 0 or idx >= len(self._character_entries):
            self.avatar_label.setPixmap(QPixmap())
            self.avatar_label.setText("无头像")
            for w in self.char_edit_fields.values():
                w.setText("")
            self.char_edit_persona.setPlainText("")
            return

        _, stem, char_name, avatar = self._character_entries[idx]

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
        chars_dir = self._get_alts_dir()
        char_file = chars_dir / f"{stem}.yaml"
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
        name, ok = QInputDialog.getText(self, "新建角色", "角色 conf_name（英文标识）：")
        if not ok or not name.strip():
            return
        name = name.strip()
        chars_dir = self._get_alts_dir()
        target = chars_dir / f"{name}.yaml"
        if target.exists():
            QMessageBox.warning(self, "已存在", f"角色文件已存在：{target.name}")
            return

        template = {
            "character_config": {
                "conf_name": name,
                "conf_uid": f"{name}_001",
                "live2d_model_name": "",
                "character_name": name,
                "human_name": "Human",
                "avatar": "",
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
            for i, (_, stem, _, _) in enumerate(self._character_entries):
                if stem == name:
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

        _, stem, _, _ = self._character_entries[idx]
        chars_dir = self._get_alts_dir()
        char_file = chars_dir / f"{stem}.yaml"

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

        # 内部标识留空时自动补全，避免写出空值导致启动失败。
        # character_name 不补：应用层已有「缺失时回退为文件名」的处理，
        # 补写只会往老角色文件里添加冗余字段。
        if not cc.get("conf_name"):
            cc["conf_name"] = stem
        if not cc.get("conf_uid"):
            cc["conf_uid"] = f"{cc['conf_name']}_001"

        cc["persona_prompt"] = self.char_edit_persona.toPlainText()
        char_data["character_config"] = cc

        try:
            with open(char_file, "w", encoding="utf-8") as f:
                self.yaml.dump(char_data, f)
            self._log(f"[启动器] ✔ 已保存角色：{stem}")
            # 刷新列表但保持选中
            old_stem = stem
            self._populate_characters()
            for i, (_, s, _, _) in enumerate(self._character_entries):
                if s == old_stem:
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

        _, stem, char_name, _ = self._character_entries[idx]
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
        w.addItems(self._scan_live2d_model_names())
        if current:
            w.setText(current)

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
        w.addItems(sorted(set(names)))
        if current:
            w.setText(current)

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

    def _populate_model_dict_list(self):
        self._model_dict_entries = self._load_model_dict()
        self._refresh_l2d_list()

    def _refresh_l2d_list(self):
        self.l2d_list.clear()
        for item in self._model_dict_entries:
            name = item.get("name", "（未命名）")
            url = item.get("url", "")
            self.l2d_list.addItem(f"{name}  →  {url}")

    def _on_l2d_selected(self, row: int):
        """选中 Live2D 条目时，从模型文件夹找贴图做静态预览。"""
        if row < 0 or row >= len(self._model_dict_entries):
            self.l2d_preview.setPixmap(QPixmap())
            self.l2d_preview.setText("（选择左侧模型查看）")
            return
        entry = self._model_dict_entries[row]
        url = entry.get("url", "")
        name = entry.get("name", "")
        model_dir = None
        if url:
            rel = url.lstrip("/")
            p = self.project_root / rel
            model_dir = p.parent if p.exists() else None
        if model_dir is None:
            cand = self.project_root / "live2d-models" / name
            if cand.is_dir():
                model_dir = cand
        if model_dir is None or not model_dir.is_dir():
            self.l2d_preview.setPixmap(QPixmap())
            self.l2d_preview.setText("（未找到模型文件夹）")
            return

        texture = next(iter(sorted(model_dir.rglob("texture_*.png"))), None)
        if texture is None:
            texture = next(iter(sorted(model_dir.rglob("*.png"))), None)
        if texture is None:
            self.l2d_preview.setPixmap(QPixmap())
            self.l2d_preview.setText("（无贴图文件）")
            return
        pix = QPixmap(str(texture))
        if pix.isNull():
            self.l2d_preview.setText("（贴图无法读取）")
            return
        self.l2d_preview.setText("")
        self.l2d_preview.setPixmap(
            pix.scaled(340, 340, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _scan_new_live2d_models(self):
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        models_dir = self.project_root / "live2d-models"
        if not models_dir.is_dir():
            QMessageBox.warning(self, "未找到目录", f"未找到：{models_dir}")
            return
        known = {item.get("name") for item in self._model_dict_entries}
        new_dirs = sorted(
            d for d in models_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name not in known
        )
        if not new_dirs:
            QMessageBox.information(self, "扫描完成", "没有发现新模型。")
            return

        for d in new_dirs:
            # 在模型目录中寻找 .model3.json 作为入口文件
            model_file = next(iter(d.rglob("*.model3.json")), None)
            if model_file is not None:
                url = "/" + model_file.relative_to(self.project_root).as_posix()
            else:
                url = f"/live2d-models/{d.name}/{d.name}.model3.json"
            self._model_dict_entries.append({
                "name": d.name,
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
        self._refresh_l2d_list()
        names = "\n".join(d.name for d in new_dirs)
        QMessageBox.information(
            self, "扫描完成",
            f"发现 {len(new_dirs)} 个新模型：\n{names}\n\n"
            "点击「保存到 model_dict.json」生效。"
        )
        self._log(f"[启动器] ✔ 扫描到 {len(new_dirs)} 个新 Live2D 模型")

    def _delete_model_dict_entry(self):
        idx = self.l2d_list.currentRow()
        if idx < 0 or idx >= len(self._model_dict_entries):
            QMessageBox.warning(self, "未选择", "请先在列表中选择要删除的模型条目。")
            return
        name = self._model_dict_entries[idx].get("name", idx)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定从 model_dict.json 中删除「{name}」吗？\n（不会删除 live2d-models/ 下的模型文件夹）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        del self._model_dict_entries[idx]
        self.l2d_list.takeItem(idx)
        self._log(f"[启动器] 已移除条目「{name}」，点击「保存到 model_dict.json」生效")

    def _save_model_dict(self):
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        p = self._model_dict_path()
        try:
            if p.exists():
                shutil.copy2(p, p.with_suffix(".json.bak"))
            p.write_text(
                json.dumps(self._model_dict_entries, ensure_ascii=False, indent=4),
                encoding="utf-8",
            )
            self._log(
                f"[启动器] ✔ 已保存 model_dict.json（{len(self._model_dict_entries)} 个条目）"
            )
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入 model_dict.json 失败：\n{e}")
            return
        # 模型列表变化后，同步刷新角色编辑器的下拉
        self._populate_live2d_combo()

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
            self._refresh_gpt_weights(silent=True)
            self._refresh_sovits_weights(silent=True)
            self._restore_saved_weights_selection()
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

    def _apply_voice_model(self):
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        name = self.combo_voice.currentText().strip()
        if not name:
            QMessageBox.warning(self, "未选择声音", "请先选择一个声音模型。")
            return
        voice_dir = self._voices_dir() / name
        meta = self._load_voice(name)
        if not meta:
            QMessageBox.warning(self, "元数据缺失",
                                f"未找到 {voice_dir / 'voice.json'}\n无法应用该声音模型。")
            return

        # 1) 找到参考音频
        ref_audio = next(iter(sorted(voice_dir.glob("ref.*"))), None)
        if ref_audio is None:
            QMessageBox.warning(self, "缺少参考音频",
                                f"{voice_dir} 中没有 ref.* 音频文件。")
            return

        # 2) 权重（可选：voices 里没写就当纯参考音频切换）
        root = self._current_gsv_root()
        gpt_text = meta.get("gpt_weight", "")
        sovits_text = meta.get("sovits_weight", "")
        gpt_path = sovits_path = None
        if gpt_text and sovits_text and root:
            gpt_path = find_weight_path(root, GPT_WEIGHTS_PREFIX, gpt_text)
            sovits_path = find_weight_path(root, SOVITS_WEIGHTS_PREFIX, sovits_text)

        # 3) 写回 conf.yaml
        cc = self.config.setdefault("character_config", {})
        gsv = cc.setdefault("tts_config", {}).setdefault("gpt_sovits_tts", {})
        gsv["ref_audio_path"] = str(ref_audio)
        gsv["prompt_text"] = meta.get("prompt_text", "")
        gsv["prompt_lang"] = meta.get("prompt_lang", "zh")
        gsv["text_lang"] = meta.get("text_lang", "zh")
        gsv["streaming_mode"] = SingleQuotedScalarString("false")
        self._save_config()
        self._log(
            f"[启动器] ✔ 声音「{name}」已应用并写入 conf.yaml："
            f"ref={ref_audio.name}, prompt_lang={gsv['prompt_lang']}, "
            f"text_lang={gsv['text_lang']}"
        )

        # 4) 切换权重（需要 GPT-SoVITS 在运行）
        if gpt_path and sovits_path:
            if not is_port_open(GPT_SOVITS_HOST, GPT_SOVITS_PORT):
                self._log("[启动器] ⚠ GPT-SoVITS 未运行，已写入配置但未切换权重；"
                          "启动后可点「应用模型到 GPT-SoVITS」或一键启动时自动切换")
            else:
                self.launcher_cfg["gpt_sovits_model"] = {
                    "gpt": gpt_path.name,
                    "sovits": sovits_path.name,
                }
                self._save_launcher_config()
                threading.Thread(
                    target=self._apply_weights_worker,
                    args=(gpt_path, sovits_path),
                    daemon=True,
                ).start()
        else:
            self._log("[启动器] ⚠ 该声音模型未指定权重对（或 GPT-SoVITS 根目录未设置），"
                      "只切换了参考音频")

    def _new_voice_model(self):
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return
        root = self._current_gsv_root()
        if not root:
            QMessageBox.warning(self, "未设置 GPT-SoVITS 目录",
                                "请先在 TTS 页选择 GPT-SoVITS 根目录。")
            return
        self._refresh_gpt_weights(silent=True)
        self._refresh_sovits_weights(silent=True)
        gpt_items = [self.combo_gpt_weight.itemText(i)
                     for i in range(self.combo_gpt_weight.count())]
        sovits_items = [self.combo_sovits_weight.itemText(i)
                        for i in range(self.combo_sovits_weight.count())]
        dlg = VoiceDialog(self, gpt_items, sovits_items)
        if dlg.exec() != QDialog.Accepted:
            return

        data = dlg.result_data()
        name = data["name"]
        voice_dir = self._voices_dir() / name
        try:
            voice_dir.mkdir(parents=True, exist_ok=True)
            # 复制参考音频
            src = Path(data["ref_audio"])
            ext = src.suffix or ".wav"
            target_audio = voice_dir / f"ref{ext}"
            if src.resolve() != target_audio.resolve():
                shutil.copy2(src, target_audio)
            meta = {
                "prompt_text": data["prompt_text"],
                "prompt_lang": data["prompt_lang"],
                "text_lang": data["text_lang"],
                "gpt_weight": data["gpt_weight"],
                "sovits_weight": data["sovits_weight"],
            }
            (voice_dir / "voice.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self._log(f"[启动器] ✔ 已创建声音模型「{name}」：{voice_dir}")
        except Exception as e:
            QMessageBox.critical(self, "创建失败", f"写入声音模型时出错：\n{e}")
            return

        self._populate_voice_models()
        self.combo_voice.setCurrentText(name)

    # ------------------------------------------------------------------
    # GPT-SoVITS 权重列表
    # ------------------------------------------------------------------

    def _current_gsv_root(self):
        gsv_root = self.launcher_cfg.get("gpt_sovits_root")
        if gsv_root and Path(gsv_root).is_dir():
            return Path(gsv_root)
        return None

    def _refresh_gpt_weights(self, silent: bool = False):
        root = self._current_gsv_root()
        if not root:
            self.combo_gpt_weight.clear()
            if not silent:
                self._log("[启动器] ⚠ 未设置 GPT-SoVITS 根目录")
            return
        files = list_weight_files(root, GPT_WEIGHTS_PREFIX, ".ckpt")
        current = self.combo_gpt_weight.currentText()
        self.combo_gpt_weight.blockSignals(True)
        self.combo_gpt_weight.clear()
        self.combo_gpt_weight.addItems(files)
        if current and current in files:
            self.combo_gpt_weight.setCurrentText(current)
        self.combo_gpt_weight.blockSignals(False)
        if not silent:
            self._log(f"[启动器] ✔ 发现 GPT 权重 {len(files)} 个")

    def _refresh_sovits_weights(self, silent: bool = False):
        root = self._current_gsv_root()
        if not root:
            self.combo_sovits_weight.clear()
            if not silent:
                self._log("[启动器] ⚠ 未设置 GPT-SoVITS 根目录")
            return
        files = list_weight_files(root, SOVITS_WEIGHTS_PREFIX, ".pth")
        current = self.combo_sovits_weight.currentText()
        self.combo_sovits_weight.blockSignals(True)
        self.combo_sovits_weight.clear()
        self.combo_sovits_weight.addItems(files)
        if current and current in files:
            self.combo_sovits_weight.setCurrentText(current)
        self.combo_sovits_weight.blockSignals(False)
        if not silent:
            self._log(f"[启动器] ✔ 发现 SoVITS 权重 {len(files)} 个")

    @staticmethod
    def _find_weight_item(combo: QComboBox, name: str):
        """在权重下拉中找条目：精确匹配，或匹配 '文件名 [目录]' 的文件名部分。"""
        idx = combo.findText(name)
        if idx >= 0:
            return idx
        for i in range(combo.count()):
            if split_weight_text(combo.itemText(i))[0] == name:
                return i
        return -1

    def _restore_saved_weights_selection(self):
        saved = self.launcher_cfg.get("gpt_sovits_model", {})
        gpt_name = saved.get("gpt", "")
        sovits_name = saved.get("sovits", "")
        if gpt_name:
            idx = self._find_weight_item(self.combo_gpt_weight, gpt_name)
            if idx >= 0:
                self.combo_gpt_weight.setCurrentIndex(idx)
        if sovits_name:
            idx = self._find_weight_item(self.combo_sovits_weight, sovits_name)
            if idx >= 0:
                self.combo_sovits_weight.setCurrentIndex(idx)
        self._update_current_weights_label()

    def _update_current_weights_label(self):
        gpt_name = self.combo_gpt_weight.currentText() or "（未选）"
        sovits_name = self.combo_sovits_weight.currentText() or "（未选）"
        short_gpt = gpt_name if len(gpt_name) <= 32 else gpt_name[:29] + "..."
        short_sovits = sovits_name if len(sovits_name) <= 32 else sovits_name[:29] + "..."
        self.lbl_current_weights.setText(f"当前：{short_gpt}  |  {short_sovits}")

    def _apply_weights(self):
        root = self._current_gsv_root()
        if not root:
            QMessageBox.warning(self, "未设置目录", "请先选择 GPT-SoVITS 根目录。")
            return

        gpt_name = self.combo_gpt_weight.currentText()
        sovits_name = self.combo_sovits_weight.currentText()
        if not gpt_name or not sovits_name:
            QMessageBox.warning(self, "未选择模型", "请先选择 GPT 和 SoVITS 权重文件。")
            return

        gpt_path = find_weight_path(root, GPT_WEIGHTS_PREFIX, gpt_name)
        sovits_path = find_weight_path(root, SOVITS_WEIGHTS_PREFIX, sovits_name)
        if not gpt_path or not sovits_path:
            QMessageBox.critical(self, "文件不存在",
                                 f"找不到权重文件：\nGPT: {gpt_path}\nSoVITS: {sovits_path}")
            return

        # API 以 v4 启动，应用其他版本权重时警告
        for name, path in (("GPT", gpt_path), ("SoVITS", sovits_path)):
            if path.parent.name not in ("GPT_weights_v4", "SoVITS_weights_v4"):
                reply = QMessageBox.warning(
                    self, "版本不匹配",
                    f"{name} 权重「{path.name}」属于 {path.parent.name}，"
                    f"但当前 API 以 v4 模式启动，混用可能导致合成失败或音质异常。\n"
                    f"仍要应用吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

        if not is_port_open(GPT_SOVITS_HOST, GPT_SOVITS_PORT):
            QMessageBox.warning(self, "GPT-SoVITS 未运行",
                                "请先启动 GPT-SoVITS，再应用模型。")
            return

        self.launcher_cfg["gpt_sovits_model"] = {
            "gpt": gpt_name,
            "sovits": sovits_name,
        }
        self._save_launcher_config()

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

        self._log(f"[启动器] ✔ 已应用预设「{name}」（记得点保存配置写入 conf.yaml）")

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
            # 角色
            idx = self.combo_character.currentIndex()
            if 0 <= idx < len(self._character_entries):
                conf_name = self._character_entries[idx][1]
            else:
                conf_name = self.combo_character.currentText()

            self.config.setdefault("character_config", {})
            self.config["character_config"]["conf_name"] = conf_name

            # LLM provider
            cc = self.config["character_config"]
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
                cc["asr_config"][ASR_ENGINE_KEY] = ""
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
                f"(角色={conf_name}, LLM={current_llm}, TTS={current_tts}, "
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
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入 conf.yaml 时出错：\n{e}")

    # ------------------------------------------------------------------
    # 启动 / 停止 Open-LLM-VTuber
    # ------------------------------------------------------------------

    def _start_llm(self):
        if self.llm_process is not None and self.llm_process.poll() is None:
            self._log("[启动器] ⚠ Open-LLM-VTuber 已经在运行")
            return
        if not self.project_root:
            QMessageBox.warning(self, "未设置项目目录", "请先选择项目目录。")
            return

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

    def _stop_llm(self):
        if self.llm_process is None or self.llm_process.poll() is not None:
            return
        self._log("[启动器] ⏹ 正在停止 Open-LLM-VTuber...")
        pid = self.llm_process.pid
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True)
        except Exception as e:
            self._log(f"[启动器] taskkill 失败：{e}")

    def _on_llm_finished(self, exit_code):
        self._log(f"[启动器] ■ Open-LLM-VTuber 进程结束（exit_code={exit_code}）")
        self.llm_process = None
        self.btn_start_llm.setEnabled(True)
        self.btn_stop_llm.setEnabled(False)

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

    def closeEvent(self, event):
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


def main():
    app = QApplication(sys.argv)
    win = LauncherWindow()
    win.show()
    _force_foreground(win)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()