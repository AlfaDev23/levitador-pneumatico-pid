# Refina K_v e tau (simplex proprio) e estima a incerteza; valida em voos nao usados no ajuste.
import numpy as np
from scipy.optimize import minimize
from identificar_voos import ll, trechos
treino, valida = trechos(['voo3', 'voo4']), trechos(['teto3', 'final2'])
p0 = np.load('dados/ident.npy')
passo = np.array([.2, .25, .3, .2, .4])
def otimiza(dados, p0, n=170):
    sx = np.vstack([p0] + [p0 + np.eye(5)[i]*passo[i] for i in range(5)])
    return minimize(lambda p: ll(p, dados), p0, method='Nelder-Mead', options={'initial_simplex': sx, 'maxfev': n, 'xatol': .01, 'fatol': 1e-6})
def mostra(nome, x, dados):
    e = np.exp(x); print(f'{nome}: Kv={e[0]:.4f} tau={e[1]:.2f} s | turb sd={e[2]:.2f} corr={e[4]:.3f} s | ruido={e[3]*100:.2f} cm | ll treino={ll(x, treino):.4f} valid={ll(x, valida):.4f}', flush=True)
s = otimiza(treino, p0); mostra('treino (voo3+voo4)', s.x, treino)
s2 = otimiza(valida, s.x); mostra('so validacao (teto3+final2)', s2.x, valida)
s3 = otimiza(treino + valida, (s.x+s2.x)/2, 120); mostra('todos', s3.x, None)
_, r, n = ll(s3.x, treino+valida, True)
print(f'residuos: media {r.mean():+.2f}, desvio {r.std():.2f}, autocorrelacao lag1 {np.corrcoef(r[1:], r[:-1])[0,1]:+.2f}')
np.save('dados/ident_final.npy', s3.x)
