function r = ler_ensaio(nome)
%LER_ENSAIO Le o ensaio mais recente com esse nome em ../ensaios/dados (modo auto).
%   r.t [s], r.ref [m], r.h [m], r.u [PWM], com t contado do inicio do modo auto.
pasta = fullfile(fileparts(mfilename('fullpath')), '..', 'ensaios', 'dados');
d = dir(fullfile(pasta, [nome '_*.txt']));
[~, i] = max([d.datenum]);
txt = fileread(fullfile(pasta, d(i).name));
tok = regexp(txt, ['t=\s*([\d.]+) s \| ref=\s*([\d.]+) cm \| h=\s*(-?[\d.]+) cm' ...
    '[^\n]*?PWM=\s*([\d.]+) \|[^\n]*\| auto'], 'tokens');
x = str2double(vertcat(tok{:}));
r.t = x(:,1) - x(1,1);  r.ref = x(:,2)/100;  r.h = x(:,3)/100;  r.u = x(:,4);
end
