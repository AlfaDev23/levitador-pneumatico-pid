# Escolhe K_v e tau pela previsao de varios passos (0,2 a 1 s a frente, sem correcao),
# em voos e disparos. Compara com previsoes triviais.
import sys, glob
import numpy as np
from scipy.optimize import minimize
from identificar_voos import ler, trechos, G, TS, NS, HE, UE
H = 25; PASSOS = [5, 10, 15, 20, 25]
def preparar(nomes, hmin=4, nmin=10):
    out = []
    for n in nomes:
        d = ler(n); h = d[:,2]/100; u = d[:,3]
        ok = (d[:,2] > hmin) & (d[:,2] < 23)
        i = 0
        while i < len(d):
            if not ok[i]: i += 1; continue
            j = i
            while j < len(d) and ok[j] and (j == i or abs(d[j,0]-d[j-1,0]-TS) < .03): j += 1
            if j - i >= nmin: out.append((n, u, h, i, j))
            i = j
    return out
def estados(h, i, j):
    # h e v por regressao local causal (7 amostras, 0,28 s; a mediana atrasa 1)
    ks = np.arange(i+6, j); t = np.arange(-6, 1)*TS
    A = np.vstack([np.ones(7), t, t**2]).T; M = np.linalg.pinv(A)
    Y = np.stack([h[k-6:k+1] for k in ks])
    c = Y @ M.T
    return ks, c[:,0], c[:,1]                # estado em k-1 (h medido em k = h real em k-1)
def prever(Kv, tau, dados, fator=1.0):
    al = 1-np.exp(-TS/NS/tau); E = {p: [] for p in PASSOS}; B0 = {p: [] for p in PASSOS}; B1 = {p: [] for p in PASSOS}
    for (_, u, h, i, j) in dados:
        w = np.empty(len(u)+1); w[0] = u[0]
        for k in range(len(u)): w[k+1] = w[k] + (1-np.exp(-TS/tau))*(u[k]-w[k])
        ks, h0, v0 = estados(h, i, j)
        s = ks - 1; x, v, ww = h0.copy(), v0.copy(), w[s].copy()
        for m in range(1, H+1):
            uk = u[np.minimum(s+m-1, len(u)-1)]
            for _ in range(NS):
                ue = np.interp(np.clip(x, 0, .22), HE, UE)*fator; q = ww - v/Kv
                v = v + TS/NS*G*(q*np.abs(q)/ue**2 - 1); x = x + TS/NS*v; ww = ww + al*(uk-ww)
            if m in E:
                ok = ks + m < j
                E[m].append((x - h[np.minimum(ks+m, len(h)-1)])[ok]); B0[m].append((h0 - h[np.minimum(ks+m, len(h)-1)])[ok])
                B1[m].append((h0 + v0*m*TS - h[np.minimum(ks+m, len(h)-1)])[ok])
    f = lambda D: np.array([np.sqrt(np.mean(np.clip(np.concatenate(D[p]), -.25, .25)**2))*100 for p in PASSOS])
    return f(E), f(B0), f(B1)
voos_a, voos_b = preparar(['voo3', 'voo4'], nmin=40), preparar(['teto3', 'final2'], nmin=40)
disp = preparar(['kp2', 'pid1', 'pid2', 'pid3', 'teto1', 'teto2', 'final1'], hmin=2.5, nmin=9)
custo = lambda p, D: np.mean(prever(np.exp(p[0]), np.exp(p[1]), D)[0])
if __name__ == '__main__':
    print('rms [cm] a', [f'{p*TS:.1f}s' for p in PASSOS])
    for nome, D in (('voos A', voos_a), ('voos B', voos_b), ('disparos', disp)):
        e, b0, b1 = prever(.0163, 1.0, D); print(f'{nome}: n={sum(t[4]-t[3] for t in D)} | parada {b0.round(1)} | vel. constante {b1.round(1)}')
    print('\nperfil: rms medio (0,2 a 1 s) voos A+B / disparos')
    KVS, TAUS = (.004, .006, .009, .012, .016, .022, .03, .045, .07), (.15, .3, .5, .7, 1., 1.5, 2.5)
    print('Kv\tau'.ljust(8) + ''.join(f'{t:>12}' for t in TAUS))
    for Kv in KVS: print(f'{Kv:<8}' + ''.join(f'{np.mean(prever(Kv,t,voos_a+voos_b)[0]):6.2f}/{np.mean(prever(Kv,t,disp)[0]):5.2f}' for t in TAUS))
    for nome, D in (('voos A', voos_a), ('voos B', voos_b), ('disparos', disp), ('tudo (peso igual)', None)):
        f = (lambda p: custo(p, D)) if D else (lambda p: custo(p, voos_a+voos_b) + custo(p, disp))
        s = min((minimize(f, np.log(x0), method='Nelder-Mead', options={'maxfev': 90, 'initial_simplex': np.log([x0, (x0[0]*1.4, x0[1]), (x0[0], x0[1]*1.5)])}) for x0 in ((.008, .5), (.02, 1.))), key=lambda s: s.fun)
        e = np.exp(s.x); print(f'{nome}: Kv={e[0]:.4f} tau={e[1]:.2f} | voos A {prever(*e, voos_a)[0].round(1)} voos B {prever(*e, voos_b)[0].round(1)} disparos {prever(*e, disp)[0].round(1)}')
