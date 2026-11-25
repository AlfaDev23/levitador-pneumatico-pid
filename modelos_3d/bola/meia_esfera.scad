// Meia-esfera oca para o levitador (imprimir 2 e colar pela borda)
// Tubo: garrafa PET 500 mL, diametro interno 59,4 mm

D    = 49.5;   // diametro externo da bola (mm) -> ~83% do tubo
t    = 0.45;   // espessura da parede (mm) -> 1 perimetro com bico 0,4
furo = 20;     // diametro do furo no polo (mm), tampar com papel/fita depois
$fn  = 180;

zc = sqrt(pow(D/2, 2) - pow(furo/2, 2));   // altura do corte do furo

difference() {
    sphere(d = D);
    sphere(d = D - 2*t);
    translate([0, 0, -D]) cube(2*D, center = true);       // metade de baixo
    translate([0, 0, zc + D]) cube(2*D, center = true);   // furo no polo
}
