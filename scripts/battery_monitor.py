"""MIFI / ASR1803 低电量监控（纯标准库，可跑在任何常开设备上）。

数据源：设备 Web 接口（无需登录）
  http://<设备IP>/xml_action.cgi?method=get&module=duster&file=json_status_info<时间戳>

只读：仅发 GET 请求，不改动设备任何设置。

用法:
  python battery_monitor.py                          # 前台跑，60 秒一次
  python battery_monitor.py --interval 30 --threshold 20
  python battery_monitor.py --host 192.168.1.1 --csv battery.csv
  python battery_monitor.py --webhook https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
  python battery_monitor.py --bark https://api.day.app/你的KEY

推送：--webhook 发 JSON {"text": "..."}（企业微信/钉钉/飞书机器人通用）
      --bark    发 GET 到 Bark，iOS 通知
"""
import argparse
import csv
import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.request

STATUS_API = "http://{host}/xml_action.cgi?method=get&module=duster&file=json_status_info{ts}"
CHARGE_TEXT = {"0": "未充电", "1": "充电中", "2": "已充满", "3": "已充满"}


def fetch(host: str, timeout: float = 8.0) -> dict:
    ts = int(time.time() * 1000)
    url = STATUS_API.format(host=host, ts=ts)
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def notify(webhook: str, bark: str, title: str, body: str) -> None:
    if webhook:
        data = json.dumps({"text": f"{title}\n{body}", "msgtype": "text",
                           "text": {"content": f"{title}\n{body}"}}).encode()
        req = urllib.request.Request(webhook, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=8).read()
            print("  [推送] webhook 已发送")
        except Exception as exc:
            print(f"  [推送失败] webhook: {exc}")
    if bark:
        url = f"{bark.rstrip('/')}/{urllib.parse.quote(title)}/{urllib.parse.quote(body)}"
        try:
            urllib.request.urlopen(url, timeout=8).read()
            print("  [推送] Bark 已发送")
        except Exception as exc:
            print(f"  [推送失败] Bark: {exc}")


def append_csv(path: str, row: list) -> None:
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["时间", "电量%", "充电状态", "已接入电池", "在线秒", "RSSI", "信号格"])
        w.writerow(row)


def main() -> None:
    ap = argparse.ArgumentParser(description="MIFI 低电量监控")
    ap.add_argument("--host", default="192.168.1.1")
    ap.add_argument("--interval", type=int, default=60, help="轮询间隔秒")
    ap.add_argument("--threshold", type=int, default=20, help="低电量提醒阈值，百分比整数")
    ap.add_argument("--critical", type=int, default=10, help="紧急提醒阈值，百分比整数")
    ap.add_argument("--recover", type=int, default=30, help="回升超过此值视为恢复")
    ap.add_argument("--cooldown", type=int, default=1800, help="两次告警最小间隔秒")
    ap.add_argument("--csv", default="", help="记录到 CSV 文件")
    ap.add_argument("--webhook", default="")
    ap.add_argument("--bark", default="")
    ap.add_argument("--once", action="store_true", help="只查一次就退出")
    args = ap.parse_args()

    print(f"监控 {args.host}  间隔 {args.interval}s  阈值 {args.threshold}%  (Ctrl+C 退出)")
    last_alert = 0.0
    level = 0  # 0 正常 / 1 低电量 / 2 紧急

    while True:
        try:
            d = fetch(args.host)
        except Exception as exc:
            print(f"[{datetime.datetime.now():%H:%M:%S}] 读取失败: {exc}")
            if args.once:
                return
            time.sleep(args.interval)
            continue

        pct = int(d.get("battery_percent", "-1") or -1)
        charge = str(d.get("battery_charge", "?"))
        charging = str(d.get("battery_charging", "?"))
        connect = str(d.get("battery_connect", "?"))
        state = CHARGE_TEXT.get(charge, charge)
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {pct:3d}%  {state:4}  电池在位={connect}  "
              f"RSSI={d.get('rssi','?')}  信号={d.get('signal_quality','?')}/5")

        if args.csv:
            append_csv(args.csv, [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  pct, state, connect, d.get("run_seconds", ""),
                                  d.get("rssi", ""), d.get("signal_quality", "")])

        is_charging = charging == "1" or charge in ("1", "2", "3")
        if connect == "1" and pct >= 0:
            if is_charging:
                if level:
                    level = 0
                    print("  -> 已接入电源，告警状态复位")
            elif pct <= args.critical:
                if level < 2 or time.time() - last_alert > args.cooldown:
                    level = 2
                    last_alert = time.time()
                    notify(args.webhook, args.bark,
                           f"电量告急 {pct}%",
                           f"设备 {args.host} 电量仅剩 {pct}%，即将断电，请立即充电。")
            elif pct <= args.threshold:
                if level < 1 or time.time() - last_alert > args.cooldown:
                    level = 1
                    last_alert = time.time()
                    notify(args.webhook, args.bark,
                           f"电量偏低 {pct}%",
                           f"设备 {args.host} 当前电量 {pct}%，未充电，请及时充电。")
            elif pct >= args.recover and level:
                level = 0
                print("  -> 电量已恢复")

        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已停止")
        sys.exit(0)
