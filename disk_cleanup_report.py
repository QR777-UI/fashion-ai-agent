import os, shutil, time

C = "C:\\"
du = shutil.disk_usage(C)
total = du.total / 1e9
free = du.free / 1e9
used = du.used / 1e9
print(f"C盘  总容量:{total:.1f} GB | 已用:{used:.1f} GB | 剩余:{free:.1f} GB | 剩余占比:{free/total*100:.1f}%")
print("="*65)

# 检查休眠文件状态
hiber = os.path.join(C, "hiberfil.sys")
if os.path.exists(hiber):
    sz = os.path.getsize(hiber)/1e9
    print(f"\n[休眠文件] hiberfil.sys: {sz:.1f} GB  → 还在，关掉可释放 {sz:.1f} GB")
else:
    print("\n[休眠文件] hiberfil.sys: 已不存在 ✓")

def dir_size(path, budget=30):
    total = 0; start = time.time(); timedout = False
    try:
        for root, dirs, files in os.walk(path, followlinks=False):
            for fn in files:
                try: total += os.path.getsize(os.path.join(root, fn))
                except OSError: pass
            if time.time() - start > budget: timedout = True; break
    except OSError: pass
    return total/1e9, timedout

# Windows 内部 - 快速扫描已知的大头
print("\n[Windows 内部组件]")
win_targets = {
    "WinSxS (组件存储)": "C:\\Windows\\WinSxS",
    "SoftwareDistribution (更新缓存)": "C:\\Windows\\SoftwareDistribution",
    "Installer (MSI缓存)": "C:\\Windows\\Installer",
    "DriverStore (驱动备份)": "C:\\Windows\\System32\\DriverStore",
    "Temp": "C:\\Windows\\Temp",
}
for label, p in win_targets.items():
    if os.path.isdir(p):
        sz, to = dir_size(p)
        print(f"  {label}: {sz:.1f} GB{' (超时,实际更大)' if to else ''}")

# 用户 AppData 前几名
print("\n[用户目录 AppData 大文件夹]")
profile = "C:\\Users\\祁润"
appdata = os.path.join(profile, "AppData")
if os.path.isdir(appdata):
    for sub in ["Local", "Roaming", "LocalLow"]:
        sp = os.path.join(appdata, sub)
        if os.path.isdir(sp):
            subs = []
            for d in os.listdir(sp):
                dp = os.path.join(sp, d)
                if os.path.isdir(dp) and not os.path.islink(dp):
                    s, _ = dir_size(dp, budget=5)
                    if s > 0.2:
                        subs.append((d, s))
            print(f"  AppData\\{sub} 中 >200MB 的:")
            for d, s in sorted(subs, key=lambda x: -x[1])[:8]:
                print(f"    └ {d}: {s:.1f} GB")

# 用户一级目录（桌面/下载/Documents等）
print("\n[用户个人目录]")
for sub in ["Desktop", "Downloads", "Documents", "Videos", "Pictures", "Music"]:
    sp = os.path.join(profile, sub)
    if os.path.isdir(sp):
        sz, _ = dir_size(sp, budget=10)
        print(f"  {sub}: {sz:.1f} GB")

# C盘其他可疑目录
print("\n[其他可清理目录]")
others = {
    "C:\\eSupport (华硕预装驱动/工具)": "C:\\eSupport",
    "C:\\ProgramData\\Package Cache (安装包缓存)": "C:\\ProgramData\\Package Cache",
}
for label, p in others.items():
    if os.path.isdir(p):
        sz, to = dir_size(p, budget=15)
        print(f"  {label}: {sz:.1f} GB")
