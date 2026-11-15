# -*- coding: utf-8 -*-
"""
================================================================================
镇江银山门社区（大龙王巷）居民社会承受—游客流量双向反馈动态网络流仿真器
--------------------------------------------------------------------------------
论文：《居民社会承受—游客流量双向反馈下的状态依赖动态网络流：
       可持续临界阈值与保持性分流》（邱成桐竞赛参赛论文复现）

严格实现主论文式(1)–式(22)：
  式(1)  N_e = U_e - V_e ;  k_e = N_e / A_e ; A_e = L_e * W_e
  式(2)  发送函数 S_e^n = ( min( U_e^{n-n_f} - V_e^{n-1},  C_e Δt ) )_+
  式(3)  接收函数 R_e^n = ( min( V_e^{n-n_ω} + k_jam A_e - U_e^{n-1} - N_{\bar e}^{n-1}, C_e Δt ) )_+
  式(4a) 累计量/在巷人数守恒更新  U/V/N
  式(4b) 节点按比例分配  q_ij = min( p_ij S_i, (p_ij S_i / Σ p S) R_j )
  式(7)  广义成本 D_j + MNL 自然选路 p^0
  式(8)  暴露强度 z = (1/R_res) Σ ω_e N_e
  式(10) Sigmoid 压力 φ(z)
  式(11b) 承受度欧拉离散 a^{n+1}=a^n+Δt[η(1-a^n)-μ a^n φ(z^n)]
  式(12) 状态依赖容量 C_e(a)=C_e[γ_e+(1-γ_e)a]
  式(14)(15) 解析临界 λ*(π)（二分搜索，含社会/流率/存量三类约束）
  式(16)(17) 保持性分流（双岔口 clip）+ 入口延迟 G^n
  式(18)–(22) 五指标

三方案：
  A 基准：仅物理约束 + 自然 Logit，不限入口，a≡1（社会容量=物理容量）
  B 静态承载：社会容量固定 C_e(a_min)，固定按 λ* 入口限流，自然 Logit
  C 本文方法：社会容量随 a^n 动态 + 状态依赖入口反馈 + 双岔口保持性分流

一键运行：  python3 simulation.py
依赖：numpy, matplotlib, json, csv, os, math
================================================================================
"""

import os
import json
import csv
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

# ------------------------------------------------------------------
# 中文字体（依次尝试，全部不可用则回退英文并在图题注明）
# ------------------------------------------------------------------
_CN_OK = False
for _f in ["WenQuanYi Micro Hei", "WenQuanYi Zen Hei", "SimHei",
           "Noto Sans CJK SC", "Microsoft YaHei", "DejaVu Sans"]:
    try:
        matplotlib.font_manager.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [_f]
        _CN_OK = (_f != "DejaVu Sans")
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIR_DATA = os.path.join(ROOT, "data")
DIR_FIG = os.path.join(ROOT, "figures")
os.makedirs(DIR_DATA, exist_ok=True)
os.makedirs(DIR_FIG, exist_ok=True)

# ============================================================
# 1. 全局参数（来源档位见 docs/04_算例与建模说明书.md）
# ============================================================
DT    = 0.5          # Δt (min)            时间步长
NT    = 240          # 总步数              模拟 120 min 运营
VF_M  = 0.9          # v_f (m/s) 自由流速度
VF    = VF_M * 60.0  # v_f = 54 m/min
VW_M  = -1.8         # v_w (m/s) 拥堵波速度
VW    = abs(VW_M) * 60.0   # |v_w| = 108 m/min
CE    = 60.0         # c_e 单位宽度通行率 人/(min·m)（银发慢游折减后）
KJAM  = 5.4          # k_jam 拥堵密度 人/m^2
THETA = 1.0          # θ Logit 拥堵权重
TREF  = 1.0          # T_ref 归一化参考时间 min
RRES  = 750.0        # R_res 大龙王巷核心街区居民（刘天琦论文，350户）
KAPPA = 14.5         # κ Sigmoid 陡度（见说明书§参数自洽性修正说明）
M0    = 0.15         # m Sigmoid 拐点（游客/居民比约15%压力加速）
ETA   = 0.02         # η 恢复速率 1/min
MU    = 0.08         # μ 损耗速率 1/min
AMIN  = 0.60         # a_min 最低可接受承受度
A0    = 0.95         # a^0 初始承受度
LAM   = 4.0          # λ 外部到达率 人/min（略高于临界值，展示C方案优势）

# 数值稳定性：Δt*(η+μ)=0.5*0.10=0.05 < 1，a^n 恒不越界 [0,1]
assert DT * (ETA + MU) < 1.0


# ============================================================
# 2. 网络拓扑：16 节点 / 20 有向边（映射3条真实主题线路）
#    每条有向边: (eid, u, v, L, W, ω, γ, 名称, 所属线路)
#    所属线路: 1=红色星火线 2=慈善文化线 3=银龄生活线 0=跨线联络
# ============================================================
NAMES = {
    0:  "歇歇角驿站(入口/出口)",
    1:  "布业公所巷北口",
    2:  "嵇直故居",
    3:  "党建微家",
    4:  "五卅演讲厅",
    5:  "板壁巷东口",
    6:  "板壁巷西口/三善巷北口",
    7:  "三善巷南口/火星庙巷西口",
    8:  "冬赈局遗址",
    9:  "同济救火会旧址",
    10: "平安锣驿站",
    11: "万家巷北口",
    12: "万家巷街巷文化墙",
    13: "街巷剧场",
    14: "大龙王巷生活街区",
    15: "社区助餐点",
}

# (u, v, L_m, W_m, omega, gamma, name, route)
EDGE_DEF = [
    (0, 1,   90, 2.2, 1.0, 0.5, "布业公所巷南段",        1),
    (1, 2,   60, 2.2, 1.0, 0.5, "布业公所巷北段",        1),
    (2, 3,   50, 2.2, 1.0, 0.5, "布业公所巷延伸",        1),
    (3, 4,  160, 3.5, 0.4, 0.8, "伯先公园通道",          1),
    (4, 0,  260, 4.0, 0.1, 0.8, "外围返回(伯先路)",      1),
    (0, 5,  110, 2.6, 1.0, 0.4, "板壁巷东段",            2),
    (5, 6,  140, 2.6, 1.0, 0.4, "板壁巷西段",            2),
    (6, 7,  120, 2.9, 0.7, 0.5, "三善巷",                2),
    (7, 8,   80, 3.8, 0.7, 0.5, "火星庙巷西段",          2),
    (8, 9,   70, 3.8, 0.7, 0.5, "火星庙巷中段",          2),
    (9, 10,  70, 3.8, 0.7, 0.5, "火星庙巷东段",          2),
    (10, 0, 130, 3.3, 1.0, 0.5, "火星庙巷→歇歇角",       2),
    (0, 10, 130, 3.3, 1.0, 0.5, "歇歇角→万家巷",         3),  # 与上条互为对向边
    (10, 11, 80, 3.1, 1.0, 0.5, "万家巷北段",            3),
    (11, 12,100, 3.1, 1.0, 0.5, "万家巷中段",            3),
    (12, 13, 70, 2.5, 0.7, 0.5, "街巷剧场联络",          3),
    (13, 14, 90, 3.7, 1.0, 0.4, "大龙王巷生活街区",      3),
    (14, 15, 60, 2.4, 0.7, 0.5, "助餐点联络",            3),
    (15, 0, 100, 3.0, 0.7, 0.5, "助餐点返驿站",          3),
    (1, 5,  120, 2.0, 0.7, 0.3, "魏同兴巷联络(窄·敏感)", 0),
]
NE = len(EDGE_DEF)
NV = len(NAMES)

# 由定义派生数组
U_E = np.array([r[0] for r in EDGE_DEF], dtype=int)   # 起点
V_E = np.array([r[1] for r in EDGE_DEF], dtype=int)   # 终点
L   = np.array([r[2] for r in EDGE_DEF], dtype=float)
W   = np.array([r[3] for r in EDGE_DEF], dtype=float)
OM  = np.array([r[4] for r in EDGE_DEF], dtype=float)   # ω_e
GAM = np.array([r[5] for r in EDGE_DEF], dtype=float)   # γ_e
ENM = [r[6] for r in EDGE_DEF]
RT  = [r[7] for r in EDGE_DEF]
A   = L * W                                            # A_e = L_e W_e
C   = CE * W                                          # C_e = c_e W_e 物理容量 人/min
TF  = L / VF                                          # 自由流通行时间 T_e (min)
NF  = np.maximum(1, np.ceil(TF / DT).astype(int))     # n_f 自由流延迟步数
NW  = np.maximum(1, np.ceil(L / VW / DT).astype(int))# n_ω 拥堵波延迟步数

# 对向边映射：式(3)需扣减 N_{\bar e}。本网络中 e11(10→0) 与 e12(0→10) 互相对向
COUNTERPART = np.full(NE, -1, dtype=int)
for e in range(NE):
    m = np.where((U_E == V_E[e]) & (V_E == U_E[e]))[0]
    if len(m) > 0:
        COUNTERPART[e] = int(m[0])

# 邻接表
INN  = {v: [] for v in range(NV)}   # 进入节点 v 的边
OUTV = {v: [] for v in range(NV)}   # 节点 v 出发的边
for e in range(NE):
    INN[V_E[e]].append(e)
    OUTV[U_E[e]].append(e)

ENTRY_EDGES = OUTV[0]               # 从歇歇角出发的入口边 e0,e5,e12
EXIT_EDGES  = INN[0]               # 回到歇歇角的出口边 e4,e11,e18

# 三条固定线路的边序列（用于解析 b_e 与 λ*）
ROUTES = {
    1: [0, 1, 2, 3, 4],
    2: [5, 6, 7, 8, 9, 10, 11],
    3: [12, 13, 14, 15, 16, 17, 18],
}
PI = np.array([1.0/3, 1.0/3, 1.0/3])    # 路径比例向量 π=(红,慈,银)

# b_e = 总客流中经过边 e 的比例（边-路径关联矩阵 B @ π）
BE = np.zeros(NE)
for ridx, r in ROUTES.items():
    BE[r] += PI[ridx - 1]
H_AN = float((OM * BE * TF).sum())      # H = Σ ω_e b_e T_e


def sigmoid(z):
    """式(10) Sigmoid 社会压力 φ(z)"""
    return 1.0 / (1.0 + np.exp(-KAPPA * (z - M0)))


def social_cap(a):
    """式(12) 状态依赖可接受容量 C_e(a)=C_e[γ_e+(1-γ_e)a]"""
    return C * (GAM + (1.0 - GAM) * a)


# ------------------------------------------------------------
# 外部到达需求 λ(t)：30步 ramp-up / 180步恒定 / 30步 ramp-down
# ------------------------------------------------------------
def arrival_rate(n):
    if n < 30:
        return LAM * (n / 30.0)
    elif n < 210:
        return LAM
    else:
        return LAM * max(0.0, (240 - n) / 30.0)


# ============================================================
# 3. 解析临界到达率 λ*(π)  式(14)(15)
# ============================================================
def equilibrium_a(lam):
    """给定到达率 λ 的稳态暴露 z*(λ) 与稳态承受度 a*(λ)（固定路径 Little 律）"""
    z_star = lam * H_AN / RRES                 # z*(λ,π) 式(14)
    phi = sigmoid(z_star)
    a_star = ETA / (ETA + MU * phi)            # 式(14)
    return z_star, a_star, phi


def feasible(lam):
    """式(15) 三类约束同时满足？"""
    if lam <= 0:
        lam = 1e-9
    z_star, a_star, phi = equilibrium_a(lam)
    # 约束1：承受度底线
    if a_star < AMIN - 1e-12:
        return False, z_star, a_star
    cap_social = social_cap(a_star)              # 人/min
    for e in range(NE):
        # 约束2：流率不超社会容量
        if lam * BE[e] > cap_social[e] + 1e-9:
            return False, z_star, a_star
        # 约束3：存量不超物理 k_jam A_e
        if lam * BE[e] * TF[e] > KJAM * A[e] + 1e-9:
            return False, z_star, a_star
    return True, z_star, a_star


def lambda_star_bisect(lo=0.0, hi=20.0, tol=1e-4):
    """二分搜索 λ* = sup{λ : 式(15) 三约束成立}"""
    # 若 λ=0 都不可行（a*(0)<a_min），约定 λ*=0
    ok0, _, _ = feasible(0.0)
    if not ok0:
        return 0.0, H_AN
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        ok, _, _ = feasible(mid)
        if ok:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return lo, H_AN


# ============================================================
# 4. 单次仿真  scheme ∈ {"A","B","C"}
# ============================================================
def simulate(scheme, lam_star):
    Uh = np.zeros((NT + 1, NE))     # 累计进入 U_e^n 历史
    Vh = np.zeros((NT + 1, NE))     # 累计离开 V_e^n 历史
    a = A0
    queue = 0.0                     # 入口排队（人），本步 G^n
    Mout = 0.0                      # 累计完成离场人数
    N_prev = np.zeros(NE)           # 上一步在巷人数（式3 对向流扣减用）

    # 时间序列记录
    rec = dict(t=[], Ntot=[], a=[], z=[], G=[],
               dens=[], inflow=[],
               kmax=0.0, tover=0.0, wdelay=0.0,
               a_min_flag=[], in_over=0.0)

    for n in range(NT):
        t = n * DT

        # ---- 4.1 式(2) 发送函数（步初累计量记账）----
        S = np.zeros(NE)
        for e in range(NE):
            u_delay = Uh[n - NF[e], e] if n >= NF[e] else 0.0   # U_e^{n-n_f}
            boundary = u_delay - Vh[n, e]                        # 已进入未离开
            S[e] = max(0.0, min(boundary, C[e] * DT))

        # ---- 4.2 式(3) 物理接收函数（含拥堵波延迟 + 对向流扣减）----
        Rphys = np.zeros(NE)
        for e in range(NE):
            v_shift = Vh[n - NW[e], e] if n >= NW[e] else 0.0   # V_e^{n-n_ω}
            barN = N_prev[COUNTERPART[e]] if COUNTERPART[e] >= 0 else 0.0
            space = v_shift + KJAM * A[e] - Uh[n, e] - barN
            Rphys[e] = max(0.0, min(space, C[e] * DT))

        # ---- 4.3 式(16) 状态依赖实际可接收 R̂_j ----
        if scheme == "A":
            a_use = 1.0
            Recv = Rphys.copy()                       # 只受物理约束，a≡1
        elif scheme == "B":
            a_use = AMIN
            Recv = np.minimum(Rphys, social_cap(np.full(NE, AMIN)) * DT)  # 固定 a_min
        else:  # C
            a_use = a
            Recv = np.minimum(Rphys, social_cap(np.full(NE, a)) * DT)     # 随 a 动态

        inflow = np.zeros(NE)     # 本步进入各边人数 I_e^n
        outflow = np.zeros(NE)    # 本步离开各边人数

        # ---- 4.4 入口限流（歇歇角 N0）----
        demand_ext = DT * arrival_rate(n) + queue      # 本步想进入 = 新到达 + 队列
        if scheme == "A":
            lam_admit = 1e9                           # 不限流
        elif scheme == "B":
            lam_admit = lam_star                      # 固定按 λ* 限流
        else:  # C：状态依赖入口反馈（式15配套控制律）
            lam_admit = float(np.clip(lam_star * (1 + 2.0 * (a - AMIN)),
                                      0.5 * lam_star, 12.0))
        admit_total = min(demand_ext, lam_admit * DT)

        # 入口三条边 e0/e5/e12 的自然 Logit 分流（式7）
        en = ENTRY_EDGES
        k_en = np.array([max(N_prev[e], 0.0) / A[e] for e in en])
        D_en = TF[en] / TREF + THETA * k_en / KJAM
        p_en = np.exp(-D_en)
        p_en = p_en / p_en.sum()
        admitted = 0.0
        for k, e in enumerate(en):
            got = min(p_en[k] * admit_total, Recv[e] - inflow[e])
            got = max(0.0, got)
            inflow[e] += got
            admitted += got
        G_n = demand_ext - admitted                   # 式(17)后：入口须延迟人数
        queue = G_n

        # ---- 4.5 出口（回到歇歇角的 e4/e11/e18 直接离场）----
        for e in EXIT_EDGES:
            outflow[e] += S[e]
            Mout += S[e]

        # ---- 4.6 内部节点转移（式4b 比例分配 + 式17 保持性分流）----
        for v in range(1, NV):
            ins = INN[v]
            outs = OUTV[v]
            if len(outs) == 0:
                continue
            supply = {i: S[i] for i in ins}
            tot_sup = sum(supply.values())
            if tot_sup <= 1e-12:
                continue
            # 自然 Logit 选路（式7）
            kk = np.array([max(N_prev[j], 0.0) / A[j] for j in outs])
            D_j = TF[outs] / TREF + THETA * kk / KJAM
            p0 = np.exp(-D_j)
            p0 = p0 / p0.sum()
            want = p0 * tot_sup

            # 式(17) 保持性分流：仅 C 方案且恰两支时把自然比例 clip 回可行区间
            if scheme == "C" and len(outs) == 2:
                Qn = want.sum()
                if Qn > 1e-12:
                    r1, r2 = Recv[outs[0]], Recv[outs[1]]
                    lo = max(0.0, 1.0 - r2 / Qn)
                    up = min(1.0, r1 / Qn)
                    p1 = min(max(p0[0], lo), up)
                    want = np.array([p1 * Qn, (1 - p1) * Qn])

            # 式(4b)：下游边 j 实得 = min(申请, 剩余 R̂_j)，再按各上游 supply 占比分摊
            for jj, j in enumerate(outs):
                got = max(0.0, min(want[jj], Recv[j] - inflow[j]))
                if tot_sup > 1e-12:
                    for i in ins:
                        qi = got * supply[i] / tot_sup
                        outflow[i] += qi
                        inflow[j] += qi

        # ---- 4.7 式(4a) 累计量/在巷人数守恒更新 ----
        Uh[n + 1] = Uh[n] + inflow
        Vh[n + 1] = Vh[n] + outflow
        N_now = Uh[n + 1] - Vh[n + 1]

        # ---- 4.8 式(8)(10)(11b) 社会反馈闭环 ----
        z = float((OM * N_now).sum() / RRES)
        # a 始终按式(11b)演化；区别在于是否把 a 反馈到容量/入口
        phi = sigmoid(z)
        a = a + DT * (ETA * (1.0 - a) - MU * a * phi)
        a = min(1.0, max(0.0, a))

        # ---- 4.9 记录与指标 ----
        N_prev = N_now                                # 供下一步对向流扣减
        rec["t"].append(t)
        rec["Ntot"].append(float(N_now.sum()))
        rec["a"].append(a)
        rec["z"].append(z)
        rec["G"].append(G_n)
        rec["dens"].append((N_now / A).copy())
        rec["inflow"].append(inflow.copy())
        # 式(18) 最大双向密度（敏感核心巷 E0 = ω≥0.7）
        for e in range(NE):
            if OM[e] >= 0.7:
                barN = N_now[COUNTERPART[e]] if COUNTERPART[e] >= 0 else 0.0
                rec["kmax"] = max(rec["kmax"],
                                  float((N_now[e] + barN) / A[e]))
        # 式(19) T_over = 承受度跌破 a_min 的累计分钟（与临界综合手册一致口径）
        if a < AMIN - 1e-9:
            rec["tover"] += DT
        # 式(21) 累计入口等待
        rec["wdelay"] += DT * G_n

    # ---- 汇总五指标 式(18)-(22) ----
    Ntot_arr = np.array(rec["Ntot"])
    Tnet = DT * Ntot_arr.sum() / max(Mout, 1e-9)
    total_in = sum(DT * arrival_rate(n) for n in range(NT))
    conserv = total_in - (Mout + Ntot_arr[-1] + queue)

    return dict(
        scheme=scheme,
        kmax=rec["kmax"],
        tover=rec["tover"],
        a_low=float(np.min(rec["a"])),
        wdelay=rec["wdelay"],
        tnet=Tnet,
        mout=Mout,
        queue_left=queue,
        total_in=total_in,
        conserv_err=conserv,
        t=np.array(rec["t"]),
        Ntot=Ntot_arr,
        a=np.array(rec["a"]),
        z=np.array(rec["z"]),
        G=np.array(rec["G"]),
        dens=np.array(rec["dens"]),
        inflow=np.array(rec["inflow"]),
    )


# ============================================================
# 5. 保持性分流单元实验（式17 孤立双岔口）
# ============================================================
def diversion_unit():
    Q = 9.2
    p0 = 0.97
    tt = np.arange(0, 150, DT)
    p_act, a_narr, in_narr, in_wide = [], [], [], []
    Cn, Cw, gn = 11.7, 33.6, 0.35
    for t in tt:
        stressed = 60 <= t <= 110
        a = 0.35 if stressed else 1.0
        Rn = min(Cn * DT, Cn * (gn + (1 - gn) * a) * DT)
        Rw = Cw * DT
        lo = max(0.0, 1 - Rw / (Q * DT))
        up = min(1.0, Rn / (Q * DT))
        p1 = min(max(p0, lo), up)
        p_act.append(p1)
        a_narr.append(a)
        in_narr.append(p1 * Q)
        in_wide.append((1 - p1) * Q)
    return tt, np.array(p_act), np.array(a_narr), np.array(in_narr), np.array(in_wide)


# ============================================================
# 6. 主程序
# ============================================================
if __name__ == "__main__":
    # 初始化 N_prev（步初状态）
    N_prev = np.zeros(NE)

    print("=" * 72)
    print("步骤①  解析临界到达率 λ*(π)  式(14)(15)")
    lam_star, H_an = lambda_star_bisect()
    z_star_at, a_star_at, _ = equilibrium_a(lam_star)
    print(f"  H = Σω_e b_e T_e = {H_an:.4f}")
    print(f"  z*(λ*)={z_star_at:.4f}  a*(λ*)={a_star_at:.4f}")
    print(f"  解析 λ*(π) = {lam_star:.3f} 人/min = {lam_star*60:.1f} 人/时")
    print(f"  仿真施加 λ = {LAM:.2f} 人/min（略高于临界值）")
    print("=" * 72)

    print("步骤②  三方案仿真（同网络/同需求/同初态）")
    res = {s: simulate(s, lam_star) for s in ["A", "B", "C"]}
    for s in ["A", "B", "C"]:
        r = res[s]
        print(f"  [方案{s}] 进入={r['total_in']:.1f} 离场={r['mout']:.1f} "
              f"在网={r['Ntot'][-1]:.1f} 排队={r['queue_left']:.1f} "
              f"守恒误差={r['conserv_err']:.2e}")

    print("-" * 72)
    print(f"{'指标':<18}{'A 基准':>14}{'B 静态':>14}{'C 本文':>14}")
    def row(name, key, fmt):
        print(f"{name:<18}" + "".join(f"{format(res[s][key],fmt):>14}"
                                       for s in ["A", "B", "C"]))
    row("最大密度(人/m²)", "kmax", ".4f")
    row("超限时间(分)", "tover", ".1f")
    row("最低承受度", "a_low", ".4f")
    row("入口等待(人·分)", "wdelay", ".0f")
    row("平均逗留(分)", "tnet", ".3f")

    # ----------------------------------------------------------
    # 6.1 写出数据文件
    # ----------------------------------------------------------
    # network.json
    net_out = dict(
        nodes=[{"id": int(v), "name": NAMES[v]} for v in range(NV)],
        edges=[{
            "eid": int(e), "u": int(U_E[e]), "v": int(V_E[e]),
            "name": ENM[e], "route": RT[e],
            "L_m": float(L[e]), "W_m": float(W[e]), "A_m2": float(A[e]),
            "C_人_per_min": float(C[e]), "omega": float(OM[e]),
            "gamma": float(GAM[e]), "T_e_min": float(TF[e]),
            "n_f": int(NF[e]), "n_omega": int(NW[e]),
            "counterpart": int(COUNTERPART[e]),
        } for e in range(NE)],
        routes={"red": ROUTES[1], "charity": ROUTES[2], "silver": ROUTES[3]},
    )
    with open(os.path.join(DIR_DATA, "network.json"), "w", encoding="utf-8") as f:
        json.dump(net_out, f, ensure_ascii=False, indent=2)

    # params.json
    params = dict(
        dt=DT, N_T=NT, v_f_m_s=VF_M, v_w_m_s=VW_M, c_e=CE, k_jam=KJAM,
        theta=THETA, T_ref=TREF, R_res=RRES, kappa=KAPPA, m=M0,
        eta=ETA, mu=MU, a_min=AMIN, a_0=A0, lambda_=LAM,
        pi=list(PI), H_analytic=H_an,
        note="κ 由任务表的 5.0 修正为 14.5 以保证 a*(0)>a_min、λ* 非退化（见说明书）",
    )
    with open(os.path.join(DIR_DATA, "params.json"), "w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False, indent=2)

    # results_*.json（时间序列）
    for s in ["A", "B", "C"]:
        r = res[s]
        out = dict(
            scheme=s,
            metrics={k: float(r[k]) for k in
                     ["kmax", "tover", "a_low", "wdelay", "tnet",
                      "mout", "queue_left", "total_in", "conserv_err"]},
            time_min=list(map(float, r["t"])),
            Ntot=list(map(float, r["Ntot"])),
            a=list(map(float, r["a"])),
            z=list(map(float, r["z"])),
            G=list(map(float, r["G"])),
            dens=list([list(map(float, row)) for row in r["dens"]]),
            inflow=list([list(map(float, row)) for row in r["inflow"]]),
        )
        with open(os.path.join(DIR_DATA, f"results_{s}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)

    # metrics.csv
    with open(os.path.join(DIR_DATA, "metrics.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["指标", "单位", "方案A_基准", "方案B_静态", "方案C_本文"])
        w.writerow(["k_max_最大双向密度", "人/m²",
                    round(res["A"]["kmax"], 4), round(res["B"]["kmax"], 4),
                    round(res["C"]["kmax"], 4)])
        w.writerow(["T_over_社会超限时间", "min",
                    round(res["A"]["tover"], 2), round(res["B"]["tover"], 2),
                    round(res["C"]["tover"], 2)])
        w.writerow(["a_low_最低承受度", "—",
                    round(res["A"]["a_low"], 4), round(res["B"]["a_low"], 4),
                    round(res["C"]["a_low"], 4)])
        w.writerow(["W_delay_累计入口等待", "人·min",
                    round(res["A"]["wdelay"], 1), round(res["B"]["wdelay"], 1),
                    round(res["C"]["wdelay"], 1)])
        w.writerow(["T_net_平均逗留时间", "min",
                    round(res["A"]["tnet"], 3), round(res["B"]["tnet"], 3),
                    round(res["C"]["tnet"], 3)])

    # critical_threshold.json
    # 扫描 λ 记录 a*(λ) 与约束激活点
    lam_grid = np.linspace(0, 8, 401)
    a_curve, z_curve, feas_curve = [], [], []
    for lam in lam_grid:
        zs, a_s, _ = equilibrium_a(lam)
        ok, _, _ = feasible(lam)
        a_curve.append(float(a_s)); z_curve.append(float(zs))
        feas_curve.append(bool(ok))
    crit = dict(
        lambda_star=float(lam_star),
        H=H_an,
        z_star_at_lambda_star=float(z_star_at),
        a_star_at_lambda_star=float(a_star_at),
        fixed_path_ratio=list(map(float, BE)),
        grid=dict(lam=list(map(float, lam_grid)),
                  a_star=a_curve, z_star=z_curve, feasible=feas_curve),
    )
    with open(os.path.join(DIR_DATA, "critical_threshold.json"), "w", encoding="utf-8") as f:
        json.dump(crit, f, ensure_ascii=False, indent=2)

    # ----------------------------------------------------------
    # 6.2 绘图
    # ----------------------------------------------------------
    col = {"A": "#d62728", "B": "#ff7f0e", "C": "#1f77b4"}

    # --- fig1 网络拓扑图 ---
    pos = {
        0: (3.0, 0.0), 1: (3.0, 1.0), 2: (3.3, 1.8), 3: (3.6, 2.5),
        4: (1.6, 3.0), 5: (4.2, 1.2), 6: (4.8, 2.0), 7: (4.5, 2.8),
        8: (3.8, 3.4), 9: (3.0, 3.6), 10: (2.2, 3.2), 11: (2.0, 2.2),
        12: (1.6, 1.4), 13: (1.2, 0.6), 14: (1.0, -0.3), 15: (1.8, -0.8),
    }
    route_color = {1: "#d62728", 2: "#2ca02c", 3: "#1f77b4", 0: "#999999"}
    fig, ax = plt.subplots(figsize=(11, 8))
    for e in range(NE):
        x1, y1 = pos[U_E[e]]; x2, y2 = pos[V_E[e]]
        lw = 0.6 + 4.0 * (W[e] / 4.0)
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                     arrowstyle="-|>", mutation_scale=10,
                                     lw=lw, color=route_color[RT[e]], alpha=0.85))
    for v, (x, y) in pos.items():
        ax.scatter(x, y, s=110, c="white", edgecolors="black", zorder=3)
        ax.text(x, y + 0.12, f"N{v}", ha="center", fontsize=8, zorder=4)
        label = NAMES[v]
        ax.text(x, y - 0.18, label, ha="center", fontsize=6.5,
                color="#333", zorder=4)
    ax.set_title("银山门社区街巷网络拓扑（红=星火线 绿=慈善线 蓝=银龄线；线宽∝街宽）",
                 fontsize=12)
    ax.axis("off")
    ax.set_aspect("equal")
    plt.tight_layout()
    plt.savefig(os.path.join(DIR_FIG, "fig1_network.png"), dpi=150)
    plt.close()

    # --- fig2 时间序列 2×2 ---
    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5))
    for s in ["A", "B", "C"]:
        r = res[s]
        ax[0, 0].plot(r["t"], r["Ntot"], color=col[s], label=f"方案{s}")
        ax[0, 1].plot(r["t"], r["a"], color=col[s], label=f"方案{s}")
        ax[1, 0].plot(r["t"], r["z"], color=col[s], label=f"方案{s}")
        ax[1, 1].plot(r["t"], r["G"], color=col[s], label=f"方案{s}")
    ax[0, 0].set_title("全网在巷游客总数 N_tot (人)"); ax[0, 0].set_ylabel("人")
    ax[0, 1].axhline(AMIN, color="k", ls=":", label="a_min=0.6")
    ax[0, 1].set_title("居民社会承受度 a^n"); ax[0, 1].set_ylabel("a")
    ax[1, 0].set_title("游客-居民暴露强度 z^n"); ax[1, 0].set_ylabel("z")
    ax[1, 1].set_title("入口延迟人数 G^n (人)"); ax[1, 1].set_ylabel("人")
    for axx in ax.ravel():
        axx.set_xlabel("时间 (min)"); axx.grid(alpha=0.3); axx.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(DIR_FIG, "fig2_time_series.png"), dpi=150)
    plt.close()

    # --- fig3 各边最大密度热力图（横向对比 A/B/C）---
    emax = np.zeros((NE, 3))
    for k, s in enumerate(["A", "B", "C"]):
        emax[:, k] = res[s]["dens"].max(axis=0)
    fig, ax = plt.subplots(figsize=(9, 9))
    im = ax.imshow(emax, aspect="auto", cmap="YlOrBr")
    ax.set_xticks(range(3)); ax.set_xticklabels(["方案A", "方案B", "方案C"])
    ax.set_yticks(range(NE))
    ax.set_yticklabels([f"e{e:02d} {ENM[e]}" for e in range(NE)], fontsize=7)
    for i in range(NE):
        for j in range(3):
            ax.text(j, i, f"{emax[i,j]:.3f}", ha="center", va="center", fontsize=7)
    ax.set_title("三方案各边最大行人密度 k_e (人/m²) 横向对比")
    fig.colorbar(im, ax=ax, label="人/m²")
    plt.tight_layout()
    plt.savefig(os.path.join(DIR_FIG, "fig3_density_heatmap.png"), dpi=150)
    plt.close()

    # --- fig4 五指标柱状图 ---
    metrics = [
        ("k_max 最大双向密度", "kmax", "人/m²"),
        ("T_over 超限时间", "tover", "min"),
        ("a_low 最低承受度", "a_low", "—"),
        ("W_delay 入口等待", "wdelay", "人·min"),
        ("T_net 平均逗留", "tnet", "min"),
    ]
    fig, ax = plt.subplots(1, 5, figsize=(17, 3.6))
    for k, (name, key, unit) in enumerate(metrics):
        vals = [res[s][key] for s in ["A", "B", "C"]]
        bars = ax[k].bar(["A", "B", "C"], vals,
                         color=[col["A"], col["B"], col["C"]])
        for i, v in enumerate(vals):
            if abs(v) < 1e-6:
                label = "0"
            elif abs(v) >= 1000:
                label = f"{v:,.0f}"
            else:
                label = f"{v:.3g}"
            ax[k].text(i, v, label, ha="center", va="bottom", fontsize=8)
        ax[k].set_title(f"{name}\n({unit})", fontsize=10)
        ax[k].grid(alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(os.path.join(DIR_FIG, "fig4_metrics_bar.png"), dpi=150)
    plt.close()

    # --- fig5 临界阈值解析图 ---
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    ax[0].plot(lam_grid, a_curve, "b-", label="解析 a*(λ)")
    ax[0].axvline(lam_star, color="r", ls="--", label=f"λ*={lam_star:.2f}")
    ax[0].axhline(AMIN, color="k", ls=":")
    ax[0].set_xlabel("λ (人/min)"); ax[0].set_ylabel("a*")
    ax[0].set_title("式(14)(15) 稳态承受度随到达率变化")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    ax[1].plot(lam_grid, z_curve, "g-", label="z*(λ)")
    ax[1].axvline(lam_star, color="r", ls="--", label=f"λ*={lam_star:.2f}")
    ax[1].axvline(LAM, color="purple", ls="-.", label=f"施加 λ={LAM:.1f}")
    ax[1].set_xlabel("λ (人/min)"); ax[1].set_ylabel("z*")
    ax[1].set_title("稳态暴露强度 z*(λ) 线性上升")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(DIR_FIG, "fig5_critical_threshold.png"), dpi=150)
    plt.close()

    # --- fig6 保持性分流单元实验 ---
    tt, p1, anr, inn, inw = diversion_unit()
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    ax[0].plot(tt, p1, "b-", label="C 实际 p_1^n")
    ax[0].plot(tt, np.full_like(tt, 0.97), "--", color="gray",
               label="自然 p_1^0=0.97")
    ax[0].set_xlabel("时间 (min)"); ax[0].set_ylabel("进入窄巷比例 p_1")
    ax[0].set_title("式(17) 保持性分流：受压期被 clip 下拉")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    ax[1].plot(tt, inn, "b-", label="进窄巷")
    ax[1].plot(tt, inw, "g-", label="改走宽支路")
    ax[1].set_xlabel("时间 (min)"); ax[1].set_ylabel("流率 (人/min)")
    ax[1].set_title("两支实际进入流率")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(DIR_FIG, "fig6_diversion.png"), dpi=150)
    plt.close()

    print("=" * 72)
    print(f"全部输出完成：data/ 与 figures/ 下各文件已生成。中文字体={'可用' if _CN_OK else '不可用(已回退)'}")
#（注：内容由AI生成）
