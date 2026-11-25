import sys, os, struct
import numpy as np
from manifold3d import Manifold

SEG = 256
cyl = lambda h, r, r2=-1: Manifold.cylinder(h, r, r2, circular_segments=SEG)

def tubo(ri, ro, z0, h):
    return (cyl(h, ro) - cyl(h + 2, ri).translate([0, 0, -1])).translate([0, 0, z0])

def box(sx, sy, sz, x=0, y=0, z=0):
    return Manifold.cube([sx, sy, sz]).translate([x, y, z])

# ---------------- medidas ----------------
D_MOTOR = 22.4
L_MOTOR = 40.0
FACE_HELICE = 38.7      # face do motor -> parte de baixo da helice (informado)
H_HELICE = 15.7
D_HELICE = 80.0
D_GARRAFA_INT, D_GARRAFA_EXT, FOLGA = 59.4, 60.0, 0.4

# ---------------- PARTE A: base + duto ----------------
Z_MOTOR = 30.0                          # traseira do motor
Z_FACE = Z_MOTOR + L_MOTOR              # 70
Z_HEL0 = Z_FACE + FACE_HELICE           # 108.7
Z_HEL1 = Z_HEL0 + H_HELICE              # 124.4
H_A = 150.0                             # ~25 mm de margem para subir a helice no mandril
R_DUTO = (D_HELICE + 6.0) / 2           # 43 -> folga radial 3 mm
R_EXT = R_DUTO + 2.5                    # 44.5
R_CL_I = (D_MOTOR + 0.4) / 2            # 11.4
R_CL_O = R_CL_I + 2.4                   # 13.8
Z_CL_TOP = 60.0
Z_FIN_TOP = 30.0
JAN_Z0, JAN_Z1, JAN_L = 8.0, 85.0, 30.0

parede = tubo(R_DUTO, R_EXT, 0, H_A)
for k in range(6):   # 6 janelas de entrada de ar, centradas entre as colunas
    j = box(30, JAN_L, JAN_Z1 - JAN_Z0, 30, -JAN_L / 2, JAN_Z0)
    parede = parede - j.rotate([0, 0, 30 + 60 * k])

braco = tubo(R_CL_I, R_CL_O, 0, Z_CL_TOP)
for ang in (60, 180, 300):              # 2 passagens de fio + recortes entre aletas embaixo
    braco = braco - box(10, 8, 21, R_CL_I - 2, -4, 3).rotate([0, 0, ang])
braco = braco - box(6, 1.5, Z_CL_TOP - 34, R_CL_I - 2, -0.75, 34).rotate([0, 0, 60])   # fenda p/ apertar
aletas = Manifold()
for ang in (0, 120, 240):               # aletas verticais ligando abracadeira ao duto
    aletas = aletas + box(R_DUTO - R_CL_O + 1.0, 2.4, Z_FIN_TOP, R_CL_O - 0.5, -1.2, 0).rotate([0, 0, ang])
apoios = Manifold()
for ang in (60, 180, 300):              # 3 apoios onde a traseira do motor encosta
    apoios = apoios + box(R_CL_I - 7.5 + 0.5, 4, 3, 7.5, -2, Z_MOTOR - 3).rotate([0, 0, ang])
sulco = tubo(R_CL_O - 0.6, R_CL_O + 1, 48, 5)   # canal para a abracadeira de nylon
flange = tubo(R_DUTO, 60.0, 0, 3.0)    # aba para parafusar na base de MDF (torre fica alta)
for ang in (30, 150, 270):
    flange = flange - cyl(5, 1.8).translate([53, 0, -1]).rotate([0, 0, ang])
parte_a = parede + braco + aletas + apoios + flange - sulco

# ---------------- PARTE B: funil + retificador + encaixe da garrafa ----------------
RI_LUVA_A = R_EXT + 0.2                 # 44.7 desliza por fora do duto
RO_LUVA_A = RI_LUVA_A + 2.0
H_LUVA_A, H_BATENTE = 12.0, 2.0
Z_CONE0 = H_LUVA_A + H_BATENTE          # 14
H_CONE = 30.0
Z_CONE1 = Z_CONE0 + H_CONE              # 44
R_TUBO = D_GARRAFA_INT / 2              # 29.7
R_LUVA_G_I = (D_GARRAFA_EXT + FOLGA) / 2  # 30.2
R_LUVA_G_O = R_LUVA_G_I + 2.0           # 32.2
H_RETIF = 25.0
Z_RET1 = Z_CONE1 + H_RETIF              # 69
H_LUVA_G = 20.0
H_B = Z_RET1 + H_LUVA_G                 # 89

luva_a = tubo(RI_LUVA_A, RO_LUVA_A, 0, H_LUVA_A)
batente = tubo(R_DUTO, RO_LUVA_A, H_LUVA_A, H_BATENTE)
cone = (cyl(H_CONE, RO_LUVA_A, R_LUVA_G_O).translate([0, 0, Z_CONE0]) -
        cyl(H_CONE + 0.02, R_DUTO, R_TUBO).translate([0, 0, Z_CONE0 - 0.01]))
retif_parede = tubo(R_TUBO, R_LUVA_G_O, Z_CONE1, H_RETIF)
# Aletas nascem na parede do cone e sobem para o centro a 45 graus -> imprimem sem suporte
envelope = (cyl(H_CONE, RO_LUVA_A, R_LUVA_G_O).translate([0, 0, Z_CONE0]) +
            cyl(H_RETIF, R_LUVA_G_O).translate([0, 0, Z_CONE1]))
abaixo_45 = cyl(R_DUTO, R_DUTO, 0).translate([0, 0, Z_CONE0])   # cone com apice no eixo
retif_aletas = Manifold()
for k in range(6):
    a = box(RO_LUVA_A + 1, 1.2, Z_RET1 - Z_CONE0, 0, -0.6, Z_CONE0).rotate([0, 0, 60 * k])
    retif_aletas = retif_aletas + ((a ^ envelope) - abaixo_45)
luva_g = tubo(R_LUVA_G_I, R_LUVA_G_O, Z_RET1, H_LUVA_G)
parte_b = luva_a + batente + cone + retif_parede + retif_aletas + luva_g

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

out = sys.argv[1]
for nome, m in (("base_motor_duto_parteA.stl", parte_a), ("funil_retificador_parteB.stl", parte_b)):
    write_stl(os.path.join(out, nome), m)
    bb = m.bounding_box()
    print(nome, m.status(), f"{m.volume()*1.24e-3:.0f} g (solido)", "bbox", [round(x, 1) for x in bb])
print(f"motor {Z_MOTOR}-{Z_FACE}, helice {Z_HEL0:.1f}-{Z_HEL1:.1f}, duto liso a partir de z={JAN_Z1}, topo A={H_A}")
print(f"area janelas {6*JAN_L*(JAN_Z1-JAN_Z0):.0f} mm2 vs duto {np.pi*R_DUTO**2:.0f} mm2")
print(f"altura total montada ~{H_A - H_LUVA_A + H_B:.0f} mm ate a borda da garrafa")
