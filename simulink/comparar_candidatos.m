%% COMPARAR_CANDIDATOS
% Simula a malha fechada com cada candidato de (K_v, tau_v) e compara as
% estatisticas com o voo real final2 (mesmos ganhos e degraus).
clear; clc;
pasta = fileparts(mfilename('fullpath')); cd(pasta);
real_ = ler_ensaio('final2');
criar_modelo_levitador;
load_system('levitador_bola');

% Trechos do voo real (depois da rampa de decolagem), alinhados aos degraus
i1 = find(abs(real_.ref - 0.16) < 1e-6, 1);          % inicio do degrau 13 -> 16
t0 = real_.t(i1) - 22;                               % instante real que equivale a t = 0
k = real_.t >= t0 & real_.t <= t0 + 66;
R.t = real_.t(k) - t0;  R.h = real_.h(k);  R.u = real_.u(k);
fprintf('%-34s %7s %7s %7s %7s %7s %8s\n', '', 'h13', 'h16', 'h13b', 'dp h', 'dp u', 'periodo');
linha('REAL final2', R.t, R.h, R.u);

for candidato = 1:2
    M = [];
    for semente = 1:6
        sem = semente; parametros_levitador; semente = 10*sem;
        out = sim('levitador_bola');
        t = out.h_med.Time; h = squeeze(out.h_med.Data); u = squeeze(out.u.Data);
        M(end+1,:) = estat(t, h, u); %#ok<SAGROW>
    end
    fprintf('%-34s %7.1f %7.1f %7.1f %7.1f %7.1f %8.2f\n', ...
        sprintf('cand. %d: K_v=%.4f tau=%.2f (media 6)', candidato, K_v, tau_v), mean(M,1));
    fprintf('%-34s %7.1f %7.1f %7.1f %7.1f %7.1f %8.2f\n', '   desvio entre sementes', std(M,0,1));
    fprintf('   Ku teorico = %.0f PWM/m, Tu = %.2f s, a = %.1f 1/s\n', Ku, Tu, a);
end
close_system('levitador_bola', 0);

function linha(nome, t, h, u)
    fprintf('%-34s %7.1f %7.1f %7.1f %7.1f %7.1f %8.2f\n', nome, estat(t, h, u));
end
function e = estat(t, h, u)
    % medias de altura por trecho [cm], desvio em torno da media movel de 3 s [cm],
    % desvio do PWM e periodo dominante da oscilacao [s] (0,4 a 4 s)
    seg = @(x, a, b) x(t >= a & t < b);
    r = h - movmean(h, 75);
    x = r(t >= 4 & t < 60); x = x - mean(x);
    nf = 4096; X = abs(fft(x(:).*hann_(numel(x)), nf)).^2; f = (0:nf-1)'/(nf*0.04);
    b = f > 0.25 & f < 2.5; fb = f(b); Xb = movmean(X(b), 9); [~, im] = max(Xb);
    e = [mean(seg(h,8,22)) mean(seg(h,30,44)) mean(seg(h,52,66))]*100;
    e = [e, std(x)*100, std(u(t >= 4 & t < 60)), 1/fb(im)];
end
function w = hann_(n), w = 0.5 - 0.5*cos(2*pi*(0:n-1)'/(n-1)); end
