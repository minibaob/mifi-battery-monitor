"""探测电池电压/ADC 相关 AT 指令（只发查询形式，不做任何写入）。

原则：只发送 ? 结尾的查询，或 3GPP 规范定义的纯查询（AT+CBC）。
不发送任何 =<参数> 形式，避免改动设备状态。
"""
import os
import sys
import time

import serial

PORT = "COM3"
BAUD = 115200

CANDIDATES = [
    "AT+CBC",
    "AT+CBC?",
    "AT*BAT?",
    "AT*BATT?",
    "AT*BATV?",
    "AT*VBAT?",
    "AT+BAT?",
    "AT+BATT?",
    "AT*BATTERY?",
    "AT*ADC?",
    "AT+ADC?",
    "AT*CADC?",
    "AT+CADC?",
    "AT*VOLT?",
    "AT+VOLT?",
    "AT*PWR?",
    "AT+PWR?",
    "AT*POWER?",
    "AT+POWER?",
    "AT*CHG?",
    "AT*CHARGE?",
    "AT*TEMP?",
    "AT*MRD_BAT?",
    "AT+CPAS",
    "AT*SYS?",
    "AT+SYSCMD?",
    "AT*SHELL?",
    "AT+CMD?",
]


def query(ser, cmd, wait=1.2):
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode())
    buf = b""
    end = time.time() + wait
    while time.time() < end:
        chunk = ser.read(4096)
        if chunk:
            buf += chunk
            if b"OK" in buf or b"ERROR" in buf:
                break
        else:
            time.sleep(0.03)
    text = buf.decode("utf-8", errors="replace").replace("\r", "")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    body = [ln for ln in lines if ln != cmd]
    return " | ".join(body) if body else "(空)"


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.4, write_timeout=1)
    print(f"探测 {PORT} @ {BAUD} — 仅查询，不写入\n")
    hits = []
    try:
        time.sleep(0.2)
        for cmd in CANDIDATES:
            res = query(ser, cmd)
            mark = "OK " if "OK" in res else ("ERR" if "ERROR" in res else "?  ")
            print(f"[{mark}] {cmd:16} -> {res}")
            if "OK" in res:
                hits.append((cmd, res))
    finally:
        ser.close()

    print("\n=== 有响应的指令 ===")
    if not hits:
        print("(无)")
    for cmd, res in hits:
        print(f"{cmd:16} {res}")


if __name__ == "__main__":
    main()
