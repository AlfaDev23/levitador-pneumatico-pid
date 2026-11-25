# Graficos do relatorio a partir dos ensaios reais (ensaios/dados -> ensaios/figuras).
import re, glob, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
AZUL, TINTA, SEC, MUDO, GRADE, EIXO, FUNDO = '#2a78d6', '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7', '#fcfcfb'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'figure.facecolor': FUNDO, 'axes.facecolor': FUNDO,
    'axes.edgecolor': EIXO, 'axes.labelcolor': SEC, 'xtick.color': MUDO, 'ytick.color': MUDO, 'axes.grid': True,
    'grid.color': GRADE, 'grid.linewidth': 0.8, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.axisbelow': True})
P = re.compile(r't=\s*([\d.]+) s \| ref=\s*([\d.]+) cm \| h=\s*(-?[\d.]+) cm.*?PWM=\s*([\d.]+) \| Kp=\s*([\d.]+) Ki=\s*([\d.]+) Kd=\s*([\d.]+) \| auto')
def ler(nome):
    f = sorted(glob.glob(f'dados/{nome}_*.txt'))[-1]
    return np.array([[float(x) for x in m.groups()] for m in P.finditer(open(f, errors='ignore').read())])
os.makedirs('figuras', exist_ok=True)
v = lambda x, n=1: f'{x:.{n}f}'.replace('.', ',')

# 1) Voo com decolagem automatica e degraus
d = ler('final2'); t = d[:,0] - d[0,0]
fig, (a, b) = plt.subplots(2, 1, figsize=(9, 5.8), sharex=True, height_ratios=[1.7, 1])
a.plot(t, d[:,2], color=AZUL, lw=2, solid_capstyle='round', label='Altura medida')
a.plot(t, d[:,1], color=TINTA, lw=1.5, ls=(0, (5, 3)), label='Referência')
a.set_ylabel('Altura [cm]'); a.set_ylim(-1.5, 24); a.legend(frameon=False, ncol=2, loc='upper right', labelcolor=SEC)
a.set_title('Altura da bola em malha fechada (sistema real)', loc='left', color=TINTA, fontsize=12, fontweight='bold', pad=20)
a.text(0, 1.02, f'PID com Kp = {v(d[0,4],0)}, Ki = {v(d[0,5],0)} e Kd = {v(d[0,6],0)}; amostragem de 40 ms', transform=a.transAxes, color=SEC)
b.plot(t, d[:,3], color=AZUL, lw=0.5, alpha=0.4)
k = np.ones(25)/25
b.plot(t[12:-12], np.convolve(d[:,3], k, 'valid'), color=AZUL, lw=2)
b.set_ylabel('PWM (0–255)'); b.set_xlabel('Tempo [s]'); b.set_ylim(0, 190); b.set_xlim(0, t[-1])
b.text(0, 1.04, 'PWM aplicado: linha fina = valor a cada 40 ms; linha grossa = média de 1 s', transform=b.transAxes, color=SEC)
fig.tight_layout(); fig.savefig('figuras/voo_degraus.png', dpi=200); plt.close(fig)

# 2) PWM medio x altura
X = []
for nome in ('teto3', 'voo1', 'voo3', 'voo4', 'final2'):
    d = ler(nome); w = 25
    for i in range(0, len(d)-w, w):
        s = d[i:i+w]
        if abs(s[-5:,2].mean() - s[:5,2].mean()) < 1.5: X.append((s[:,2].mean(), s[:,3].mean()))
X = np.array(X)
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.scatter(X[:,0], X[:,1], s=24, color=AZUL, alpha=0.3, lw=0, label='Janela de 1 s com a bola quase parada')
m = []
for lo, hi in ((-2,1),(1,3),(3,6),(6,9),(9,12),(12,15),(15,18)):
    q = (X[:,0] >= lo) & (X[:,0] < hi)
    if q.sum() >= 3: m.append((X[q,0].mean(), X[q,1].mean(), X[q,1].std(), q.sum(), lo, hi))
m = np.array(m)
ax.plot(m[:,0], m[:,1], color=AZUL, lw=2, marker='o', ms=9, mec=FUNDO, mew=2, label='Média por faixa de altura')
ax.set_xticks(range(0, 19, 3))
ax.set_xlabel('Altura da bola [cm]'); ax.set_ylabel('PWM médio (0–255)'); ax.legend(frameon=False, labelcolor=SEC)
ax.set_title('PWM necessário para sustentar a bola em cada altura', loc='left', color=TINTA, fontsize=12, fontweight='bold', pad=20)
ax.text(0, 1.02, 'Médias medidas em malha fechada, em cinco voos', transform=ax.transAxes, color=SEC)
fig.tight_layout(); fig.savefig('figuras/pwm_x_altura.png', dpi=200); plt.close(fig)
for r in m: print(f'h {r[4]:.0f} a {r[5]:.0f} cm: PWM {r[1]:.1f} +- {r[2]:.1f} (n={r[3]:.0f})')

# 3) Numeros do voo final por trecho
d = ler('final2'); c = [0] + [i for i in range(1, len(d)) if d[i,1] != d[i-1,1]] + [len(d)]
for i, j in zip(c[:-1], c[1:]):
    if j - i < 100: continue
    s = d[i:j]; e = s[:,2] - s[0,1]; y = s[-250:,2]
    print(f'ref={s[0,1]:.0f}: {len(s)*.04:.1f} s | ultimos 10 s: {y.mean():.1f} +- {y.std():.1f} cm | erro medio {e.mean():+.1f} | rms {np.sqrt((e**2).mean()):.1f} | min {s[:,2].min():.1f} max {s[:,2].max():.1f}')
