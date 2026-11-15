# 随身移动 WiFi 电量检测

波导 M03X（ASR1803 平台）随身 WiFi 的电量读取、低电量提醒，以及原生集成进 [岛仔 Daozai](https://github.com/Renly1994/xiaotang-daozai) 桌面端的完整过程记录。

不是成品软件仓库，是**一份可复现的方法记录**：遇到什么问题、怎么验证、哪些路走不通、为什么。

## 三条核心结论

1. **AT 串口读不到电量。** 28 条候选指令（`AT+CBC` / `AT*BAT?` / `AT*ADC?` / `AT*CHG?` / `AT*TEMP?` …）在 ASR1803 固件上全部返回 `ERROR` 或 `+CME ERROR: 4`，`AT+CLAC`（枚举指令）也不支持。电池没有接进 AT 层。
2. **Web 接口有电量百分比，没有电压，且无需认证。** 固件自带的 duster 框架提供了一个只读 JSON 接口，能拿到 `battery_percent`、充电状态、电池在位；16 个接口全扫过，**没有任何 mV/ADC 字段**。
3. **岛仔没有插件机制。** 页面在编译期写死（`PAGE_NAMES` 数组 + `match`），egui 无 WebView/DOM，也没有 webhook、文件监听或本地 HTTP 入口。想集成只能改源码，所以这里提供的是**可重放补丁**而不是插件。

## 目录

| 文档 | 内容 |
|---|---|
| [docs/01-串口与AT调试.md](docs/01-串口与AT调试.md) | 两个 COM 口怎么区分、AT 指令探测矩阵、踩过的坑 |
| [docs/02-电量接口逆向.md](docs/02-电量接口逆向.md) | 从 `base.js` 挖出 duster JSON 接口、22 个字段、失败语义 |
| [docs/03-低电量监控脚本.md](docs/03-低电量监控脚本.md) | 独立监控程序：轮询、状态机、静默期、PushPlus |
| [docs/04-岛仔源码集成.md](docs/04-岛仔源码集成.md) | 新增第 10 页、无 MSVC 环境搭 gnu 工具链、图标坑、测试对比 |

## 脚本

| 文件 | 用途 |
|---|---|
| `scripts/asr_cli.py` | AT 口命令行工具（发指令、抓日志、自动找 COM 口） |
| `scripts/probe_battery.py` | 批量探测电量相关 AT 指令，输出矩阵 |
| `scripts/battery_monitor.py` | 独立低电量监控（网页接口 → 阈值判断 → Bark/PushPlus） |

## 补丁

`patches/` 里是岛仔 Daozai 的 6 个补丁（`git am` 即可应用），实现"新增第 10 页：随身 WiFi 电量"。
适用上游 v0.6.64，应用方法与冲突排查见 [patches/README.md](patches/README.md)。

## 环境

- Windows 10/11
- Python 3.9+，`pip install pyserial`
- 设备：波导 M03X（`VID_1286&PID_4E3D`），USB 复合设备
- 实测固件：`AT+CGMR` → `1.057.064`，Web 版本 `LB12AKAS00160_N12_BD_M1261T_V009`，硬件 `LB12A_N12`

## 快速开始

```bash
pip install pyserial

# 1. 找到哪个 COM 口能通 AT
python scripts/asr_cli.py ports
python scripts/asr_cli.py at "ATI"          # → ASR, Inc.

# 2. 确认这固件没放电量指令（会打印一整张矩阵）
python scripts/probe_battery.py

# 3. 走 Web 接口拿电量
curl "http://192.168.1.1/xml_action.cgi?method=get&module=duster&file=json_status_info"

# 4. 独立监控 + 低电量提醒
python scripts/battery_monitor.py --threshold 20 --critical 10
```

## 边界说明

- 只做**读取**。没有刷固件、没有发任何带参数的写指令（`AT&W`/`AT&F`/`AT+RESET` 一次都没用过）。
- Web 接口是固件自带的只读统计接口，不是漏洞利用。
- 岛仔的改动基于 MIT 许可的源码，以补丁形式提供，未修改其原有功能。

## 许可

文档与脚本：MIT。岛仔相关的补丁遵循其上游 MIT 许可。
