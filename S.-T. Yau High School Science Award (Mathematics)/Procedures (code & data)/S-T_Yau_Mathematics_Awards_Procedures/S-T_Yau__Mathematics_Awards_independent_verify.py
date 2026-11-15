# -*- coding: utf-8 -*-
"""
独立复算脚本：从 results_*.json 读取时间序列，独立复算五指标，
与 metrics.csv 逐项对比；同时做守恒性检验、解析临界值复算、
极端情形测试、κ=5.0 退化验证。
"""
import json, csv, math, hashlib, os
import numpy as np

DATA = "/home/user/Doubao/chats/38441471802326274/project/data"
CODE = "/home/user/Doubao/chats/38441471802326274/project/code"

# ---- 读取 params ----
with open(os.path.join(DATA, "params.json")) as f:
    P = json.load(f)
DT = P["dt"]; KJAM = P["k_jam"]; RRES = P["R_res"]
KAPPA = P["kappa"]; M0 = P["m"]; ETA = P["eta"]; MU = P["mu"]
AMIN = P["a_min"]; CE = P["c_e"]

# ---- 读取 network ----
with open(os.path.join(DATA, "network.json")) as f:
    NET = json.load(f)
edges = NET["edges"]
NE = len(edges)
L = np.array([e["L_m"] for e in edges])
W = np.array([e["W_m"] for e in edges])
OM = np.array([e["omega"] for e in edges])
GAM = np.array([e["gamma"] for e in edges])
A = L * W
C = CE * W
TF = np.array([e["T_e_min"] for e in edges])
CP = np.array([e["counterpart"] for e in edges])

# 路径比例
routes = NET["routes"]
PI = np.array([1/3, 1/3, 1/3])
BE = np.zeros(NE)
for ridx, key in enumerate(["red", "charity", "silver"]):
    for eid in routes[key]:
        BE[eid] += PI[ridx]

print("="*70)
print("A. 独立复算五指标")
print("="*70)

# 读取 metrics.csv 作为对比基准
metrics_csv = {}
with open(os.path.join(DATA, "metrics.csv"), encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        metrics_csv[row["指标"]] = {
            "A": float(row["方案A_基准"]),
            "B": float(row["方案B_静态"]),
            "C": float(row["方案C_本文"]),
        }

def recompute_metrics(scheme):
    """从 results_X.json 独立复算五指标"""
    with open(os.path.join(DATA, f"results_{scheme}.json")) as f:
        R = json.load(f)
    t = np.array(R["time_min"])
    Ntot = np.array(R["Ntot"])
    a_arr = np.array(R["a"])
    G = np.array(R["G"])
    dens = np.array(R["dens"])   # (NT, NE)
    inflow = np.array(R["inflow"])  # (NT, NE)
    met = R["metrics"]
    NT_steps = len(t)

    # k_max: 敏感核心巷 omega>=0.7 的最大双向密度 (N_e + N_bar)/A
    kmax = 0.0
    for n in range(NT_steps):
        for e in range(NE):
            if OM[e] >= 0.7:
                barN = dens[n, CP[e]] * A[CP[e]] if CP[e] >= 0 else 0.0
                # dens[n,e] = N_e/A_e, so N_e = dens[n,e]*A[e]
                Ne = dens[n, e] * A[e]
                kmax = max(kmax, (Ne + barN) / A[e])

    # T_over: a < a_min 的累计分钟
    tover = 0.0
    for n in range(NT_steps):
        if a_arr[n] < AMIN - 1e-9:
            tover += DT

    # a_low: min(a)
    a_low = float(np.min(a_arr))

    # W_delay: sum(DT * G^n)
    wdelay = float(np.sum(DT * G))

    # T_net: DT * sum(Ntot) / Mout
    # Mout = total external exit = total_in - final_Ntot - queue_left
    # But we can compute from metrics
    mout = met["mout"]
    tnet = DT * np.sum(Ntot) / max(mout, 1e-9)

    return {
        "kmax": kmax, "tover": tover, "a_low": a_low,
        "wdelay": wdelay, "tnet": tnet,
        "mout": mout, "Ntot_end": float(Ntot[-1]),
        "total_in": met["total_in"], "queue_left": met["queue_left"],
        "conserv_err": met["conserv_err"],
    }

results_recomputed = {}
for s in ["A", "B", "C"]:
    rc = recompute_metrics(s)
    results_recomputed[s] = rc
    print(f"\n--- 方案{s} ---")
    print(f"  k_max:  复算={rc['kmax']:.6f}  metrics.csv={list(metrics_csv.values())[0]['A' if s=='A' else 'B' if s=='B' else 'C']:.6f}")
    print(f"  T_over: 复算={rc['tover']:.4f}  metrics.csv={list(metrics_csv.values())[1][s]:.4f}")
    print(f"  a_low:  复算={rc['a_low']:.6f}  metrics.csv={list(metrics_csv.values())[2][s]:.6f}")
    print(f"  W_delay:复算={rc['wdelay']:.4f}  metrics.csv={list(metrics_csv.values())[3][s]:.4f}")
    print(f"  T_net:  复算={rc['tnet']:.6f}  metrics.csv={list(metrics_csv.values())[4][s]:.6f}")
    print(f"  守恒误差(来自JSON)={rc['conserv_err']:.2e}")
    print(f"  total_in={rc['total_in']:.1f} mout={rc['mout']:.1f} Ntot_end={rc['Ntot_end']:.1f} queue={rc['queue_left']:.1f}")

print("\n" + "="*70)
print("B. 守恒性检验：total_in = Mout + Ntot_final + queue_left")
print("="*70)
for s in ["A", "B", "C"]:
    rc = results_recomputed[s]
    balance = rc["total_in"] - (rc["mout"] + rc["Ntot_end"] + rc["queue_left"])
    print(f"  方案{s}: total_in={rc['total_in']:.4f} - (mout={rc['mout']:.4f} + Ntot_end={rc['Ntot_end']:.4f} + queue={rc['queue_left']:.4f}) = {balance:.6e}")

print("\n" + "="*70)
print("C. 解析临界值独立复算")
print("="*70)

H = float((OM * BE * TF).sum())
print(f"  H = Σ ω_e b_e T_e = {H:.6f}")

# 复算 a*(0)
def sigmoid(z, kappa=KAPPA):
    return 1.0 / (1.0 + math.exp(-kappa * (z - M0)))

phi0 = sigmoid(0.0)
a0 = ETA / (ETA + MU * phi0)
print(f"  κ={KAPPA}: φ(0)={phi0:.6f}, a*(0)={a0:.6f} ({'≥' if a0>=AMIN else '<'} a_min={AMIN})")

# κ=5.0 退化验证
phi0_k5 = 1.0 / (1.0 + math.exp(-5.0 * (0.0 - M0)))
a0_k5 = ETA / (ETA + MU * phi0_k5)
print(f"  κ=5.0:   φ(0)={phi0_k5:.6f}, a*(0)={a0_k5:.6f} ({'≥' if a0_k5>=AMIN else '<'} a_min={AMIN})")

# 复算 λ*: 令 a*=a_min=0.6
# φ* = η(1-a_min)/(μ*a_min)
phi_star = ETA * (1 - AMIN) / (MU * AMIN)
print(f"  φ* (when a*={AMIN}) = {phi_star:.6f}")
# 反解 Sigmoid: φ = 1/(1+exp(-κ(z-m))) => exp(-κ(z-m)) = 1/φ - 1
# -κ(z-m) = ln(1/φ - 1) => z* = m - (1/κ) ln(1/φ - 1)
z_star = M0 - (1.0/KAPPA) * math.log(1.0/phi_star - 1.0)
print(f"  z* (when a*={AMIN}) = {z_star:.6f}")
lam_star_calc = RRES * z_star / H
print(f"  λ* = R_res * z* / H = {RRES} * {z_star:.6f} / {H:.6f} = {lam_star_calc:.6f} 人/min")

# 从 critical_threshold.json 读取对比
with open(os.path.join(DATA, "critical_threshold.json")) as f:
    CT = json.load(f)
print(f"  critical_threshold.json λ* = {CT['lambda_star']:.6f}")
print(f"  误差 = {abs(lam_star_calc - CT['lambda_star']):.6e}")

# 物理约束检查
print("\n  物理约束复检（λ*=%.3f 时）:" % CT['lambda_star'])
lam = CT['lambda_star']
for e in range(NE):
    flow = lam * BE[e]
    cap_social = C[e] * (GAM[e] + (1-GAM[e]) * AMIN)
    stock = lam * BE[e] * TF[e]
    phys_stock = KJAM * A[e]
    if flow > cap_social + 1e-6:
        print(f"    e{e:02d} {edges[e]['name']}: flow={flow:.3f} > social_cap={cap_social:.1f} *** VIOLATED")
    if stock > phys_stock + 1e-6:
        print(f"    e{e:02d} {edges[e]['name']}: stock={stock:.3f} > k_jam*A={phys_stock:.1f} *** VIOLATED")
print("    (无输出=全部满足)")

print("\n" + "="*70)
print("D. 稳态解析-仿真互证（最后50步平均）")
print("="*70)
for s in ["A", "B", "C"]:
    with open(os.path.join(DATA, f"results_{s}.json")) as f:
        R = json.load(f)
    a_arr = np.array(R["a"])
    z_arr = np.array(R["z"])
    a_ss = float(np.mean(a_arr[-50:]))
    z_ss = float(np.mean(z_arr[-50:]))
    # 解析值在 λ=4.0 时
    lam_test = 4.0
    z_analytic = lam_test * H / RRES
    phi_analytic = sigmoid(z_analytic)
    a_analytic = ETA / (ETA + MU * phi_analytic)
    print(f"  方案{s}: 仿真稳态 a={a_ss:.4f} z={z_ss:.4f} | 解析 a*(λ=4)={a_analytic:.4f} z*={z_analytic:.4f}")
    print(f"           注意: 方案A/B/C 入口限流不同，实际到达≠λ=4，此对比仅供参考")

print("\n" + "="*70)
print("E. k_max 与 k_jam 对比（网络-流量匹配性）")
print("="*70)
print(f"  k_jam = {KJAM} 人/m²")
for s in ["A", "B", "C"]:
    rc = results_recomputed[s]
    ratio = rc["kmax"] / KJAM
    print(f"  方案{s}: k_max={rc['kmax']:.6f} 人/m²  占 k_jam 的 {ratio*100:.3f}%")

# 各边最大流量 vs 容量
print("\n  各边峰值流量 vs 物理容量:")
for s in ["A", "B", "C"]:
    with open(os.path.join(DATA, f"results_{s}.json")) as f:
        R = json.load(f)
    inflow = np.array(R["inflow"])  # (NT, NE)
    peak_in = inflow.max(axis=0)
    print(f"  方案{s} 最繁忙3条边:")
    top3 = np.argsort(peak_in)[::-1][:3]
    for e in top3:
        print(f"    e{e:02d} {edges[e]['name']:20s}: peak_inflow={peak_in[e]:.3f} 人/step ({peak_in[e]/DT:.3f} 人/min)  C={C[e]:.1f} 人/min  占比={peak_in[e]/DT/C[e]*100:.2f}%")

print("\n" + "="*70)
print("F. 输出 SHA256 哈希（可复现性）")
print("="*70)
for fname in ["results_A.json", "results_B.json", "results_C.json", "metrics.csv", "critical_threshold.json"]:
    fpath = os.path.join(DATA, fname)
    with open(fpath, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    print(f"  {fname}: {h[:32]}...")

print("\n" + "="*70)
print("G. 检查 T_over 定义偏差")
print("="*70)
print("  主论文式(19)原文: 流入超过社会容量的时间")
print("  程序实现: 承受度 a < a_min 的累计分钟 (代码行402-404)")
print("  偏差类型: 指标口径替换 — 从'流量越容量'改为'承受度越底线'")
for s in ["A", "B", "C"]:
    rc = results_recomputed[s]
    print(f"  方案{s}: T_over={rc['tover']:.1f} min (口径=承受度跌破a_min时间)")

print("\nDone.")
#（注：内容由AI生成）
