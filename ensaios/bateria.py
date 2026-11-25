# O PWM de equilibrio na mesma altura sobe com o tempo (queda da bateria/aquecimento)?
import re, glob, os
import numpy as np
P = re.compile(r't=\s*([\d.]+) s \| ref=\s*([\d.]+) cm \| h=\s*(-?[\d.]+) cm.*?PWM=\s*([\d.]+) \| Kp=.*?\| auto')
for lo, hi in ((11.5, 16.5),):
    for n in ('teto3', 'voo1', 'voo3', 'voo4', 'final2'):
        f = sorted(glob.glob(f'dados/{n}_*.txt'))[-1]
        d = np.array([[float(x) for x in m.groups()] for m in P.finditer(open(f, errors='ignore').read())])
        d[:, 0] -= d[0, 0]; w = 50; X = []
        for i in range(0, len(d)-w, w):
            s = d[i:i+w]
            if lo <= s[:, 2].mean() <= hi and abs(s[-8:, 2].mean() - s[:8, 2].mean()) < 1.5: X.append((s[:, 0].mean(), s[:, 3].mean()))
        X = np.array(X)
        if len(X) < 4: print(n, 'poucas janelas', len(X)); continue
        b, a = np.polyfit(X[:, 0], X[:, 1], 1); r = X[:, 1] - (a + b*X[:, 0])
        se = np.sqrt((r**2).sum()/(len(X)-2)/((X[:, 0]-X[:, 0].mean())**2).sum())
        print(f"{n} {os.path.basename(f)[-10:-4]}: n={len(X)} (2 s) PWM medio={X[:,1].mean():.1f} | tendencia {b*60:+.1f} +- {1.96*se*60:.1f} PWM/min | t {X[0,0]:.0f}-{X[-1,0]:.0f} s")
