# -*- coding: utf-8 -*-
"""
一键启动 GPT-SoVITS V4 DPO
- 不修改现有 tts_infer.yaml
- 自动寻找 GPT_weights_v4/*v4dpo*.ckpt
- 自动寻找 SoVITS_weights_v4/*v4dpo*.pth
- 用 Python 以 UTF-8 写入临时配置，避免 Windows CMD 中文编码导致的 YAML 读取错误
"""

from pathlib import Path
import os
import socket
import subprocess
import tempfile
import uuid


ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / "runtime" / "python.exe"
API = ROOT / "api_v2.py"
GPT_DIR = ROOT / "GPT_weights_v4"
SOVITS_DIR = ROOT / "SoVITS_weights_v4"


def find_one(folder: Path, pattern: str):
    files = [p for p in folder.glob(pattern) if p.is_file()]
    if not files:
        return None
    # 如果以后放了多个 v4dpo 文件，优先选择修改时间最新的
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def port_in_use(host="127.0.0.1", port=9880):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def main():
    print("=" * 68)
    print(" GPT-SoVITS V4 DPO 一键启动器")
    print("=" * 68)
    print(f"整合包目录: {ROOT}")
    print()

    if not PYTHON.is_file():
        print("[错误] 找不到 runtime\\python.exe")
        print("请确认本程序放在 GPT-SoVITS 整合包根目录。")
        input("\n按 Enter 退出...")
        return 1

    if not API.is_file():
        print("[错误] 找不到 api_v2.py")
        input("\n按 Enter 退出...")
        return 1

    gpt = find_one(GPT_DIR, "*v4dpo*.ckpt")
    sovits = find_one(SOVITS_DIR, "*v4dpo*.pth")

    if gpt is None:
        print(f"[错误] 在 {GPT_DIR} 中没有找到 *v4dpo*.ckpt")
        input("\n按 Enter 退出...")
        return 1

    if sovits is None:
        print(f"[错误] 在 {SOVITS_DIR} 中没有找到 *v4dpo*.pth")
        input("\n按 Enter 退出...")
        return 1

    print(f"[GPT V4 DPO]   {gpt.name}")
    print(f"[SoVITS V4 DPO] {sovits.name}")
    print()

    if port_in_use():
        print("[错误] 9880 端口已经被占用。")
        print("请先关闭之前手动启动的 GPT-SoVITS/API，再重新运行本程序。")
        input("\n按 Enter 退出...")
        return 2

    # 这里故意使用 UTF-8 写临时 YAML。
    # 不使用 CMD 的 echo 重定向，因此不会再出现：
    # UnicodeDecodeError: 'utf-8' codec can't decode byte ...
    #
    # 路径使用相对于整合包根目录的形式，与 api_v2.py / TTS_Config 的工作方式一致。
    gpt_rel = gpt.relative_to(ROOT).as_posix()
    sovits_rel = sovits.relative_to(ROOT).as_posix()

    config_text = f"""custom:
  bert_base_path: GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large
  cnhuhbert_base_path: GPT_SoVITS/pretrained_models/chinese-hubert-base
  device: cuda
  is_half: true
  t2s_weights_path: {gpt_rel}
  version: v4
  vits_weights_path: {sovits_rel}
"""

    temp_path = (
        Path(tempfile.gettempdir()) / f"gpt_sovits_v4_dpo_{uuid.uuid4().hex}.yaml"
    )

    try:
        temp_path.write_text(config_text, encoding="utf-8")

        print(f"临时 V4 配置: {temp_path}")
        print("版本: V4")
        print("地址: http://127.0.0.1:9880/tts")
        print()
        print("正在启动 GPT-SoVITS，请保持这个窗口打开。")
        print("-" * 68)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            str(PYTHON),
            str(API),
            "-c",
            str(temp_path),
            "-a",
            "127.0.0.1",
            "-p",
            "9880",
        ]

        # 关键：cwd 固定在整合包根目录，使 GPT_SoVITS/... 相对路径正常。
        result = subprocess.call(cmd, cwd=str(ROOT), env=env)

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
