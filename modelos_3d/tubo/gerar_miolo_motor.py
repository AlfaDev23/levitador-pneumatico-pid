"""Miolo de reposicao da parte A: abracadeira do motor + 3 aletas com sapatas para colar no duto.

Motor real: 27,3 mm de diametro. Furos impressos em FDM saem ~0,2-0,5 mm menores que o
modelo, entao o furo tem 28,1 mm (27,3 + 0,8 de folga) e a abracadeira e uma pinca (3 fendas + abracadeira de nylon), entao folga a mais nao prejudica.
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

D_MOTOR = 27.3
FOLGA_FURO = 0.8                 # compensa o furo que encolhe na impressao
R_CL_I = (D_MOTOR + FOLGA_FURO) / 2     # 14.05 -> furo 28,1 mm
R_CL_O = R_CL_I + 2.4                    # 16.45
Z_MOTOR, Z_CL_TOP, Z_FIN_TOP = 30.0, 60.0, 30.0
R_DUTO = 43.0                    # raio interno do duto da parte A (O86)
R_SAP_O = R_DUTO - 0.2           # sapata encosta na parede, com folga para descer pelo duto
R_SAP_I = R_SAP_O - 1.6
LARG_SAP = 10.0
CHANFRO = 1.0

abracadeira = tubo(R_CL_I, R_CL_O, 0, Z_CL_TOP)
abracadeira = abracadeira - cyl(CHANFRO + 0.01, R_CL_I, R_CL_I + CHANFRO).translate([0, 0, Z_CL_TOP - CHANFRO])
for ang in (60, 180, 300):
    abracadeira = abracadeira - box(10, 8, 21, R_CL_I - 2, -4, 3).rotate([0, 0, ang])            # passagem dos fios
    abracadeira = abracadeira - box(6, 1.5, Z_CL_TOP - 33 + 1, R_CL_I - 2, -0.75, 33).rotate([0, 0, ang])  # fendas da pinca
sulco = tubo(R_CL_O - 0.6, R_CL_O + 1, 52, 5)            # canal da abracadeira de nylon

aletas = Manifold()
for ang in (0, 120, 240):
    aleta = box(R_SAP_I - R_CL_O + 1.0, 2.4, Z_FIN_TOP, R_CL_O - 0.5, -1.2, 0)
    sapata = tubo(R_SAP_I, R_SAP_O, 0, Z_FIN_TOP) ^ box(10, LARG_SAP, Z_FIN_TOP, R_SAP_I - 3, -LARG_SAP / 2, 0)
    aletas = aletas + (aleta + sapata).rotate([0, 0, ang])

apoios = Manifold()
for ang in (60, 180, 300):
    apoios = apoios + box(R_CL_I - 10.0 + 0.5, 4, 3, 10.0, -2, Z_MOTOR - 3).rotate([0, 0, ang])

miolo = abracadeira + aletas + apoios - sulco

def write_stl(path, m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    t = np.asarray(mesh.tri_verts)
    with open(path, "wb") as f:
        f.write(b"miolo motor".ljust(80, b" "))
        f.write(struct.pack("<I", len(t)))
        for a, b, c in t:
            p = v[[a, b, c]]
            n = np.cross(p[1] - p[0], p[2] - p[0]); n /= np.linalg.norm(n) or 1
            f.write(struct.pack("<12fH", *n, *p.ravel(), 0))

out = sys.argv[1] if len(sys.argv) > 1 else "."
write_stl(os.path.join(out, "miolo_motor_reposicao.stl"), miolo)
print(miolo.status(), f"{miolo.volume()*1.24e-3:.1f} g", "bbox", [round(x, 2) for x in miolo.bounding_box()])
