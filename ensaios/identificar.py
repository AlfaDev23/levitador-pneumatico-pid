# Ajusta o modelo fisico aos disparos gravados em ensaios/dados:
#   tau*w' = u - w                              (ventilador, w em PWM)
#   h'' = g*( (w - h'/Kv)*|w - h'/Kv|/u0^2 - 1 ) (bola; Kv em (m/s)/PWM)
# Kv e tau sao comuns a todos os ensaios; u0 e ajustado em cada um.
import re, glob, sys
import numpy as np
from scipy.optimize import least_squares

PAD = re.compile(r't=\s*([\d.]+) s .*?\| h=\s*(-?[\d.]+) cm.*?PWM=\s*([\d.]+) \|.*\| (auto|manual|parado)')
DT, G = 0.002, 9.81
DEPOIS = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25   # s aproveitados depois do "s"

def carregar(f):
    txt = open(f, encoding='utf-8', errors='ignore').read()
    d = [(float(m[1]), float(m[2])/100, float(m[3]), m[4]) for m in PAD.finditer(txt)]
    ini = next(i for i, x in enumerate(d) if x[3] != 'parado')
    d = d[ini:]
    par = next((i for i, x in enumerate(d) if x[3] == 'parado'), len(d))
    tp = d[par-1][0]
    d = [x for x in d if x[0] <= tp + DEPOIS]
    return np.array([x[0] for x in d]), np.array([x[1] for x in d]), np.array([x[2] for x in d])

def trecho(t, h, tp):
    # disparo: desde 0,5 s antes da ultima passagem por 5 cm, ate 22 cm
    k = np.where(h[:-1] < 0.05)[0]; k = k[k < np.argmax(h)]
    i0 = max(0, k[-1] - 12)
    cima = np.where((np.arange(len(h)) > k[-1]) & (h > 0.22))[0]
    return i0, (cima[0] if len(cima) else len(h))

runs = []
for f in sorted(glob.glob('dados/*.txt')):
    t, h, u = carregar(f)
    if h.max() < 0.10: continue
    i0, i1 = trecho(t, h, None)
    runs.append((f, t, h, u, i0, i1))

def simular(r, Kv, tau, u0, atraso, v0):
    _, t, h, u, i0, i1 = r
    tf = np.arange(t[0], t[i1-1] + DT, DT)
    uf = u[np.clip(np.searchsorted(t, tf, side='right') - 1, 0, len(u)-1)]
    w = np.empty_like(tf); w[0] = u[0] if u[0] > 100 else 0
    al = 1 - np.exp(-DT/tau)
    for k in range(1, len(tf)): w[k] = w[k-1] + al*(uf[k-1] - w[k-1])
    k0 = int((t[i0] - t[0])/DT); x, v = h[i0], v0
    hs = np.full_like(tf, h[i0])
    for k in range(k0, len(tf)):
        rel = w[k] - v/Kv
        v += DT*G*(rel*abs(rel)/u0**2 - 1); x += DT*v
        if x < 0: x, v = 0.0, max(v, 0)
        hs[k] = x
    return np.interp(t[i0:i1] - atraso, tf, hs)

def residuo(p):
    Kv, tau, atraso = np.exp(p[0]), np.exp(p[1]), 0.04
    n = len(runs)
    return np.concatenate([(simular(r, Kv, tau, p[2+j], atraso, p[2+n+j]) - r[2][r[4]:r[5]])*100
                           for j, r in enumerate(runs)])

for r in runs:
    print(r[0], 'pontos', r[5]-r[4], 'h', r[2][r[4]].round(3), '->', r[2][r[5]-1].round(3))
melhor = []
n = len(runs)
for Kv0 in (0.02, 0.05):
    for tau0 in (0.1, 0.3, 0.8):
        p0 = np.r_[np.log(Kv0), np.log(tau0), np.full(n, 146.0), np.zeros(n)]
        lb = np.r_[np.log(0.003), np.log(0.02), np.full(n, 120.0), np.full(n, -0.3)]
        ub = np.r_[np.log(0.3), np.log(5.0), np.full(n, 160.0), np.full(n, 0.3)]
        s = least_squares(residuo, p0, bounds=(lb, ub), x_scale=np.r_[0.3, 0.3, np.full(n, 2.0), np.full(n, 0.1)],
                          diff_step=1e-4, loss='soft_l1', max_nfev=120)
        rms = np.sqrt(np.mean(residuo(s.x)**2))
        melhor.append((s.cost, rms, s.x))
        print(f'chute Kv={Kv0} tau={tau0}: custo={s.cost:.1f} rms={rms:.2f} cm Kv={np.exp(s.x[0]):.4f} tau={np.exp(s.x[1]):.3f} u0={s.x[2:2+n].round(1)} v0={s.x[2+n:].round(2)}')
c, rms, x = min(melhor, key=lambda m: m[0])
Kv, tau, u0 = np.exp(x[0]), np.exp(x[1]), np.median(x[2:2+n])
a = 2*G/(Kv*u0)
print(f'\nMELHOR: Kv={Kv:.4f} (m/s)/PWM  tau={tau:.3f} s  u0={u0:.1f}  a={a:.2f} 1/s  rms={rms:.2f} cm')
print(f'Routh: Ku={(1+a*tau)/(tau*Kv):.1f} PWM/m  Tu={2*np.pi/np.sqrt(a/tau):.2f} s')
