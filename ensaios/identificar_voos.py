# Identifica K_v e tau com os VOOS (PWM variando muito), por maxima verossimilhanca
# com filtro de Kalman estendido. Estados: h, v, w (ventilador, em PWM), d (perturbacao).
#   tau*w' = u - w        h'' = g*( (w - v/Kv)|w - v/Kv| / ue(h)^2 - 1 ) + d
# ue(h): PWM medio medido em cada altura (graficos.py). h medido = h atrasado 1 amostra (mediana de 3).
import re, glob, sys
import numpy as np
from scipy.optimize import minimize
P = re.compile(r't=\s*([\d.]+) s \| ref=\s*([\d.]+) cm \| h=\s*(-?[\d.]+) cm.*?PWM=\s*([\d.]+) \|.*\| auto')
G, TS, NS = 9.81, 0.04, 5
HE = np.array([0, .017, .080, .103, .138, .157, .22]); UE = np.array([143.6, 141.1, 133.2, 129.0, 126.7, 127.3, 127.3])
def ler(n):
    f = sorted(glob.glob(f'dados/{n}_*.txt'))[-1]
    return np.array([[float(x) for x in m.groups()] for m in P.finditer(open(f, errors='ignore').read())])
def trechos(nomes):
    out = []
    for n in nomes:
        d = ler(n); ar = d[:,2] > 4
        i = 0
        while i < len(d):
            if ar[i]:
                j = i
                while j < len(d) and ar[j] and (j == i or abs(d[j,0]-d[j-1,0]-TS) < .03): j += 1
                if j - i >= 50:
                    w0 = d[0,3]; w = w0
                    out.append((n, d[:, 3], d[:, 2]/100, i, j))
                i = j
            else: i += 1
    return out
def ll(p, dados, h_pred=None):
    Kv, tau, sd, r, theta = np.exp(p[0]), np.exp(p[1]), np.exp(p[2]), np.exp(p[3]), np.exp(p[4])
    dt = TS/NS; al = 1-np.exp(-dt/tau); fi = np.exp(-dt/theta); tot = 0.0; n = 0; res = []
    for (_, u, h, i, j) in dados:
        w = u[0]
        for k in range(i): w += (1-np.exp(-TS/tau))*(u[k]-w)
        x = np.array([h[i+1], 0.0, w, 0.0]); C = np.diag([4e-4, .04, 25., sd**2])
        for k in range(i, j-1):
            y = h[k+1]                                   # mediana de 3: mede h(k)
            S = C[0,0] + r*r; e = y - x[0]
            tot += .5*(np.log(2*np.pi*S) + e*e/S); n += 1; res.append(e/np.sqrt(S))
            K = C[:,0]/S; x = x + K*e; C = C - np.outer(K, C[0])
            for _ in range(NS):
                hh = min(max(x[0], 0), .22); ue = np.interp(hh, HE, UE); due = (np.interp(hh+1e-3, HE, UE)-np.interp(hh-1e-3, HE, UE))/2e-3
                q = x[2] - x[1]/Kv; a = G*(q*abs(q)/ue**2 - 1) + x[3]
                F = np.eye(4); F[0,1] = dt
                F[1,0] = dt*G*q*abs(q)*(-2/ue**3)*due; F[1,1] = 1 - dt*G*2*abs(q)/ue**2/Kv; F[1,2] = dt*G*2*abs(q)/ue**2; F[1,3] = dt
                F[2,2] = 1-al; F[3,3] = fi
                x = np.array([x[0]+dt*x[1], x[1]+dt*a, x[2]+al*(u[k]-x[2]), x[3]*fi])
                C = F@C@F.T; C[3,3] += sd**2*(1-fi**2); C[1,1] += 1e-6
            C = (C+C.T)/2
            if not np.isfinite(x).all(): return 1e9
    return (tot/n, np.array(res), n) if h_pred else tot/n
if __name__ == '__main__':
    treino, valida = trechos(['voo3', 'voo4']), trechos(['teto3', 'final2'])
    for nome, d in (('treino', treino), ('validacao', valida)): print(nome, [(t[0], t[4]-t[3]) for t in d])
    def fixo(Kv, tau, x0=(np.log(1.0), np.log(.005), np.log(.15))):
        f = lambda q: ll(np.r_[np.log(Kv), np.log(tau), q], treino)
        s = minimize(f, x0, method='Nelder-Mead', options={'maxiter': 45, 'xatol': .05, 'fatol': 2e-4}); return s.fun, s.x
    N = sum(t[4]-t[3]-1 for t in treino)
    print('perfil: 2*(dif. de log-verossim.) em relacao ao melhor (acima de ~6 = rejeitado a 95%)')
    KVS, TAUS = (.008, .012, .018, .03, .06, .12), (.1, .25, .5, 1., 2.)
    tab = {}
    for Kv in KVS:
        q = None
        for tau in TAUS:
            tab[Kv, tau] = fixo(Kv, tau, q if q is not None else (0, np.log(.005), np.log(.15))); q = tab[Kv, tau][1]
    b = min(v[0] for v in tab.values())
    print('Kv\tau ' + ''.join(f'{t:>8}' for t in TAUS))
    for Kv in KVS: print(f'{Kv:<7}' + ''.join(f'{2*N*(tab[Kv,t][0]-b):8.0f}' for t in TAUS))
    kb = min(tab, key=lambda k: tab[k][0])
    s = minimize(lambda p: ll(p, treino), np.r_[np.log(kb[0]), np.log(kb[1]), tab[kb][1]], method='Nelder-Mead', options={'maxiter': 220, 'xatol': .01, 'fatol': 1e-5})
    e = np.exp(s.x); print(f'\nMELHOR Kv={e[0]:.4f} tau={e[1]:.3f} s | perturb. sd={e[2]:.2f} m/s2 corr={e[4]:.2f} s | ruido={e[3]*100:.2f} cm | ll={s.fun:.4f} (grade {b:.4f})')
    print(f'validacao: ll={ll(s.x, valida):.4f}')
    np.save('dados/ident.npy', s.x)
