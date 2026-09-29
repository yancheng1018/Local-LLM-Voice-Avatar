# -*- coding: utf-8 -*-
"""
GPT-SoVITS API 通用启动器
适配整合包布局：runtime/python.exe + api_v2.py + GPT/SoVITS_weights_<version>
- 不修改整合包现有 tts_infer.yaml，改用 UTF-8 写临时 YAML 配置（用后即删）
- 权重：--gpt/--sovits 显式指定优先；缺省时在 GPT_weights_<version>/ 与
  SoVITS_weights_<version>/ 中取修改时间最新的一对
- GUI 启动器（launcher/OpenLLMVTuber_GUI.py）与本 CLI 共用本脚本
"""

import argparse
import os
import socket
import subprocess
import tempfile
import uuid
from pathlib import Path


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GPT-SoVITS API 通用启动器（整合包启动适配）"
    )
    parser.add_argument(
        "--root",
        required=True,
        help="GPT-SoVITS 整合包根目录（绝对或相对路径均可）",
    )
    parser.add_argument(
        "--version",
        default="v4",
        help="权重版本目录后缀与临时 YAML version 键（默认 v4）",
    )
    parser.add_argument(
        "--gpt",
        default=None,
        help="显式 GPT 权重（相对 root 的路径或绝对路径），缺省取版本目录最新 .ckpt",
    )
    parser.add_argument(
        "--sovits",
        default=None,
        help="显式 SoVITS 权重（相对 root 的路径或绝对路径），缺省取版本目录最新 .pth",
    )
    return parser.parse_args(argv)


def find_one(folder: Path, pattern: str):
    files = [p for p in folder.glob(pattern) if p.is_file()]
    if not files:
        return None
    # 多个候选权重时优先选择修改时间最新的
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def resolve_weight(
    explicit: str | None, folder: Path, pattern: str, root: Path
) -> Path | None:
    # 显式权重优先：相对路径按 root 拼接；不存在或未给时回退目录内最新
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = root / path
        if path.is_file():
            return path
    return find_one(folder, pattern)


def build_config_text(gpt_rel: str, sovits_rel: str, version: str) -> str:
    # 路径使用相对于整合包根目录的形式，与 api_v2.py / TTS_Config 的工作方式一致
    return f"""custom:
  bert_base_path: GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large
  cnhuhbert_base_path: GPT_SoVITS/pretrained_models/chinese-hubert-base
  device: cuda
  is_half: true
  t2s_weights_path: {gpt_rel}
  version: {version}
  vits_weights_path: {sovits_rel}
"""


def port_in_use(host="127.0.0.1", port=9880):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _as_api_path(weight: Path, root: Path) -> str:
    # 权重在整合包内 → 相对 posix 路径；显式给了包外权重 → 绝对 posix 路径
    try:
        return weight.relative_to(root).as_posix()
    except ValueError:
        return weight.resolve().as_posix()


def main(argv=None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    version = args.version

    print("=" * 68)
    print(" GPT-SoVITS API 启动器")
    print("=" * 68)
    print(f"整合包目录: {root}")
    print()

    python_exe = root / "runtime" / "python.exe"
    api = root / "api_v2.py"

    if not python_exe.is_file():
        print("[错误] 找不到 runtime\\python.exe")
        print("请确认 --root 指向 GPT-SoVITS 整合包根目录。")
        return 1

    if not api.is_file():
        print("[错误] 找不到 api_v2.py")
        return 1

    gpt_dir = root / f"GPT_weights_{version}"
    sovits_dir = root / f"SoVITS_weights_{version}"
    gpt = resolve_weight(args.gpt, gpt_dir, "*.ckpt", root)
    sovits = resolve_weight(args.sovits, sovits_dir, "*.pth", root)

    if gpt is None:
        print(f"[错误] 在 {gpt_dir} 中没有找到 *.ckpt")
        print("可用 --gpt 显式指定 GPT 权重路径。")
        return 1

    if sovits is None:
        print(f"[错误] 在 {sovits_dir} 中没有找到 *.pth")
        print("可用 --sovits 显式指定 SoVITS 权重路径。")
        return 1

    print(f"[GPT]   {gpt.name}")
    print(f"[SoVITS] {sovits.name}")
    print()

    if port_in_use():
        print("[错误] 9880 端口已经被占用。")
        print("请先关闭之前手动启动的 GPT-SoVITS/API，再重新运行本程序。")
        return 2

    config_text = build_config_text(
        _as_api_path(gpt, root), _as_api_path(sovits, root), version
    )

    temp_path = Path(tempfile.gettempdir()) / f"gsv_api_{uuid.uuid4().hex}.yaml"

    try:
        # 故意使用 UTF-8 写临时 YAML，避免 Windows CMD 中文编码导致的 YAML 读取错误
        temp_path.write_text(config_text, encoding="utf-8")

        print(f"版本: {version}")
        print("地址: http://127.0.0.1:9880/tts")
        print()
        print("正在启动 GPT-SoVITS，请保持这个窗口打开。")
        print("-" * 68)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            str(python_exe),
            str(api),
            "-c",
            str(temp_path),
            "-a",
            "127.0.0.1",
            "-p",
            "9880",
        ]

        # 关键：cwd 固定在整合包根目录，使 GPT_SoVITS/... 相对路径正常。
        result = subprocess.call(cmd, cwd=str(root), env=env)

        print()
        print("-" * 68)
        print(f"GPT-SoVITS 已退出，退出代码: {result}")
        return result

    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
