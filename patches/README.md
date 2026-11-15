# 岛仔 Daozai 补丁

把「随身 WiFi 电量」页面加到 [岛仔](https://github.com/Renly1994/xiaotang-daozai) 上。

适用上游版本：**v0.6.64**（更早/更晚的版本请见下面"冲突排查"）

## 补丁清单

按顺序应用，不要跳：

| 文件 | 作用 |
|---|---|
| `0001-feat-mifi-WiFi.patch` | 主体：新增 `src/mifi.rs`（逻辑 + 7 个单测）、`src/mifi_ui.rs`（页面 + 设置表单），改 `app.rs` / `model.rs` / `extras.rs` / `lib.rs` |
| `0002-fix-mifi-10-page_order.patch` | 补第 10 页的设置描述（否则打开设置会 index out of bounds panic）；`page_order` 恢复"完整排列"校验语义 |
| `0003-test-9-10-page_order.patch` | 把上游 `ui_tests.rs` 里写死的 9 页断言同步到 10 页 |
| `0004-docs-MSVC-gnu.patch` | 新增 `docs/mifi-battery.md`（上游视角的功能与构建说明） |
| `0005-fix-mifi.patch` | 未启用时显示「未启用」而不是「离线」；低电量提醒联动岛内提示；图标资源注入说明 |
| `0006-fix-mifi-windres.patch` | windres 处理 PNG 压缩 ico 会导致图标空白的记录 |

## 应用

```bash
git clone https://github.com/Renly1994/xiaotang-daozai.git
cd xiaotang-daozai
git checkout v0.6.64          # 或对应的 0.6.64 提交

git am /path/to/patches/*.patch
```

如果 `git am` 因空行/编码报错，改用：

```bash
git apply --3way /path/to/patches/0001-feat-mifi-WiFi.patch
# 逐个应用，冲突时手动解
```

> 补丁里的 commit hash、作者、日期来自开发机，应用后会变，这是正常的 —— `git am` 只取 diff 内容。

## 构建

上游默认是 `x86_64-pc-windows-msvc`。如果机器上有 MSVC：

```bash
cargo test --lib
cargo build --release --bin daozai
```

没有 MSVC 的话见 [../docs/04-岛仔源码集成.md](../docs/04-岛仔源码集成.md) 第 5 节，那里写了怎么用 gnu 工具链 + `windres` 从零搭起来（含图标坑）。

## 冲突排查

改的都是**定长数组**，所以上游一旦调整页面数量或设置分页，冲突点很固定：

| 文件 | 位置 | 说明 |
|---|---|---|
| `src/app.rs` | `PAGE_NAMES`、`PAGE_SETTINGS_TABS`、`dots: [Spring; N]` | 页面数与名称 |
| `src/model.rs` | `visible_pages: [bool; N]`、`page_order: [usize; N]`、解析/序列化 | 配置数组与兼容逻辑 |
| `src/extras.rs` | `titles` 数组、`descriptions` 数组、`settings_tab_module` | 设置窗口的 tab 表 |
| `src/ui_tests.rs` | 页面数相关断言 | 上游自己的回归测试 |

页数从 9 变成别的值时，`src/mifi.rs` 和 `src/mifi_ui.rs` 一般不用改 —— 它们不依赖页数，只依赖 `App.mifi` 字段和 `render_page(9)` 这条分支。

## 验证清单

```bash
cargo test --lib mifi::     # 7 个状态机/解析单测
cargo test --lib            # 全套，与未改动版本对比失败数
```

预期：mifi 单测全绿；全套里新增的失败只应来自**环境**（原生窗口、Windows 凭据库、缺 `rc.exe` 的图标测试），不应来自功能逻辑。对比方法见主 README。
