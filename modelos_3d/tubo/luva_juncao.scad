// Luva de juncao entre as duas garrafas PET (tambem serve de guia de corte)
// Medir o diametro EXTERNO da garrafa com paquimetro e ajustar D_ext.

D_ext  = 60.0;  // diametro externo da garrafa (mm)
folga  = 0.4;   // folga do furo (use o anel de teste que encaixou melhor)
parede = 2.0;   // espessura da luva (mm)
L      = 40;    // comprimento total (20 mm em cada garrafa)
chanf  = 0.8;   // chanfro interno nas bordas, facilita o encaixe
sulco  = 0.6;   // sulco externo no meio: marca onde fica a emenda
$fn    = 360;

ri = (D_ext + folga) / 2;
ro = ri + parede;

rotate_extrude()
    polygon([[ri + chanf, 0], [ro, 0], [ro, L/2 - sulco], [ro - sulco, L/2],
             [ro, L/2 + sulco], [ro, L], [ri + chanf, L], [ri, L - chanf], [ri, chanf]]);
