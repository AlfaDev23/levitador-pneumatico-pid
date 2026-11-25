# Procura ganhos que controlem TODOS os modelos compativeis com os disparos
# (perfil.py). Simula o firmware: Ts=40 ms, mediana de 3, derivada filtrada, anti-windup.
import numpy as np
G, DT, TS = 9.81, 0.005, 0.04
# Kv, tau, c (forca depende da altura), u0 no fundo
MOD = np.array([(.04,.1,.71,150),(.04,.3,.59,150),(.06,.3,.49,150),(.06,.6,.42,149),(.10,.3,.41,150),
                (.10,.6,.33,149),(.06,1.,.37,148),(.10,1.,.29,148),(.06,.6,0,145),(.10,.3,0,145.5),(.06,1.,0,145)])
def simular(Kp, Ki, Kd, N, u0c, ref=.10, T=24, seed=1, turb=0.012):
    # Vetorizado: ganhos (linhas) x modelos (colunas)
    Kp, Ki, Kd = [np.asarray(x, float)[:, None] for x in (Kp, Ki, Kd)]
    Kv, tau, c, u0 = MOD.T; shp = (Kp.shape[0], len(MOD)); rng = np.random.default_rng(seed)
    x = np.zeros(shp); v = np.zeros(shp); w = np.zeros(shp); I = np.zeros(shp); D = np.zeros(shp)
    hb = [np.zeros(shp)]*3; ha = np.zeros(shp); u = np.zeros(shp); al = 1-np.exp(-DT/tau); d = 0.0
    H, U = [], []; n = int(round(TS/DT)); alfa = TS/(TS+1/N)
    for k in range(int(T/TS)):
        r = ref if k*TS < T*.6 else ref+.05
        hm = x + rng.normal(0, .002, shp); hm = hm + .013*(rng.random(shp) < .05)
        hb = [hb[1], hb[2], hm]; h = np.median(np.stack(hb), axis=0)
        e = r-h; D = D + alfa*(-(h-ha)/TS - D); ha = h
        us = u0c + Kp*e + Ki*I + Kd*D
        I = I + np.where(((us >= 255) & (e > 0)) | ((us <= 0) & (e < 0)), 0, e*TS)
        u = np.clip(u0c + Kp*e + Ki*I + Kd*D, 0, 255)
        d = .85*d + turb*np.sqrt(1-.85**2)*rng.normal()     # turbulencia
        for _ in range(n):
            w = w + al*(u-w); rel = w*(1+d) - v/Kv; ue = u0*(1-c*x)
            v = v + DT*G*(rel*np.abs(rel)/ue**2 - 1); x = x + DT*v
            f = x < 0; v = np.where(f, np.maximum(v, 0), v); x = np.where(f, 0, x)
            f = x > .25; v = np.where(f, np.minimum(v, 0), v); x = np.where(f, .25, x)
        H.append(x.copy()); U.append(u.copy())
    return np.array(H), np.array(U)
if __name__ == '__main__':
    for N in (10, 25):
        g = np.array([(p, i, d) for p in (20,40,60,90,130,180,250) for i in (2,5,10,20,40,80) for d in (5,10,20,35,50,75,100,140,200)], float)
        H, U = simular(*g.T, N, 148)
        n = len(H); ref = np.where(np.arange(n)*TS < n*TS*.6, .10, .15)[:, None, None]
        reg = np.r_[int(n*.35):int(n*.58), int(n*.8):n]
        err = np.sqrt(np.mean((H[reg]-ref[reg])**2, axis=0))*100     # cm
        topo = H.max(axis=0)*100
        print(f'--- N={N}: rms em regime [cm], pior modelo / mediana | pico max [cm]')
        for j in np.argsort(err.max(axis=1))[:8]:
            print('Kp=%3.0f Ki=%2.0f Kd=%3.0f' % tuple(g[j]), '| pior %.1f mediana %.1f | pico %.0f | por modelo' % (err[j].max(), np.median(err[j]), topo[j].max()), err[j].round(1))
        j = [k for k in range(len(g)) if tuple(g[k]) == (60,20,20)][0]
        print('ref (60,20,20): pior %.1f mediana %.1f pico %.0f' % (err[j].max(), np.median(err[j]), topo[j].max()))
