# Verifica se os dados distinguem as hipoteses: perfil de erro em (Kv, tau),
# com e sem forca dependente da altura (u0 efetivo = u0*(1 - c*h)).
import re, sys
src = open('identificar.py', encoding='utf-8').read().split('melhor = []')[0]
exec(src)
n = len(runs)
def sim2(r, Kv, tau, u0, c, v0, atraso=0.04):
    _, t, h, u, i0, i1 = r
    tf = np.arange(t[0], t[i1-1] + DT, DT)
    uf = u[np.clip(np.searchsorted(t, tf, side='right') - 1, 0, len(u)-1)]
    w = np.empty_like(tf); w[0] = u[0]; al = 1 - np.exp(-DT/tau)
    for k in range(1, len(tf)): w[k] = w[k-1] + al*(uf[k-1] - w[k-1])
    k0 = int((t[i0]-t[0])/DT); x, v = h[i0], v0; hs = np.full_like(tf, h[i0])
    for k in range(k0, len(tf)):
        rel = w[k] - v/Kv; ue = u0*(1 - c*x)
        v += DT*G*(rel*abs(rel)/ue**2 - 1); x += DT*v
        if x < 0: x, v = 0.0, max(v, 0)
        hs[k] = x
    return np.interp(t[i0:i1]-atraso, tf, hs)
def ajusta(Kv, tau, livre_c):
    def res(p):
        c = p[2*n] if livre_c else 0.0
        return np.concatenate([(sim2(r, Kv, tau, p[j], c, p[n+j]) - r[2][r[4]:r[5]])*100 for j, r in enumerate(runs)])
    p0 = np.r_[np.full(n, 146.0), np.zeros(n), [0.2]*livre_c]
    lb = np.r_[np.full(n, 100.0), np.full(n, -.3), [-1.0]*livre_c]
    ub = np.r_[np.full(n, 170.0), np.full(n, .3), [2.0]*livre_c]
    s = least_squares(res, p0, bounds=(lb, ub), x_scale=np.r_[np.full(n, 2.0), np.full(n, .1), [.1]*livre_c], diff_step=1e-4, max_nfev=60)
    return np.sqrt(np.mean(s.fun**2)), s.x
for livre in (0, 1):
    print('COM forca dependente da altura' if livre else 'SEM forca dependente da altura')
    for Kv in (0.02, 0.04, 0.06, 0.10):
        linha = []
        for tau in (0.1, 0.3, 0.6, 1.0, 2.0):
            rms, x = ajusta(Kv, tau, livre)
            linha.append(f'tau={tau}: {rms:.2f}cm' + (f' c={x[-1]:.2f}' if livre else '') + f' u0={x[:n].min():.0f}-{x[:n].max():.0f}')
        print(f'  Kv={Kv}: ' + ' | '.join(linha))
