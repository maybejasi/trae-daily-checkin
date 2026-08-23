# -*- coding: utf-8 -*-
"""TraeWork + WorkBuddy 每日积分自动领取
- 自动定位左侧栏「签到/立即领取」深色按钮（像素分析），不依赖固定坐标，避免误点
- 已领取（按钮变灰）则跳过，并记日志
- 用法：python run_daily.py
"""
import os, sys, time, ctypes, subprocess, datetime
from ctypes import wintypes
from PIL import Image, ImageGrab

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkin.log")
SIDE_X = 420          # 只扫左侧栏 x<420
BOTTOM_GUARD = 950    # 忽略底部状态栏(更新按钮等) y>950
user32 = ctypes.windll.user32

# 应用可执行文件路径：优先环境变量，否则按 %LOCALAPPDATA% 常见安装目录查（可在环境变量里覆盖）
TRAE_EXE = os.environ.get(
    "TRAE_EXE") or os.path.expandvars(r"%LOCALAPPDATA%\Programs\TRAE SOLO CN\TRAE SOLO CN.exe")
BUDDY_EXE = os.environ.get(
    "BUDDY_EXE") or os.path.expandvars(r"%LOCALAPPDATA%\Programs\WorkBuddy\WorkBuddy.exe")

def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def is_visible_process(exe_name):
    r = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe_name}"],
                       capture_output=True, text=True, encoding="gbk", errors="ignore")
    return exe_name.lower() in r.stdout.lower()

def find_top(needle):
    hwnds = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        if user32.IsWindowVisible(h):
            n = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, n, 256)
            if needle in n.value:
                hwnds.append((h, n.value))
        return True
    user32.EnumWindows(cb, 0)
    return hwnds

def capture():
    """全屏截图，返回 PIL RGB Image（等价于 PrintWindow，用 ImageGrab 更稳）"""
    return ImageGrab.grab().convert("RGB")

def dark_pills(im):
    """返回左侧栏内深色胶囊按钮的中心点列表（已忽略底部状态栏）"""
    W, H = im.size
    img = im.convert("RGB"); px = img.load()
    def dark(x, y):
        rr, gg, bb = px[x, y]
        return rr < 110 and gg < 110 and bb < 110
    visited = [[False] * W for _ in range(H)]
    out = []
    for y in range(min(H, BOTTOM_GUARD)):
        for x in range(0, min(W, SIDE_X)):
            if dark(x, y) and not visited[y][x]:
                stack = [(x, y)]; visited[y][x] = True
                minx = maxx = x; miny = maxy = y; cnt = 0
                while stack:
                    cx, cy = stack.pop(); cnt += 1
                    minx = min(minx, cx); maxx = max(maxx, cx)
                    miny = min(miny, cy); maxy = max(maxy, cy)
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < W and 0 <= ny < H and not visited[ny][nx] and dark(nx, ny):
                                visited[ny][nx] = True; stack.append((nx, ny))
                bw, bh = maxx - minx + 1, maxy - miny + 1
                if 30 <= bw <= 220 and 14 <= bh <= 70 and cnt > 100:
                    out.append(((minx + maxx) // 2, (miny + maxy) // 2))
    out.sort(key=lambda p: (p[1], p[0]))
    return out

def activate(hwnd):
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)

def click(x, y):
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                    ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_uint))]
    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("mi", MOUSEINPUT)]
    user32.SetCursorPos(x, y); time.sleep(0.2)
    for flag in (0x0002, 0x0004):   # LEFTDOWN, LEFTUP
        inp = INPUT(); inp.type = 0
        inp.mi.dwFlags = flag
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)); time.sleep(0.08)
    time.sleep(0.5)

def claim(app_name, exe_name, title_needle, launch):
    """对指定应用执行一次领取。app_name 仅用于日志。"""
    if not is_visible_process(exe_name):
        log(f"[{app_name}] 进程未运行，尝试启动 {launch}")
        subprocess.Popen([launch]); time.sleep(8)
    wins = find_top(title_needle)
    if not wins:
        log(f"[{app_name}] 未找到标题含 {title_needle!r} 的窗口，跳过")
        return
    hwnd, t = wins[0]
    activate(hwnd)
    try:
        im = capture()
    except Exception as e:
        log(f"[{app_name}] 截图失败: {e}"); return
    pills = dark_pills(im)
    log(f"[{app_name}] 可点击深色按钮候选: {pills}")
    if not pills:
        log(f"[{app_name}] 未发现深色领取/签到按钮（可能已领取或界面未加载）→ 跳过")
        return
    x, y = pills[0]          # 取最靠上深色按钮（左侧栏中通常是签到/立即领取）
    log(f"[{app_name}] 点击 ({x},{y})")
    click(x, y)
    time.sleep(1.5)
    # 复核
    try:
        im2 = capture()
        pills2 = dark_pills(im2)
        still = any(abs(px0 - x) < 8 and abs(py0 - y) < 8 for px0, py0 in pills2)
        log(f"[{app_name}] 点击后按钮是否仍在: {'是(可能等待/失败)' if still else '否(状态已变化)'}；候选={pills2}")
    except Exception:
        pass

def main():
    log("===== 每日积分自动领取开始 =====")
    claim("TraeWork", "TRAE SOLO CN.exe", "Trae", TRAE_EXE)
    claim("WorkBuddy", "WorkBuddy.exe", "WorkBuddy", BUDDY_EXE)
    log("===== 本轮结束 =====")

if __name__ == "__main__":
    main()