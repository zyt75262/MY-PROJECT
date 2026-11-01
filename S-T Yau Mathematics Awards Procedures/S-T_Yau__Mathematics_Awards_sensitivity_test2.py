# -*- coding: utf-8 -*-
"""正确的时间步敏感性测试：直接import模块并修改全局参数"""
import sys, os, json, csv, importlib
import numpy as np

PROJ = "/home/user/Doubao/chats/38441471802326274/project"
CODE = os.path.join(PROJ, "code")
sys.path.insert(0, CODE)
DATA = os.path.join(PROJ, "data")

# 读取原始 simulation 模块
import simulation as sim

def run_with_dt(dt_val, total_time=120.0):
    """用不同 dt 运行仿真，返回五指标"""
    nt_val = int(round(total_time / dt_val))
    # 保存原始值
    orig_dt, orig_nt = sim.DT, sim.NT
    # ramp-up/down 保持 15 分钟
    ramp_steps = int(round(15.0 / dt_val))
    const_start = ramp_steps
    const_end = nt_val - ramp_steps

    sim.DT = dt_val
    sim.NT = nt_val

    # 重定义 arrival_rate
    orig_arrival = sim.arrival_rate
    def custom_arrival(n):
        if n < const_start:
            return sim.LAM * (n / float(const_start))
        elif n < const_end:
            return sim.LAM
        else:
            return sim.LAM * max(0.0, (nt_val - n) / float(ramp_steps))
    sim.arrival_rate = custom_arrival

    # 重算依赖 DT 的派生量
    sim.TF = sim.L / sim.VF
    sim.NF = np.maximum(1, np.ceil(sim.TF / dt_val).astype(int))
    sim.NW = np.maximum(1, np.ceil(sim.L / sim.VW / dt_val).astype(int))

    try:
        lam_star, H_an = sim.lambda_star_bisect()
        res = {s: sim.simulate(s, lam_star) for s in ["A", "B", "C"]}
        out = {}
        for s in ["A", "B", "C"]:
            r = res[s]
            out[s] = {
                "kmax": r["kmax"], "tover": r["tover"], "a_low": r["a_low"],
                "wdelay": r["wdelay"], "tnet": r["tnet"],
                "conserv": r["conserv_err"],
            }
    finally:
        sim.DT = orig_dt
        sim.NT = orig_nt
        sim.arrival_rate = orig_arrival
        sim.TF = sim.L / sim.VF
        sim.NF = np.maximum(1, np.ceil(sim.TF / orig_dt).astype(int))
        sim.NW = np.maximum(1, np.ceil(sim.L / sim.VW / orig_dt).astype(int))

    return out, lam_star

print("="*80)
print("时间步收敛性测试（正确缩放 ramp-up/down=15min，总时长=120min）")
print("="*80)

for dt_val in [0.25, 0.5, 1.0]:
    out, lam_star = run_with_dt(dt_val)
    print(f"\n--- Δt={dt_val} min (NT={int(120/dt_val)}), λ*={lam_star:.3f} ---")
    print(f"  {'指标':<20}{'A':>12}{'B':>12}{'C':>12}")
    for metric in ["kmax", "tover", "a_low", "wdelay", "tnet"]:
        vals = [out[s][metric] for s in ["A","B","C"]]
        print(f"  {metric:<20}{vals[0]:>12.4f}{vals[1]:>12.4f}{vals[2]:>12.4f}")
    for s in ["A","B","C"]:
        print(f"  方案{s} 守恒误差={out[s]['conserv']:.2e}")

# 对比 Δt=0.5 vs Δt=0.25 的变化幅度
print("\n" + "="*80)
print("收敛性评估：Δt=0.5 相对于 Δt=0.25 的变化幅度")
print("="*80)
out025, _ = run_with_dt(0.25)
out050, _ = run_with_dt(0.5)
out100, _ = run_with_dt(1.0)

for metric in ["kmax", "tover", "a_low", "wdelay", "tnet"]:
    for s in ["A","B","C"]:
        v025 = out025[s][metric]
        v050 = out050[s][metric]
        v100 = out100[s][metric]
        # 相对变化 0.25→0.5 和 0.5→1.0
        chg_025_050 = abs(v050 - v025) / max(abs(v025), 1e-9) * 100
        chg_050_100 = abs(v100 - v050) / max(abs(v050), 1e-9) * 100
        if s == "A":
            print(f"  {metric:<20} {s}: Δt 0.25→0.5 变化={chg_025_050:.1f}%  0.5→1.0 变化={chg_050_100:.1f}%")
#（注：内容由AI生成）
