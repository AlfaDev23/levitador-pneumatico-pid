"""Parte B em duas pecas:
  B1 = encaixe na parte A + funil conico + alojamento do retificador + encaixe da garrafa
  B2 = retificador de fluxo, entra por cima em B1 e apoia no degrau no fim do cone.
       A borda de cima do retificador serve de batente para a garrafa.
Folgas ja compensam furos que encolhem na impressao FDM.
"""
import sys, os, struct
import numpy as np
from manifold3d import Manifold

SEG = 256
cyl = lambda h, r, r2=-1: Manifold.cylinder(h, r, r2, circular_segments=SEG)

def tubo(ri, ro, z0, h):
    return (cyl(h, ro) - cyl(h + 2, ri).translate([0, 0, -1])).translate([0, 0, z0])

def box(sx, sy, sz, x=0, y=0, z=0):
    return Manifold.cube([sx, sy, sz]).translate([x, y, z])

# Parte A
R_DUTO, R_EXT_A = 43.0, 45.5
# Garrafa
D_GARRAFA_EXT, FOLGA_GARRAFA = 60.0, 0.4      # mesma folga da luva de juncao
R_FURO = (D_GARRAFA_EXT + FOLGA_GARRAFA) / 2  # 30.2 -> retificador + garrafa

# ---------------- B1 ----------------
RI_LUVA_A = R_EXT_A + 0.4                     # 45.9 (folga 0,8 mm no diametro)
RO_LUVA_A = RI_LUVA_A + 2.0                   # 47.9
H_LUVA_A, H_BATENTE = 12.0, 2.0
Z_CONE0 = H_LUVA_A + H_BATENTE                # 14
H_CONE = 30.0
Z_CONE1 = Z_CONE0 + H_CONE                    # 44
R_CONE_FIM = 28.5                             # degrau de 1,7 mm onde o retificador apoia
R_EXT_SUP = R_FURO + 2.0                      # 32.2
H_RETIF = 25.0
H_LUVA_G = 20.0
H_B1 = Z_CONE1 + H_RETIF + H_LUVA_G           # 89

luva_a = tubo(RI_LUVA_A, RO_LUVA_A, 0, H_LUVA_A)
batente = tubo(R_DUTO, RO_LUVA_A, H_LUVA_A, H_BATENTE)
cone = (cyl(H_CONE, RO_LUVA_A, R_EXT_SUP).translate([0, 0, Z_CONE0]) -
        cyl(H_CONE + 0.02, R_DUTO, R_CONE_FIM).translate([0, 0, Z_CONE0 - 0.01]))
alojamento = tubo(R_FURO, R_EXT_SUP, Z_CONE1, H_RETIF + H_LUVA_G)
b1 = luva_a + batente + cone + alojamento

# ---------------- B2: retificador ----------------
FOLGA_RET = 0.3                               # radial, alem do encolhimento do furo
RO_RET = R_FURO - FOLGA_RET                   # 29.9
RI_RET = RO_RET - 1.6                         # 28.3
N_ALETAS, ESP_ALETA = 6, 1.2
anel = tubo(RI_RET, RO_RET, 0, H_RETIF)
aletas = Manifold()
for k in range(N_ALETAS):
    aletas = aletas + box(RO_RET - 0.3, ESP_ALETA, H_RETIF, 0, -ESP_ALETA / 2, 0).rotate([0, 0, 360 / N_ALETAS * k])
b2 = anel + aletas

def write_stl(path, m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    t = np.asarray(mesh.tri_verts)
    with open(path, "wb") as f:
        f.write(b"levitador".ljust(80, b" "))
        f.write(struct.pack("<I", len(t)))
        for a, b, c in t:
            p = v[[a, b, c]]
            n = np.cross(p[1] - p[0], p[2] - p[0]); n /= np.linalg.norm(n) or 1
            f.write(struct.pack("<12fH", *n, *p.ravel(), 0))

out = sys.argv[1] if len(sys.argv) > 1 else "."
for nome, m in (("funil_parteB1.stl", b1), ("retificador_parteB2.stl", b2)):
    write_stl(os.path.join(out, nome), m)
    print(nome, m.status(), f"{m.volume()*1.24e-3:.1f} g", "bbox", [round(x, 2) for x in m.bounding_box()])
print(f"furo do alojamento O{2*R_FURO:.1f} | retificador O{2*RO_RET:.1f} (folga {FOLGA_RET} por lado) | "
      f"degrau de apoio r {R_CONE_FIM}..{R_FURO} | garrafa apoia no topo do retificador em z={Z_CONE1 + H_RETIF}")
print(f"encaixe na parte A: furo O{2*RI_LUVA_A:.1f} sobre O{2*R_EXT_A:.1f}")
