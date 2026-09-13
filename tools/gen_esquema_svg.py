# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Leonardo Roman da Rosa
"""
Gera os dois diagramas de fiacao em SVG (RP2040 e Arduino UNO).

Por que nao e uma captura do simulador: no Wokwi cada modulo puxa o proprio
fio de alimentacao ate a placa, o que da 48 linhas e vira um emaranhado. Aqui
V+, GND e CLK sao BARRAMENTOS -- uma linha grossa que atravessa o desenho,
com derivacoes curtas para cada modulo. Sobram ~18 fios desenhados em vez de
48, que e tambem como a coisa se cabeia de verdade.

FIOS DE SINAL NAO SE CRUZAM. Cada fio de DIO/D0 faz um "Z": sai do modulo,
anda na horizontal numa faixa e chega ao pino da placa. Dois Zs se cruzam
quando o trecho horizontal de um contem o pad ou o pino do outro. Por isso os
pinos da placa foram escolhidos de modo que nenhum trecho horizontal contenha
pad ou pino alheio -- e o script CONFERE isso no fim, segmento a segmento, e
sai com erro se achar cruzamento. (A primeira versao tinha quatro: D4/D5,
A4/A5 e os equivalentes do Pico, mais o fio do display 1 cortando a descida
do CLK.)

Os cruzamentos que sobram sao de fio atravessando BARRAMENTO, inerentes a
desenhar com barramentos: sem bolinha, nao ha ligacao -- a convencao de
qualquer esquema. O unico fio que precisa atravessar outro fio de alimentacao
(o V+ da placa passando pela coluna de GND) ganha uma ponte em arco.

    python tools/gen_esquema_svg.py
"""
import io, os, sys, html

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

N = 6

# ----------------------------------------------------------------- cores
BG      = "#f6f6f2"
TINTA   = "#1a1a1a"
CINZA   = "#6b6b6b"
MOD_F, MOD_S = "#ffffff", "#3a3a3a"
MCU_F, MCU_S = "#e8f0fa", "#1f4e79"
C_V     = "#cc2222"   # alimentacao
C_G     = "#1a1a1a"   # terra
C_CLK   = "#c98a00"   # clock comum dos displays
C_DIO   = "#218c4f"   # dados de cada display
C_D0    = "#1f6fd0"   # saida dos sensores
C_PORTA = "#008b8b"
C_BOTAO = "#d97706"
C_BUZZ  = "#7a4fbf"

# --------------------------------------------------------------- geometria
W, H      = 1780, 1420
DISP_W, DISP_H, PITCH, X0 = 210, 118, 262, 130
DISP_Y    = 122
PAD_DX    = (30, 58, 86, 114)        # 4 pinos do header, da esquerda p/ direita

Y_CLK, Y_VD, Y_GD = 300, 330, 360    # barramentos de cima (displays)

MCU_X0, MCU_X1, MCU_Y0, MCU_Y1 = 300, 1300, 540, 700

# Pinos da placa. Os pads DIO dos displays ficam em x = 188, 450, 712, 974,
# 1236, 1498 e os pads D0 dos sensores em 216, 478, 740, 1002, 1264, 1526.
# Com os pinos abaixo, os trechos horizontais sao [188,400] [450,580]
# [712,760] [940,974] [1120,1236] [1280,1498] em cima (e o analogo embaixo):
# todos disjuntos, e nenhum contem pad ou pino de outro fio.
TOP_PINS  = [400, 580, 760, 940, 1120, 1280]         # DIO 1..6
BOT_PINS  = [400, 580, 760, 940, 1120, 1280]         # D0 1..6
# Faixas alternadas: nao sao necessarias para evitar cruzamento (os trechos ja
# sao disjuntos), mas evitam que dois trechos na mesma altura parecam um fio so.
LANE_DIO  = [412 if i % 2 == 0 else 432 for i in range(N)]
LANE_D0   = [780 if i % 2 == 0 else 800 for i in range(N)]

# O CLK sai pela borda ESQUERDA da placa e sobe por uma coluna propria. Pela
# borda de cima, a descida dele cortaria o fio do display 1, que vem da
# esquerda para um pino a direita.
CLK_Y     = 562
CLK_COL   = 124
ESQ_Y     = (588, 652)                               # V+, GND
LADO_Y    = (572, 620, 668)                          # porta, botao, buzzer

Y_VS, Y_GS = 866, 896                # barramentos de baixo (sensores)
SENS_Y, SENS_H = 940, 100

SPINE_X   = 74                       # coluna de V+; a de GND fica em +26

CTRL_X0, CTRL_X1, CTRL_Y0, CTRL_Y1 = 1380, 1706, 528, 712

# ------------------------------------------------------------------ perfis
PERFIS = {
    "pico": dict(
        saida="cronometro-rasp-pico/docs/fiacao-pico.svg",
        placa="Raspberry Pi Pico  /  RP2040",
        tensao="3,3 V",
        v_rot="3V3", v_pino="3V3 (furo 36)",
        g_pino="GND (furos 3, 8, 13, 18, 23, 28, 38)",
        clk="GP9", dio=["GP10", "GP11", "GP12", "GP13", "GP14", "GP15"],
        sens=["GP2", "GP3", "GP4", "GP5", "GP6", "GP7"],
        largada="GP8", botao="GP21", buzzer="GP16",
        serial="USB, ou UART0 em GP0/GP1",
        notas=[
            "Os nomes sao GPIO, nao a posicao do furo. A tabela GPIO - furo das",
            "duas placas (Pico oficial e RP2040 roxa) esta em docs/pinout.md.",
            "ATENCAO: tudo em 3,3 V, displays E sensores. TM1637 e TCRT5000 tem",
            "pull-up para o proprio VCC: em 5 V, poem 5 V num pino que nao tolera.",
        ],
    ),
    "uno": dict(
        saida="cronometro-arduino/docs/fiacao-arduino.svg",
        placa="Arduino UNO  /  Nano  (ATmega328P)",
        tensao="5 V",
        v_rot="5V", v_pino="5V",
        g_pino="GND (qualquer um dos tres)",
        clk="D3", dio=["D4", "D5", "D6", "D7", "D8", "D9"],
        sens=["A0", "A1", "A2", "A3", "A4", "A5"],
        largada="D2", botao="D11", buzzer="D10",
        serial="USB, 115200",
        notas=[
            "Os sensores TEM que ficar em A0..A5, nesta ordem: sao a PORTC",
            "inteira, e so assim os seis cabem numa unica interrupcao de mudanca",
            "de pino (PCINT1). O 328P so tem duas interrupcoes externas (D2/D3).",
            "A largada TEM que ser D2 (INT0). Sobram livres so D12 e D13.",
        ],
    ),
}

# ------------------------------------------------------------------ helpers
def esc(t):
    return html.escape(str(t), quote=False)

class Svg:
    def __init__(self):
        self.o = []
        self.fios = []          # (rede, pontos) dos fios de SINAL, p/ conferir
    def add(self, s):
        self.o.append(s)
    def rect(self, x, y, w, h, fill, stroke, rx=6, sw=1.6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
    def txt(self, x, y, t, size=13, fill=TINTA, anchor="start", weight="normal",
            family="DejaVu Sans, Verdana, Arial, sans-serif"):
        self.add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
                 f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">'
                 f'{esc(t)}</text>')
    def d(self, dados, cor, sw=2.4):
        self.add(f'<path d="{dados}" fill="none" stroke="{cor}" stroke-width="{sw}" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
    def path(self, pts, cor, sw=2.4, rede=None):
        self.d(" ".join(("M" if i == 0 else "L") + f"{x},{y}"
                        for i, (x, y) in enumerate(pts)), cor, sw)
        if rede:
            self.fios.append((rede, pts))
    def linha(self, x1, y1, x2, y2, cor, sw=2.4):
        self.path([(x1, y1), (x2, y2)], cor, sw)
    def no(self, x, y, cor, r=4.2):          # bolinha de juncao
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{cor}"/>')
    def pad(self, x, y, cor=MOD_S):          # pino de header
        self.add(f'<rect x="{x-4.5}" y="{y-4.5}" width="9" height="9" rx="1.5" '
                 f'fill="#ffffff" stroke="{cor}" stroke-width="1.6"/>')
    def ponte(self, x0, x1, y, xc, cor, r=6):
        """Linha horizontal de x0 a x1 que passa POR CIMA de uma vertical em xc."""
        a, b = (xc + r, xc - r) if x0 > x1 else (xc - r, xc + r)
        varre = 0 if x0 > x1 else 1          # arco sempre para cima
        self.d(f"M{x0},{y} L{a},{y} A{r},{r} 0 0 {varre} {b},{y} L{x1},{y}", cor)

# ------------------------------------------------------- conferencia
def cruzamentos(fios):
    """Pares de fios de redes diferentes que se cruzam ou correm sobrepostos."""
    segs = [(rede, a, b) for rede, pts in fios for a, b in zip(pts, pts[1:])]
    achados = []
    for i, (ra, (ax1, ay1), (ax2, ay2)) in enumerate(segs):
        for rb, (bx1, by1), (bx2, by2) in segs[i + 1:]:
            if ra == rb:
                continue
            ah, bh = ay1 == ay2, by1 == by2
            if ah and bh:
                if ay1 == by1 and max(min(ax1, ax2), min(bx1, bx2)) < min(max(ax1, ax2), max(bx1, bx2)):
                    achados.append((ra, rb, "horizontais sobrepostas", ay1))
            elif not ah and not bh:
                if ax1 == bx1 and max(min(ay1, ay2), min(by1, by2)) < min(max(ay1, ay2), max(by1, by2)):
                    achados.append((ra, rb, "verticais sobrepostas", ax1))
            else:
                (hx1, hy, hx2), (vx, vy1, vy2) = (((ax1, ay1, ax2), (bx1, by1, by2)) if ah
                                                  else ((bx1, by1, bx2), (ax1, ay1, ay2)))
                if min(hx1, hx2) < vx < max(hx1, hx2) and min(vy1, vy2) < hy < max(vy1, vy2):
                    achados.append((ra, rb, "cruzamento", (vx, hy)))
    return achados

def _teste_do_conferidor():
    # Os antigos D4/D5: o trecho horizontal de um contem o pad do outro. Se o
    # conferidor nao achar este, ele nao prova nada quando diz "zero".
    ruins = [("D4", [(188, 240), (188, 402), (500, 402), (500, 540)]),
             ("D5", [(450, 240), (450, 418), (650, 418), (650, 540)])]
    assert len(cruzamentos(ruins)) == 2, "conferidor nao pegou os cruzamentos conhecidos"

# --------------------------------------------------------------- desenho
def gera(perfil):
    p = PERFIS[perfil]
    s = Svg()
    s.add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
          f'viewBox="0 0 {W} {H}">')
    # O script e software (GPL-3.0); o DESENHO que ele produz e hardware, e
    # segue a licenca de hardware do projeto, como no Pong.
    s.add("<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->")
    s.add("<!-- Copyright (C) 2026 Leonardo Roman da Rosa -->")
    s.rect(0, 0, W, H, BG, BG, rx=0, sw=0)

    # ------------------------------------------------------------- titulo
    s.txt(40, 52, "CRONOMETRO HOT WHEELS - 6 PISTAS", 27, TINTA, weight="bold")
    s.txt(40, 80, f"Ligacoes para {p['placa']}   -   tudo em {p['tensao']}", 16, CINZA)
    s.txt(W - 40, 52, "diagrama de fiacao", 15, CINZA, anchor="end")
    s.txt(W - 40, 74, "gerado por tools/gen_esquema_svg.py", 12, CINZA, anchor="end")
    s.txt(W - 40, 94, "desenho sob CERN-OHL-S-2.0", 12, CINZA, anchor="end")

    xs = [X0 + PITCH * i for i in range(N)]
    xg = SPINE_X + 26                    # coluna de GND

    # ---------------------------------------------------- barramentos (V+/GND)
    # Colunas de alimentacao a esquerda, ligando os barramentos de cima e de baixo.
    s.linha(SPINE_X, Y_VD, SPINE_X, Y_VS, C_V, 4.5)
    s.linha(xg, Y_GD, xg, Y_GS, C_G, 4.5)
    for y, cor, rot in ((Y_VD, C_V, p["v_rot"]), (Y_GD, C_G, "GND"),
                        (Y_VS, C_V, p["v_rot"]), (Y_GS, C_G, "GND")):
        s.linha(SPINE_X if cor == C_V else xg, y, xs[-1] + DISP_W, y, cor, 4.5)
        s.txt(SPINE_X - 8, y + 5, rot, 13, cor, anchor="end", weight="bold")
    s.no(SPINE_X, Y_VD, C_V); s.no(SPINE_X, Y_VS, C_V)
    s.no(xg, Y_GD, C_G); s.no(xg, Y_GS, C_G)

    # Barramento de CLK (so os displays). Comeca na coluna por onde o CLK sobe
    # da placa, a esquerda do display 1.
    s.linha(CLK_COL, Y_CLK, xs[-1] + DISP_W, Y_CLK, C_CLK, 4.5)

    # -------------------------------------------------------------- displays
    for i, x in enumerate(xs):
        s.rect(x, DISP_Y, DISP_W, DISP_H, MOD_F, MOD_S)
        s.txt(x + DISP_W / 2, DISP_Y + 26, f"PISTA {i+1}", 15, TINTA,
              anchor="middle", weight="bold")
        s.txt(x + DISP_W / 2, DISP_Y + 45, "display TM1637", 12, CINZA, anchor="middle")
        for dg in range(4):
            dx = x + 46 + dg * 32
            s.rect(dx, DISP_Y + 58, 24, 40, "#111318", "#111318", rx=3, sw=1)
            s.txt(dx + 12, DISP_Y + 87, "8", 27, "#37d67a", anchor="middle",
                  family="DejaVu Sans Mono, Consolas, monospace")
        yb = DISP_Y + DISP_H
        for k, (nome, cor) in enumerate((("CLK", C_CLK), ("DIO", C_DIO),
                                         ("GND", C_G), (p["v_rot"], C_V))):
            px = x + PAD_DX[k]
            s.pad(px, yb)
            # Rotulo DENTRO da caixa, acima do pino: a derivacao desce do pino,
            # e embaixo dele o texto seria atravessado pela propria linha.
            s.txt(px, yb - 9, nome, 10, cor, anchor="middle", weight="bold")

        s.path([(x + PAD_DX[0], yb), (x + PAD_DX[0], Y_CLK)], C_CLK, rede="CLK")
        s.no(x + PAD_DX[0], Y_CLK, C_CLK)
        s.path([(x + PAD_DX[3], yb), (x + PAD_DX[3], Y_VD)], C_V)
        s.no(x + PAD_DX[3], Y_VD, C_V)
        s.path([(x + PAD_DX[2], yb), (x + PAD_DX[2], Y_GD)], C_G)
        s.no(x + PAD_DX[2], Y_GD, C_G)

        # DIO: desce ate a faixa, anda ate o pino da placa e desce nele
        xd, faixa, xp = x + PAD_DX[1], LANE_DIO[i], TOP_PINS[i]
        s.path([(xd, yb), (xd, faixa), (xp, faixa), (xp, MCU_Y0)], C_DIO, rede=p["dio"][i])
        s.txt(xd + 7, 394, p["dio"][i], 11, C_DIO, weight="bold")

    # CLK da placa: pela borda esquerda, subindo pela propria coluna.
    s.path([(MCU_X0, CLK_Y), (CLK_COL, CLK_Y), (CLK_COL, Y_CLK)], C_CLK, rede="CLK")
    s.no(CLK_COL, Y_CLK, C_CLK)
    s.txt(CLK_COL + 10, CLK_Y - 8, "CLK  " + p["clk"], 11, C_CLK, weight="bold")

    # Rotulos dos barramentos na ponta direita, onde nenhuma derivacao cruza.
    xe = xs[-1] + DISP_W + 10
    s.txt(xe, Y_CLK + 4, "CLK  " + p["clk"], 11.5, C_CLK, weight="bold")
    for y, cor, rot in ((Y_VD, C_V, p["v_rot"]), (Y_GD, C_G, "GND"),
                        (Y_VS, C_V, p["v_rot"]), (Y_GS, C_G, "GND")):
        s.txt(xe, y + 4, rot, 11.5, cor, weight="bold")

    # --------------------------------------------------------------- sensores
    ys = SENS_Y
    for i, x in enumerate(xs):
        s.rect(x, ys, DISP_W, SENS_H, MOD_F, MOD_S)
        s.txt(x + DISP_W / 2, ys + 60, f"PISTA {i+1}", 15, TINTA,
              anchor="middle", weight="bold")
        s.txt(x + DISP_W / 2, ys + 80, "sensor TCRT5000", 12, CINZA, anchor="middle")
        for k, (nome, cor) in enumerate((("VCC", C_V), ("GND", C_G),
                                         ("D0", C_D0), ("A0", CINZA))):
            px = x + PAD_DX[k]
            s.pad(px, ys)
            # Rotulo DENTRO da caixa, abaixo do pino: aqui a derivacao sobe.
            s.txt(px, ys + 21, nome, 10, cor, anchor="middle", weight="bold")
        s.txt(x + PAD_DX[3], ys + 34, "solto", 9.5, CINZA, anchor="middle")

        s.path([(x + PAD_DX[0], ys), (x + PAD_DX[0], Y_VS)], C_V)
        s.no(x + PAD_DX[0], Y_VS, C_V)
        s.path([(x + PAD_DX[1], ys), (x + PAD_DX[1], Y_GS)], C_G)
        s.no(x + PAD_DX[1], Y_GS, C_G)

        xd, faixa, xp = x + PAD_DX[2], LANE_D0[i], BOT_PINS[i]
        s.path([(xd, ys), (xd, faixa), (xp, faixa), (xp, MCU_Y1)], C_D0, rede=p["sens"][i])
        s.txt(xd + 7, 852, p["sens"][i], 11, C_D0, weight="bold")

    # ------------------------------------------------------------------- MCU
    s.rect(MCU_X0, MCU_Y0, MCU_X1 - MCU_X0, MCU_Y1 - MCU_Y0, MCU_F, MCU_S, rx=10, sw=2.4)
    s.txt((MCU_X0 + MCU_X1) / 2, MCU_Y0 + 66, p["placa"], 22, MCU_S,
          anchor="middle", weight="bold")
    s.txt((MCU_X0 + MCU_X1) / 2, MCU_Y0 + 92, "os nomes dos pinos sao o que vale; "
          "a posicao do furo esta em docs/pinout.md", 12, CINZA, anchor="middle")
    s.txt((MCU_X0 + MCU_X1) / 2, MCU_Y0 + 130, f"log serial: {p['serial']}", 12,
          CINZA, anchor="middle")

    for i, x in enumerate(TOP_PINS):
        s.pad(x, MCU_Y0, MCU_S)
        s.txt(x, MCU_Y0 + 22, p["dio"][i], 11, MCU_S, anchor="middle", weight="bold")
    for i, x in enumerate(BOT_PINS):
        s.pad(x, MCU_Y1, MCU_S)
        s.txt(x, MCU_Y1 - 12, p["sens"][i], 11, MCU_S, anchor="middle", weight="bold")
    s.pad(MCU_X0, CLK_Y, MCU_S)
    s.txt(MCU_X0 + 14, CLK_Y + 5, p["clk"], 11.5, C_CLK, weight="bold")

    # Alimentacao da placa, pelas colunas da esquerda. O V+ tem que atravessar
    # a coluna de GND para chegar a dele: la vai a ponte em arco.
    yv, ygp = ESQ_Y
    s.pad(MCU_X0, yv, MCU_S)
    s.txt(MCU_X0 + 14, yv + 5, p["v_pino"], 11.5, C_V, weight="bold")
    s.ponte(MCU_X0, SPINE_X, yv, xg, C_V)
    s.no(SPINE_X, yv, C_V)
    s.pad(MCU_X0, ygp, MCU_S)
    s.txt(MCU_X0 + 14, ygp + 5, p["g_pino"], 11.5, C_G, weight="bold")
    s.path([(MCU_X0, ygp), (xg, ygp)], C_G)
    s.no(xg, ygp, C_G)

    # ------------------------------------------------------------- controles
    s.rect(CTRL_X0, CTRL_Y0, CTRL_X1 - CTRL_X0, CTRL_Y1 - CTRL_Y0,
           "#ffffff", CINZA, rx=8, sw=1.4, dash="6 4")
    s.txt(CTRL_X0 + 12, CTRL_Y0 + 22, "PAINEL / CABINE", 12, CINZA, weight="bold")
    ctrl = ((p["largada"], "microswitch da PORTA", C_PORTA),
            (p["botao"],   "botao TESTE (opcional)", C_BOTAO),
            (p["buzzer"],  "buzzer passivo (opcional)", C_BUZZ))
    for k, (pino, rot, cor) in enumerate(ctrl):
        y = LADO_Y[k]
        s.pad(MCU_X1, y, MCU_S)
        s.path([(MCU_X1, y), (CTRL_X0 + 18, y)], cor, rede=pino)
        s.txt(MCU_X1 + 14, y - 8, pino, 11, cor, weight="bold")
        s.no(CTRL_X0 + 18, y, cor)
        s.txt(CTRL_X0 + 28, y + 5, rot, 12, TINTA)
    s.txt(CTRL_X0 + 12, CTRL_Y1 - 14, "o outro lado dos tres vai ao GND", 11, CINZA)

    # --------------------------------------------------------- rodape: legenda
    ry = 1092
    s.rect(40, ry, W - 80, 306, "#ffffff", CINZA, rx=8, sw=1.2)
    s.txt(62, ry + 30, "COMO LER", 14, TINTA, weight="bold")
    leg = ((C_V, f"{p['v_rot']} - barramento de alimentacao"),
           (C_G, "GND - barramento de terra"),
           (C_CLK, "CLK - um fio so, passa nos seis displays"),
           (C_DIO, "DIO - um fio por display"),
           (C_D0, "D0 - um fio por sensor"))
    for k, (cor, rot) in enumerate(leg):
        y = ry + 58 + k * 26
        s.linha(62, y, 104, y, cor, 4.5)
        s.txt(114, y + 5, rot, 12.5, TINTA)
    y = ry + 58 + len(leg) * 26
    s.no(83, y, TINTA)
    s.txt(114, y + 5, "bolinha = fios ligados;  cruzamento sem bolinha = nao ligados",
          12.5, TINTA)
    y += 26
    s.linha(83, y - 11, 83, y + 11, C_G, 2.4)
    s.ponte(62, 104, y, 83, C_V)
    s.txt(114, y + 5, "arco = um fio passa por cima do outro, sem ligar", 12.5, TINTA)

    s.txt(700, ry + 30, "RESUMO DAS LIGACOES", 14, TINTA, weight="bold")
    tab = [("displays TM1637", f"CLK {p['clk']} (comum) + DIO "
                               f"{p['dio'][0]}..{p['dio'][-1]}, um por pista"),
           ("sensores TCRT5000", f"D0 em {p['sens'][0]}..{p['sens'][-1]}, um por "
                                 f"pista. O A0 do modulo fica solto"),
           ("porta de largada", f"{p['largada']}, contato para GND"),
           ("botao TESTE", f"{p['botao']}, para GND (opcional)"),
           ("buzzer", f"{p['buzzer']}, para GND (opcional)"),
           ("alimentacao", f"{p['v_pino']} e {p['g_pino']}")]
    for k, (a, b) in enumerate(tab):
        y = ry + 58 + k * 26
        s.txt(700, y + 5, a, 12.5, TINTA, weight="bold")
        s.txt(880, y + 5, b, 12.5, TINTA)
    for k, nota in enumerate(p["notas"]):
        s.txt(700, ry + 222 + k * 19, nota, 11.5, "#8a3b00")

    s.add("</svg>")
    saida = p["saida"]
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    io.open(saida, "w", encoding="utf-8", newline="\n").write("\n".join(s.o) + "\n")
    return saida, s.fios

if __name__ == "__main__":
    import xml.dom.minidom as md
    _teste_do_conferidor()
    ok = True
    for perfil in PERFIS:
        arq, fios = gera(perfil)
        md.parse(arq)                    # falha alto se o SVG nao for XML valido
        achados = cruzamentos(fios)
        print(f"{arq}  ({os.path.getsize(arq)} bytes, XML valido, {len(fios)} fios de sinal, "
              + ("nenhum cruzamento entre eles)" if not achados
                 else f"{len(achados)} CRUZAMENTOS)"))
        for a in achados:
            print("    ", a)
        ok = ok and not achados
    sys.exit(0 if ok else 1)
