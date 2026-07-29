import os, time

def dir_size(path, budget=50, skip_junctions=True):
    total = 0
    start = time.time()
    try:
        for root, dirs, files in os.walk(path, followlinks=False):
            # 跳过 junction/符号链接目录，避免重复计数
            if skip_junctions:
                dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for fn in files:
                try:
                    total += os.path.getsize(os.path.join(root, fn))
                except OSError:
                    pass
            if time.time() - start > budget:
                return total, True
    except OSError:
        return total, False
    return total, False

def gb(n):
    return f"{n/1e9:.1f} GB"

print("[1] 真实用户目录 C:\\Users\\祁润")
UP = "C:\\Users\\祁润"
if os.path.isdir(UP):
    for sub in sorted(os.listdir(UP)):
        sp = os.path.join(UP, sub)
        if os.path.isdir(sp) and not os.path.islink(sp):
            sz, to = dir_size(sp, budget=20)
            print(f"  {sub}: {gb(sz)}{' (超时)' if to else ''}")
else:
    print("  未找到该目录")

print("\n[2] AppData 内部 (最易膨胀)")
APPD = os.path.join(UP, "AppData")
if os.path.isdir(APPD):
    for sub in ["Local", "Roaming", "LocalLow"]:
        sp = os.path.join(APPD, sub)
        if os.path.isdir(sp):
            sz, to = dir_size(sp, budget=25)
            print(f"  AppData\\{sub}: {gb(sz)}{' (超时)' if to else ''}")
    # Local 下 Top 子目录
    loc = os.path.join(APPD, "Local")
    if os.path.isdir(loc):
        print("  -- AppData\\Local 前10大子目录 --")
        subs = []
        for d in os.listdir(loc):
            dp = os.path.join(loc, d)
            if os.path.isdir(dp) and not os.path.islink(dp):
                s, _ = dir_size(dp, budget=10)
                subs.append((d, s))
        for d, s in sorted(subs, key=lambda x: -x[1])[:10]:
            print(f"      {d}: {gb(s)}")

print("\n[3] Windows 内部组件")
win = {
    "WinSxS (组件存储)": "C:\\Windows\\WinSxS",
    "SoftwareDistribution (更新缓存)": "C:\\Windows\\SoftwareDistribution",
    "Temp": "C:\\Windows\\Temp",
    "Installer (MSI缓存)": "C:\\Windows\\Installer",
    "DriverStore (驱动)": "C:\\Windows\\System32\\DriverStore",
    "Prefetch": "C:\\Windows\\Prefetch",
    "Downloaded Program Files": "C:\\Windows\\Downloaded Program Files",
}
for label, p in win.items():
    if os.path.isdir(p):
        sz, to = dir_size(p, budget=30)
        print(f"  {label}: {gb(sz)}{' (超时)' if to else ''}")
    else:
        print(f"  {label}: 不存在")

print("\n[4] 其他可疑大目录")
others = {
    "C:\\eSupport (华硕预装)": "C:\\eSupport",
    "C:\\ProgramData": "C:\\ProgramData",
    "C:\\PerfLogs": "C:\\PerfLogs",
}
for label, p in others.items():
    if os.path.isdir(p):
        sz, to = dir_size(p, budget=20)
        print(f"  {label}: {gb(sz)}{' (超时)' if to else ''}")
