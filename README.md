# Trae 每日积分自动领取 · TraeWork + WorkBuddy

自动领取两个应用每日的签到积分，纯本地 Python + Windows UI 自动化实现，**代码可审、无第三方二进制**。

> 这是一个"GUI 模拟点击"脚本，本质是替代人手每天点一次「签到」。
> 平台并未开放免费签到 API，所有自动化都必须基于界面操作——请自行确认其使用不违反所涉平台规则。

## 支持对象

| 应用 | 入口 | 每日积分 |
|---|---|---|
| TraeWork CN | 侧边栏「每日签到领积分 · 签到」 | 约 200 |
| WorkBuddy | Buddy加油站「立即领取」弹窗 | 100 |

## 快速开始

```bash
# 1. 安装依赖（Windows，Python 3.10+）
pip install -r requirements.txt

# 2. 运行
python run_daily.py
```

脚本按序处理 TraeWork → WorkBuddy，结果写入脚本同目录的 `checkin.log`。

### 应用路径配置（可选）

默认按 `%LOCALAPPDATA%\Programs\...` 常见安装目录查找。若安装到其他位置，设置环境变量覆盖：

```bash
set TRAE_EXE=C:\你的路径\TraeWork.exe
set BUDDY_EXE=C:\你的路径\WorkBuddy.exe
python run_daily.py
```

## 运行原理（为什么不需要校准坐标）

不依赖写死的像素坐标，而是每次运行**实时截图并做像素分析**：

1. 截图 → 在左侧栏区域内找「深色胶囊按钮」（如「签到」「立即领取」）。
2. 已领取时按钮会变灰（如「今日已签」「今日已领」），因此**检测不到深色按钮就自动跳过**，不会重复点或误点。
3. 找到按钮 → 前置窗口 → `SendInput` 单次单击 → 复核按钮是否已变化。

## 已知限制

- **锁屏 / 窗口最小化 / 被遮挡**时，Windows 会拦截模拟点击，本次领取会失败。
- TraeWork 签到面板与 WorkBuddy 弹窗是**网页渲染**，UI 自动化分支拿不到控件句柄，只能靠截图坐标点击——这是平台未开放 API 导致的固有限制。
- 应用改版导致按钮位置/样式变化时，可调整脚本顶部参数：`SIDE_X`（扫描横向范围）、`BOTTOM_GUARD`（跳过底部状态栏）、深色阈值 `110`。

## 目录结构

```
.
├── run_daily.py        # 主脚本（自动定位 + 领取 + 日志）
├── requirements.txt    # 依赖
└── README.md
```

## License

[MIT](LICENSE)