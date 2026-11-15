"""ASR1803 串口调试 CLI（基于 pyserial，纯只读安全默认）。

用法:
  python asr_cli.py ports                         列出系统串口
  python asr_cli.py snapshot                      对 AT 口跑一遍只读查询
  python asr_cli.py at "AT+CSQ"                   发送单条指令（原样返回）
  python asr_cli.py at "AT+CSQ" --baud 921600     指定波特率
  python asr_cli.py log --port COM4 --sec 5       抓 DIAG 日志到 logs/
  python asr_cli.py at "..." --port COM4 --hex    以十六进制显示返回（二进制口用）

默认 AT 口 = COM3，波特率 115200，行尾 \\r\\n。
"""
import argparse
import datetime
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

import serial
from serial.tools import list_ports

AT_PORT = "COM3"
DIAG_PORT = "COM4"
BAUD = 115200
EOL = "\r\n"

SNAPSHOT = [
    ("固件", "AT+CGMR"),
    ("厂商", "AT+CGMI"),
    ("型号", "AT+CGMM"),
    ("IMEI", "AT+CGSN"),
    ("SN", "AT*MRD_SN?"),
    ("WiFi MAC", "AT*MRD_WIFIID?"),
    ("SIM 状态", "AT+CPIN?"),
    ("信号", "AT+CSQ"),
    ("CSQ 详情", "AT+CSQ"),
    ("注册(CS)", "AT+CREG?"),
    ("注册(EPS)", "AT+CEREG?"),
    ("运营商", "AT+COPS?"),
    ("APN", "AT+CGDCONT?"),
    ("射频频段", "AT*BAND?"),
]


def open_port(port: str, baud: int) -> serial.Serial:
    return serial.Serial(port, baud, timeout=0.4, write_timeout=1)


def send(ser: serial.Serial, cmd: str, wait: float = 0.6) -> bytes:
    ser.reset_input_buffer()
    ser.write((cmd + EOL).encode())
    deadline = time.time() + wait
    buf = b""
    while time.time() < deadline:
        chunk = ser.read(4096)
        if chunk:
            buf += chunk
            if b"OK" in buf or b"ERROR" in buf:
                break
        else:
            time.sleep(0.03)
    return buf


def clean(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace").replace("\r", "")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return "\n".join(lines)


def mask(value: str) -> str:
    if len(value) >= 12 and value.isdigit():
        return value[:6] + "*" * (len(value) - 10) + value[-4:]
    return value


def cmd_ports() -> None:
    found = list(list_ports.comports())
    if not found:
        print("没有发现串口")
        return
    for p in found:
        print(f"{p.device:8}  {p.description}  [{p.hwid}]")


def cmd_snapshot(port: str, baud: int) -> None:
    try:
        ser = open_port(port, baud)
    except Exception as exc:
        print(f"打开 {port} 失败: {exc}")
        return
    print(f"设备快照  {port} @ {baud}  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n")
    try:
        time.sleep(0.2)
        for label, cmd in SNAPSHOT:
            raw = send(ser, cmd)
            body = clean(raw)
            values = [
                ln for ln in body.split("\n")
                if not ln.startswith(cmd) and ln not in ("OK", "ERROR")
            ]
            val = " | ".join(v for v in values if not v.endswith("ERROR")) or "(无返回)"
            if label in ("IMEI", "SN"):
                val = mask(val.strip())
            print(f"{label:10} {val}")
    finally:
        ser.close()


def cmd_at(port: str, baud: int, cmd: str, as_hex: bool, wait: float = 1.0) -> None:
    try:
        ser = open_port(port, baud)
    except Exception as exc:
        print(f"打开 {port} 失败: {exc}")
        return
    try:
        raw = send(ser, cmd, wait=max(0.2, wait))
    finally:
        ser.close()
    if as_hex:
        print(" ".join(f"{b:02X}" for b in raw[:512]))
        print(f"({len(raw)} 字节)")
    else:
        print(clean(raw) or "(无回显)")


def cmd_log(port: str, baud: int, seconds: int) -> None:
    try:
        ser = open_port(port, baud)
    except Exception as exc:
        print(f"打开 {port} 失败: {exc}")
        return
    log_dir = os.path.join(HERE, "logs")
    os.makedirs(log_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(log_dir, f"{port}-{stamp}.log")
    total = 0
    print(f"抓取 {port} 共 {seconds}s -> {path}")
    try:
        ser.reset_input_buffer()
        end = time.time() + seconds
        with open(path, "wb") as fh:
            while time.time() < end:
                chunk = ser.read(8192)
                if chunk:
                    fh.write(chunk)
                    total += len(chunk)
    finally:
        ser.close()
    print(f"完成，{total} 字节")


def main() -> None:
    ap = argparse.ArgumentParser(description="ASR1803 串口调试")
    ap.add_argument("action", choices=["ports", "snapshot", "at", "log"])
    ap.add_argument("command", nargs="?", default="AT")
    ap.add_argument("--port", default=AT_PORT)
    ap.add_argument("--baud", type=int, default=BAUD)
    ap.add_argument("--sec", "--seconds", type=int, default=5, dest="sec")
    ap.add_argument("--wait", type=float, default=1.0, help="单条指令最长等待秒数（慢指令调大）")
    ap.add_argument("--hex", action="store_true")
    args = ap.parse_args()

    if args.action == "ports":
        cmd_ports()
    elif args.action == "snapshot":
        cmd_snapshot(args.port, args.baud)
    elif args.action == "at":
        cmd_at(args.port, args.baud, args.command, args.hex, args.wait)
    elif args.action == "log":
        cmd_log(args.port, args.baud, args.sec)


if __name__ == "__main__":
    main()
