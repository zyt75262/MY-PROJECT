# -*- coding: utf-8 -*-
"""时间步敏感性测试 + 哈希复现性检查"""
import subprocess, hashlib, os, sys, json, shutil

PROJ = "/home/user/Doubao/chats/38441471802326274/project"
CODE = os.path.join(PROJ, "code", "simulation.py")
DATA = os.path.join(PROJ, "data")

def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def get_hashes():
    h = {}
    for f in ["results_A.json", "results_B.json", "results_C.json", "metrics.csv", "critical_threshold.json"]:
        h[f] = sha256_file(os.path.join(DATA, f))
    return h

# ---- 1. 第一次运行的哈希 ----
h1 = get_hashes()
print("=== 第一次运行后的哈希 ===")
for k, v in h1.items():
    print(f"  {k}: {v[:24]}...")

# ---- 2. 再运行一次，对比哈希 ----
print("\n=== 第二次运行（检查确定性）===")
result = subprocess.run([sys.executable, CODE], capture_output=True, text=True, cwd=os.path.dirname(CODE))
h2 = get_hashes()
all_same = all(h1[k] == h2[k] for k in h1)
print(f"  两次运行哈希完全一致: {all_same}")
if not all_same:
    for k in h1:
        if h1[k] != h2[k]:
            print(f"  差异: {k}: {h1[k][:16]} vs {h2[k][:16]}")

# ---- 3. 时间步敏感性测试 ----
print("\n=== 时间步敏感性测试 ===")
# 备份原始 simulation.py
shutil.copy(CODE, CODE + ".bak")

# 读取原始代码
with open(CODE, "r") as f:
    orig_code = f.read()

results_sens = {}
for dt_val in [0.25, 0.5, 1.0]:
    # 修改 DT 和 NT 保持总时长 120min
    nt_val = int(120.0 / dt_val)
    modified = orig_code.replace("DT    = 0.5", f"DT    = {dt_val}")
    modified = modified.replace("NT    = 240", f"NT    = {nt_val}")
    # 也需要修改 arrival_rate 中的硬编码 30/210/240
    modified = modified.replace("if n < 30:", f"if n < {int(30*dt_val/0.5)}:")
    modified = modified.replace("n / 30.0", f"n / {int(30*dt_val/0.5)}.0")
    modified = modified.replace("elif n < 210:", f"elif n < {int(210*dt_val/0.5)}:")
    modified = modified.replace("(240 - n) / 30.0", f"({nt_val} - n) / {int(30*dt_val/0.5)}.0")
    modified = modified.replace("return LAM * max(0.0, (240 - n)", f"return LAM * max(0.0, ({nt_val} - n)")

    with open(CODE, "w") as f:
        f.write(modified)

    r = subprocess.run([sys.executable, CODE], capture_output=True, text=True, cwd=os.path.dirname(CODE))
    # 读取 metrics.csv
    with open(os.path.join(DATA, "metrics.csv"), encoding="utf-8-sig") as f:
        lines = f.readlines()
    results_sens[dt_val] = lines

    print(f"\n  Δt={dt_val} (NT={nt_val}):")
    for line in lines[1:]:
        parts = line.strip().split(",")
        print(f"    {parts[0]:30s} A={parts[2]:>10s}  B={parts[3]:>10s}  C={parts[4]:>10s}")

# 恢复原始代码
shutil.copy(CODE + ".bak", CODE)
os.remove(CODE + ".bak")
print("\n  已恢复原始 simulation.py")

# ---- 4. 重新运行原始代码恢复数据 ----
subprocess.run([sys.executable, CODE], capture_output=True, text=True, cwd=os.path.dirname(CODE))
print("  已重新运行原始代码恢复数据")
#（注：内容由AI生成）
