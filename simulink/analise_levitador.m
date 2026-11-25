%% ANALISE_LEVITADOR
% Resultados e graficos do relatorio com os parametros identificados:
%   modelagem (FT, polos, degrau, Bode, LGR), ganho critico teorico,
%   malha fechada com o PID gravado no Uno e comparacao Simulink x voo real.
% Os graficos sao salvos na pasta "figuras".

clear; close all; clc;
pasta = fileparts(mfilename('fullpath')); cd(pasta);
candidato = 1; parametros_levitador;
if ~exist('figuras', 'dir'), mkdir figuras; end
salvar = @(f, nome) exportgraphics(f, fullfile('figuras', [nome '.png']), 'Resolution', 200);
azul = [42 120 214]/255; tinta = [11 11 11]/255; cinza = [137 135 129]/255;
set(groot, 'defaultAxesFontSize', 10, 'defaultFigureColor', 'w', 'defaultFigureVisible', 'off');

%% 1) Modelo
fprintf('===== MODELO (h0 = %.0f cm) =====\n', 100*h0);
fprintf('K_v = %.4f (m/s)/PWM | tau = %.2f s | v0 = %.2f m/s | a = %.2f 1/s | obstrucao = %.0f%%\n', ...
    K_v, tau_v, v0, a, 100*obstrucao);
G
fprintf('Polos de G(s): %s\n', mat2str(pole(G).', 4));
fprintf('Polos em h = %.0f cm: %s\n', 100*h1, mat2str(pole(G_baixo).', 4));

f = figure; step(G, 5); grid on; ylabel('Altura [m]');
title('Degrau unitário de PWM em malha aberta (14 cm): sistema integrador');
salvar(f, '01_degrau_malha_aberta');
f = figure; pzmap(G, 'b', G_baixo, 'r'); legend('14 cm (integrador)', '9 cm (polo instável)');
title('Polos do modelo linear em duas alturas'); salvar(f, '02_polos_zeros');

%% 2) Malha aberta com o PID do Uno (atraso: mediana de 3 + retencao do PWM)
atraso = Ts + Ts/2;
C = pid(Kp, Ki, Kd, 1/N_filtro);
Lma = C*G*exp(-s*atraso);
[Gm, Pm, ~, wcp] = margin(Lma);
fprintf('\nPID do Uno: Kp=%g Ki=%g Kd=%g | margem de fase = %.1f graus em %.2f rad/s | margem de ganho = %.1f dB\n', ...
    Kp, Ki, Kd, Pm, wcp, 20*log10(Gm));
f = figure; margin(Lma, {0.01, 40}); grid on; salvar(f, '03_bode_margens');
f = figure; rlocus(C/Kp*pade(G*exp(-s*atraso), 2)); xlim([-40 15]); ylim([-25 25]);
title('Lugar das raízes com o PID do Uno (K_p variando, K_i/K_p e K_d/K_p fixos)');
salvar(f, '04_lugar_das_raizes');

%% 3) Ganho critico teorico (Routh) - NAO foi medido na planta
fprintf('\nRouth (teorico): Ku = %.0f PWM/m | Tu = %.2f s\n', Ku, Tu);
f = figure; step(feedback(Ku*G, 1), 15); grid on; ylabel('Altura [m]');
title(sprintf('Teórico: K_p = K_u = %.0f, oscilação sustentada (T_u = %.2f s)', Ku, Tu));
salvar(f, '05_oscilacao_critica');

%% 4) Malha fechada linear
T = feedback(pade(Lma, 2), 1);
% no codigo a derivada atua so na medicao
Gd = pade(G*exp(-s*atraso), 2);
Cpi = pid(Kp, Ki); Cd = pid(0, 0, Kd, 1/N_filtro);
T2 = minreal(feedback(Cpi*feedback(Gd, Cd), 1), 1e-4);
fprintf('Estavel (linear): %d | ', isstable(T2)); S = stepinfo(T2);
fprintf('sobressinal = %.0f%% | subida = %.2f s | acomodacao = %.1f s\n', S.Overshoot, S.RiseTime, S.SettlingTime);
f = figure; step(T2, 20); grid on; ylabel('Altura normalizada');
title('Malha fechada linear com o PID do Uno (14 cm)'); salvar(f, '06_malha_fechada_linear');

%% 5) Simulink x voo real
criar_modelo_levitador; load_system('levitador_bola');
r = ler_ensaio('final2'); i1 = find(abs(r.ref - 0.16) < 1e-6, 1); t0 = r.t(i1) - 22;
k = r.t >= t0 & r.t <= t0 + t_final;
out = sim('levitador_bola');
ts = out.h_med.Time; hs = squeeze(out.h_med.Data); us = squeeze(out.u.Data);
sd0 = turb_sd; rd0 = ruido_s; turb_sd = 0; ruido_s = 1e-12;
limpo = sim('levitador_bola'); turb_sd = sd0; ruido_s = rd0;
tl = limpo.h.Time; hl = squeeze(limpo.h.Data);
fprintf('\n%-10s %8s %8s\n', '', 'real', 'Simulink');
nomes = {'13 cm', '16 cm', '13 cm (fim)'}; lim = [8 22; 30 44; 52 66];
for j = 1:3
    qr = r.t - t0 >= lim(j,1) & r.t - t0 < lim(j,2); qs = ts >= lim(j,1) & ts < lim(j,2);
    fprintf('%-12s %5.1f+-%.1f  %5.1f+-%.1f\n', nomes{j}, 100*mean(r.h(qr)), 100*std(r.h(qr)), 100*mean(hs(qs)), 100*std(hs(qs)));
end
f = figure('Position', [100 100 1000 700]); tl_ = tiledlayout(3, 1, 'TileSpacing', 'compact');
nexttile; plot(r.t(k) - t0, 100*r.h(k), 'Color', azul, 'LineWidth', 1.2); hold on; grid on;
stairs(r.t(k) - t0, 100*r.ref(k), '--', 'Color', tinta, 'LineWidth', 1.1);
ylim([0 24]); xlim([0 t_final]); ylabel('Altura [cm]'); title('Sistema real (voo final2)');
legend('Altura medida', 'Referência', 'Location', 'northeast', 'Orientation', 'horizontal', 'Box', 'off');
nexttile; plot(ts, 100*hs, 'Color', azul, 'LineWidth', 1.2); hold on; grid on;
stairs(ts, 100*squeeze(out.ref.Data), '--', 'Color', tinta, 'LineWidth', 1.1);
ylim([0 24]); xlim([0 t_final]); ylabel('Altura [cm]'); title('Simulink com turbulência e ruído do sensor');
nexttile; plot(tl, 100*hl, 'Color', azul, 'LineWidth', 1.4); hold on; grid on;
stairs(ts, 100*squeeze(out.ref.Data), '--', 'Color', tinta, 'LineWidth', 1.1);
ylim([0 24]); xlim([0 t_final]); ylabel('Altura [cm]'); xlabel('Tempo [s]'); title('Simulink sem turbulência nem ruído');
salvar(f, '07_simulink_x_real');

f = figure('Position', [100 100 900 420]);
open_system('levitador_bola');
print('-slevitador_bola', '-dpng', '-r200', fullfile('figuras', '08_diagrama_simulink.png'));
print('-slevitador_bola/Bola (nao linear)', '-dpng', '-r200', fullfile('figuras', '09_subsistema_bola.png'));
close_system('levitador_bola', 0);
if exist(fullfile('figuras', '07_simulink_nao_linear.png'), 'file')   % antiga, copia em versao_valores_supostos
    delete(fullfile('figuras', '07_simulink_nao_linear.png'));
end
fprintf('\nGraficos salvos em %s\n', fullfile(pasta, 'figuras'));
