import os, shutil, time

C = "C:\\"
du = shutil.disk_usage(C)
total = du.total / 1e9
free = du.free / 1e9
used = du.used / 1e9
print(f"C盘  总容量:{total:.1f} GB | 已用:{used:.1f} GB | 剩余:{free:.1f} GB | 剩余占比:{free/total*100:.1f}%")
print("=" * 60)

# 已知系统大文件
print("\n[系统大文件]")
for f in ["pagefile.sys", "hiberfil.sys", "swapfile.sys"]:
    p = os.path.join(C, f)
    if os.path.exists(p):
        print(f"  {f}: {os.path.getsize(p)/1e9:.1f} GB")
    else:
        print(f"  {f}: 不存在")

# 时间预算内的目录扫描
def dir_size(path, budget=40):
    total = 0
    start = time.time()
    try:
        for root, dirs, files in os.walk(path):
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

print("\n[C盘一级目录大小]")
top_dirs = []
for name in sorted(os.listdir(C)):
    p = os.path.join(C, name)
    if os.path.isdir(p):
        top_dirs.append(p)

for p in top_dirs:
    sz, timeout = dir_size(p)
    flag = " (扫描超时,实际更大)" if timeout else ""
    print(f"  {p}: {sz/1e9:.1f} GB{flag}")

# 重点展开 Users 目录
print("\n[用户目录明细 C:\\Users]")
users = os.path.join(C, "Users")
if os.path.isdir(users):
    for u in sorted(os.listdir(users)):
        up = os.path.join(users, u)
        if os.path.isdir(up):
            sz, timeout = dir_size(up)
            flag = " (扫描超时,实际更大)" if timeout else ""
            print(f"  {up}: {sz/1e9:.1f} GB{flag}")
            # 用户下子目录
            for sub in sorted(os.listdir(up)):
                sp = os.path.join(up, sub)
                if os.path.isdir(sp):
                    ssz, _ = dir_size(sp, budget=15)
                    print(f"      └ {sub}: {ssz/1e9:.1f} GB")
