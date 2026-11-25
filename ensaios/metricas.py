# Desempenho dos ensaios em malha fechada, por trecho de referencia/ganho.
import re, glob, sys
import numpy as np
P = re.compile(r't=\s*([\d.]+) s \| ref=\s*([\d.]+) cm \| h=\s*(-?[\d.]+) cm.*?PWM=\s*([\d.]+) \| Kp=\s*([\d.]+) Ki=\s*([\d.]+) Kd=\s*([\d.]+) \| auto')
for nome in sys.argv[1:]:
    f = sorted(glob.glob(f'dados/{nome}_*.txt'))[-1]
    d = np.array([[float(x) for x in m.groups()] for m in P.finditer(open(f, errors='ignore').read())])
    dec = np.argmax(d[:,2] > 4)                      # decolagem
    print(f'{nome}: {len(d)*.04:.1f} s em auto, decolou em {d[dec,0]-d[0,0]:.1f} s')
    cortes = [0] + [i for i in range(1, len(d)) if (d[i,[1,4,5,6]] != d[i-1,[1,4,5,6]]).any()] + [len(d)]
    for a, b in zip(cortes[:-1], cortes[1:]):
        a0 = max(a, dec); s = d[a0:b]
        if len(s) < 25: continue
        h, r = s[:,2], s[0,1]; e = h - r
        fundo = np.mean(h < 3)*100
        ult = h[-200:] if len(h) >= 200 else h        # ultimos 8 s
        print(f'  ref={r:4.1f} Ki={s[0,5]:4.1f} | {len(s)*.04:4.1f} s | media={h.mean():5.1f} desvio={h.std():4.1f} | ult 8 s: media={ult.mean():5.1f} desvio={ult.std():4.1f} | dentro de 2 cm: {np.mean(abs(e)<=2)*100:3.0f}% | no fundo (<3 cm): {fundo:3.0f}% | u medio={s[:,3].mean():.1f}')
# PWM medio em funcao da altura, com a bola quase parada (todos os voos)
X = []
for f in sorted(glob.glob('dados/voo*.txt') + glob.glob('dados/teto3*.txt')):
    d = np.array([[float(x) for x in m.groups()] for m in P.finditer(open(f, errors='ignore').read())])
    w = 25                                            # janelas de 1 s com pouca variacao de altura
    for i in range(0, len(d)-w, w):
        s = d[i:i+w]
        if abs(s[-5:,2].mean() - s[:5,2].mean()) < 1.5: X.append((s[:,2].mean(), s[:,3].mean()))
X = np.array(X); print('\nPWM medio x altura (janelas de 1 s com a bola quase parada)')
for lo, hi in ((-2,1),(1,3),(3,6),(6,9),(9,12),(12,15),(15,18)):
    k = (X[:,0] >= lo) & (X[:,0] < hi)
    if k.sum() >= 3: print(f'  h {lo:3d} a {hi:2d} cm: {X[k,1].mean():.1f} +- {X[k,1].std():.1f} (n={k.sum()})')
