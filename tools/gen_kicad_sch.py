# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Leonardo Roman da Rosa
"""
Gera os esquemas do KiCad 10 das duas versoes do cronometro:

    cronometro-rasp-pico/kicad/cronometro-rasp-pico.kicad_sch
    cronometro-arduino/kicad/cronometro-arduino.kicad_sch

    python tools/gen_kicad_sch.py            # so gera
    python tools/gen_kicad_sch.py --verificar  # gera, roda o ERC e exporta SVG

Os simbolos NAO estao copiados aqui: sao lidos da biblioteca do KiCad
instalado (MCU_Module:RaspberryPi_Pico, MCU_Module:Arduino_UNO_R3, ...), com
posicao e numero de cada pino. Assim o esquema bate com o KiCad que vai
abri-lo. Caminhos: KICAD10_SYMBOL_DIR e KICAD_CLI sobrescrevem o padrao.

Como o desenho e organizado:
- os modulos (TM1637, TCRT5000) sao conectores de 4 pinos na ordem exata do
  header de cada placa, porque e isso que se solda;
- as ligacoes sao por ROTULO DE REDE (CLK, DIO_1..6, SENSOR_1..6, ...), nao
  por fio longo: e o jeito legivel de ligar 7 blocos a uma placa;
- alimentacao por simbolo de power, rotacionado na ponta de cada toco --
  os pinos de um header ficam a 2,54 mm e simbolos em pe se sobreporiam;
- todo pino nao usado leva no-connect, para o ERC sair limpo.

Os UUIDs sao deterministicos (uuid5), entao regerar nao suja o git.
"""
import io, os, re, sys, uuid, subprocess

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMDIR = os.environ.get("KICAD10_SYMBOL_DIR",
                        r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
KICAD_CLI = os.environ.get("KICAD_CLI",
                           r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
NS = uuid.UUID("7d0a4f7e-1b0e-4c43-9a55-2f1d6c9b8e21")
BARRA = "\\"
DATA = "2026-09-12"
PASSO = 2.54

# ------------------------------------------------------------ bibliotecas
def _bloco(t, ini):
    prof, i, em_str = 0, ini, False
    while i < len(t):
        c = t[i]
        if em_str:
            if c == BARRA:
                i += 1
            elif c == '"':
                em_str = False
        elif c == '"':
            em_str = True
        elif c == "(":
            prof += 1
        elif c == ")":
            prof -= 1
            if prof == 0:
                return t[ini:i + 1]
        i += 1
    raise ValueError("s-expression sem fechamento")

_cache = {}
def simbolo_lib(lib, nome):
    chave = f"{lib}:{nome}"
    if chave in _cache:
        return _cache[chave]
    arq = os.path.join(SYMDIR, lib + ".kicad_sym")
    t = io.open(arq, encoding="utf-8").read()
    k = t.find('\n\t(symbol "%s"' % nome)
    if k < 0:
        raise SystemExit(f"simbolo {chave} nao encontrado em {arq}")
    b = _bloco(t, k + 2)
    if "(extends " in b:
        raise SystemExit(f"{chave} e derivado de outro simbolo; nao suportado")
    pinos = {}
    for m in re.finditer(r'\(pin (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*'
                         r'\(length [-\d.]+\)(.*?)\(name "([^"]*)"(.*?)\(number "([^"]*)"',
                         b, re.S):
        pinos[m.group(9)] = dict(tipo=m.group(1), x=float(m.group(3)),
                                 y=float(m.group(4)), ang=int(float(m.group(5))),
                                 nome=m.group(7))
    embutido = b.replace('(symbol "%s"' % nome, '(symbol "%s"' % chave, 1)
    _cache[chave] = dict(lib_id=chave, pinos=pinos, texto=embutido)
    return _cache[chave]

# ---------------------------------------------------------------- folha
def n(v):
    return f"{round(v, 4):g}"

def q(s):
    return '"' + s.replace(BARRA, BARRA * 2).replace('"', BARRA + '"').replace("\n", BARRA + "n") + '"'

# direcao "para fora" do pino, em coordenadas da folha (y cresce para baixo)
FORA = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}

# Rotacao do simbolo de power para o desenho apontar na direcao d.
ROT_V   = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}   # +3V3/+5V: seta p/ cima
ROT_GND = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}   # GND: aponta p/ baixo

class Folha:
    def __init__(self, projeto, titulo, comentarios):
        self.projeto, self.titulo, self.comentarios = projeto, titulo, comentarios
        self.raiz = str(uuid.uuid5(NS, projeto))
        self.itens, self.libs, self.cont = [], {}, {}

    def uid(self, *k):
        return str(uuid.uuid5(NS, self.projeto + "|" + "|".join(map(str, k))))

    def _ref(self, prefixo):
        self.cont[prefixo] = self.cont.get(prefixo, 0) + 1
        return f"{prefixo}{self.cont[prefixo]:02d}"

    # --------------------------------------------------------- primitivas
    def fio(self, x1, y1, x2, y2):
        self.itens.append(
            f'\t(wire\n\t\t(pts\n\t\t\t(xy {n(x1)} {n(y1)}) (xy {n(x2)} {n(y2)})\n\t\t)\n'
            f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            f'\t\t(uuid "{self.uid("fio", x1, y1, x2, y2)}")\n\t)')

    def juncao(self, x, y):
        self.itens.append(
            f'\t(junction\n\t\t(at {n(x)} {n(y)})\n\t\t(diameter 0)\n'
            f'\t\t(color 0 0 0 0)\n\t\t(uuid "{self.uid("jn", x, y)}")\n\t)')

    def nc(self, x, y):
        self.itens.append(f'\t(no_connect\n\t\t(at {n(x)} {n(y)})\n'
                          f'\t\t(uuid "{self.uid("nc", x, y)}")\n\t)')

    def rotulo(self, nome, x, y, d):
        rot, just = (180, "right") if d == (-1, 0) else (0, "left")
        self.itens.append(
            f'\t(label {q(nome)}\n\t\t(at {n(x)} {n(y)} {rot})\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            f'\t\t\t(justify {just} bottom)\n\t\t)\n'
            f'\t\t(uuid "{self.uid("lbl", nome, x, y)}")\n\t)')

    def texto(self, s, x, y, tam=1.27, negrito=False):
        b = "\n\t\t\t\t(bold yes)" if negrito else ""
        self.itens.append(
            f'\t(text {q(s)}\n\t\t(exclude_from_sim no)\n\t\t(at {n(x)} {n(y)} 0)\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {n(tam)} {n(tam)}){b}\n\t\t\t)\n'
            f'\t\t\t(justify left top)\n\t\t)\n'
            f'\t\t(uuid "{self.uid("txt", s[:40], x, y)}")\n\t)')

    def _prop(self, nome, valor, x, y, oculto=False, just=None, ang=0):
        h = "\n\t\t\t(hide yes)" if oculto else ""
        j = f"\n\t\t\t\t(justify {just})" if just else ""
        return (f'\t\t(property {q(nome)} {q(valor)}\n\t\t\t(at {n(x)} {n(y)} {ang}){h}\n'
                f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){j}\n'
                f'\t\t\t)\n\t\t)')

    def componente(self, sym, ref, valor, X, Y, rot=0, pos_ref=None, pos_val=None,
                   just_ref=None, just_val=None, ocultar_ref=False, ocultar_val=False,
                   no_bom=False, ang_val=0):
        self.libs[sym["lib_id"]] = sym["texto"]
        pr = pos_ref or (X, Y - 5.08)
        pv = pos_val or (X, Y + 5.08)
        props = [self._prop("Reference", ref, *pr, oculto=ocultar_ref, just=just_ref),
                 self._prop("Value", valor, *pv, oculto=ocultar_val, just=just_val, ang=ang_val),
                 self._prop("Footprint", "", X, Y, oculto=True),
                 self._prop("Datasheet", "", X, Y, oculto=True)]
        pinos = "\n".join(f'\t\t(pin {q(num)}\n\t\t\t(uuid "{self.uid("pin", ref, num)}")\n\t\t)'
                          for num in sym["pinos"])
        self.itens.append(
            f'\t(symbol\n\t\t(lib_id {q(sym["lib_id"])})\n\t\t(at {n(X)} {n(Y)} {rot})\n'
            f'\t\t(unit 1)\n\t\t(exclude_from_sim no)\n'
            f'\t\t(in_bom {"no" if no_bom else "yes"})\n\t\t(on_board yes)\n\t\t(dnp no)\n'
            f'\t\t(uuid "{self.uid("sym", ref)}")\n' + "\n".join(props) + "\n" + pinos + "\n"
            f'\t\t(instances\n\t\t\t(project {q(self.projeto)}\n'
            f'\t\t\t\t(path "/{self.raiz}"\n\t\t\t\t\t(reference {q(ref)})\n'
            f'\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')

    # ----------------------------------------------------------- ligacoes
    @staticmethod
    def pino(sym, X, Y, num):
        p = sym["pinos"][num]
        return X + p["x"], Y - p["y"], FORA[p["ang"]]

    def power(self, rede, x, y, d):
        if rede == "GND":
            sym, rot = simbolo_lib("power", "GND"), ROT_GND[d]
        else:
            sym, rot = simbolo_lib("power", rede), ROT_V[d]
        just = "right" if d == (-1, 0) else "left" if d == (1, 0) else None
        # O KiCad soma o angulo do campo a rotacao do simbolo e, quando a soma
        # da 180, desenha na horizontal mas INVERTE a justificacao: o texto cai
        # em cima do proprio simbolo. Girar o campo por -rot zera a soma.
        self.componente(sym, self._ref("#PWR"), rede, x, y, rot,
                        pos_ref=(x, y), pos_val=(x + d[0] * 5.08, y + d[1] * 5.08 + (1.27 if d[1] > 0 else 0)),
                        just_val=just, ocultar_ref=True, no_bom=True,
                        ang_val=(360 - rot) % 360)

    def pwr_flag(self, x, y, rot=0):
        sym = simbolo_lib("power", "PWR_FLAG")
        dy = 5.08 if rot == 180 else -3.81
        self.componente(sym, self._ref("#FLG"), "PWR_FLAG", x, y, rot,
                        pos_ref=(x, y), pos_val=(x, y + dy), ocultar_ref=True, no_bom=True,
                        ang_val=(360 - rot) % 360)

    def liga_rotulo(self, sym, X, Y, num, rede, toco=5.08):
        x, y, d = self.pino(sym, X, Y, num)
        xe, ye = x + d[0] * toco, y + d[1] * toco
        self.fio(x, y, xe, ye)
        self.rotulo(rede, xe, ye, d)

    def liga_power(self, sym, X, Y, num, rede, toco=5.08):
        x, y, d = self.pino(sym, X, Y, num)
        xe, ye = x + d[0] * toco, y + d[1] * toco
        if toco:
            self.fio(x, y, xe, ye)
        self.power(rede, xe, ye, d)

    def sem_ligacao(self, sym, X, Y, num):
        x, y, _ = self.pino(sym, X, Y, num)
        self.nc(x, y)

    # ------------------------------------------------------------- saida
    # O carimbo do formato de folha padrao do KiCad (pagelayout_default) tem
    # 108 mm de largura, texto de 1,5 mm e 4 linhas de comentario. Cabem uns
    # 70 caracteres por linha, menos com muita maiuscula; a primeira versao
    # usou 88 e 99 e estourou a moldura da folha. O gerador recusa antes.
    MAX_COMENTARIO, MAX_LINHAS = 62, 4

    def salvar(self, caminho):
        assert len(self.comentarios) <= self.MAX_LINHAS, "comentarios demais para o carimbo"
        for c in self.comentarios:
            assert len(c) <= self.MAX_COMENTARIO, f"comentario longo demais para o carimbo ({len(c)}): {c}"
        libs = "\n".join(self.libs[k] for k in sorted(self.libs))
        coment = "\n".join(f"\t\t(comment {i+1} {q(c)})" for i, c in enumerate(self.comentarios))
        s = (f'(kicad_sch\n\t(version 20250610)\n\t(generator "gen_kicad_sch")\n'
             f'\t(generator_version "10.0")\n\t(uuid "{self.raiz}")\n\t(paper "A3")\n'
             f'\t(title_block\n\t\t(title {q(self.titulo)})\n\t\t(date "{DATA}")\n'
             f'\t\t(rev "1")\n\t\t(company "Leonardo Roman da Rosa")\n{coment}\n\t)\n'
             f'\t(lib_symbols\n{libs}\n\t)\n' + "\n".join(self.itens) + "\n"
             f'\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n'
             f'\t(embedded_fonts no)\n)\n')
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        io.open(caminho, "w", encoding="utf-8", newline="\n").write(s)
        return caminho

# ------------------------------------------------------- partes comuns
def modulos_e_controles(f, vrede):
    J = simbolo_lib("Connector_Generic", "Conn_01x04")
    SW = simbolo_lib("Switch", "SW_Push")
    BZ = simbolo_lib("Device", "Buzzer")

    f.texto("DISPLAYS TM1637  -  header do modulo: CLK, DIO, GND, VCC", 223.52, 30.48, 1.5, True)
    f.texto("SENSORES TCRT5000  -  header do modulo: VCC, GND, D0, A0", 317.5, 30.48, 1.5, True)
    for k in range(6):
        Xc, Yc = 256.54, 45.72 + 22.86 * k
        f.componente(J, f"J{k+1}", f"TM1637 pista {k+1}", Xc, Yc,
                     pos_ref=(Xc + 3.81, Yc - 1.27), pos_val=(Xc + 3.81, Yc + 1.27),
                     just_ref="left", just_val="left")
        f.liga_rotulo(J, Xc, Yc, "1", "CLK")
        f.liga_rotulo(J, Xc, Yc, "2", f"DIO_{k+1}")
        f.liga_power(J, Xc, Yc, "3", "GND")
        f.liga_power(J, Xc, Yc, "4", vrede)

        Xs = 347.98
        f.componente(J, f"J{k+7}", f"TCRT5000 pista {k+1}", Xs, Yc,
                     pos_ref=(Xs + 3.81, Yc - 1.27), pos_val=(Xs + 3.81, Yc + 1.27),
                     just_ref="left", just_val="left")
        f.liga_power(J, Xs, Yc, "1", vrede)
        f.liga_power(J, Xs, Yc, "2", "GND")
        # Rotulo de rede fica ACIMA do fio: com toco curto, o SENSOR_n do pino 3
        # encostava no texto "GND" do pino 2, logo acima. O toco longo desencontra
        # os dois na horizontal.
        f.liga_rotulo(J, Xs, Yc, "3", f"SENSOR_{k+1}", toco=15.24)
        f.sem_ligacao(J, Xs, Yc, "4")          # A0 analogico: nao usado

    f.texto("PAINEL", 30.48, 205.74, 1.5, True)
    X1, Y1 = 53.34, 220.98
    f.componente(SW, "SW1", "Microswitch da porta", X1, Y1, pos_ref=(X1, Y1 - 5.08),
                 pos_val=(X1, Y1 + 3.81))
    f.liga_rotulo(SW, X1, Y1, "1", "LARGADA")
    f.liga_power(SW, X1, Y1, "2", "GND")
    X2, Y2 = 53.34, 241.3
    f.componente(SW, "SW2", "Botao TESTE (opcional)", X2, Y2, pos_ref=(X2, Y2 - 5.08),
                 pos_val=(X2, Y2 + 3.81))
    f.liga_rotulo(SW, X2, Y2, "1", "BOTAO")
    f.liga_power(SW, X2, Y2, "2", "GND")
    X3, Y3 = 55.88, 261.62
    f.componente(BZ, "BZ1", "Buzzer passivo (opcional)", X3, Y3,
                 pos_ref=(X3 + 5.08, Y3 - 1.27), pos_val=(X3 + 5.08, Y3 + 1.27),
                 just_ref="left", just_val="left")
    f.liga_rotulo(BZ, X3, Y3, "1", "BUZZER")
    f.liga_power(BZ, X3, Y3, "2", "GND")

def placa_generica(f, U, X, Y, mapa_nome, mapa_num, power_direto, pular):
    """Liga os pinos usados por rotulo; power direto no pino; resto no-connect."""
    for num, p in U["pinos"].items():
        if num in pular or p["tipo"] == "no_connect":
            continue
        if num in mapa_num:
            f.liga_rotulo(U, X, Y, num, mapa_num[num])
        elif p["nome"] in mapa_nome and num not in mapa_num:
            f.liga_rotulo(U, X, Y, num, mapa_nome[p["nome"]])
        elif num in power_direto:
            f.liga_power(U, X, Y, num, power_direto[num], toco=0)
        else:
            f.sem_ligacao(U, X, Y, num)

# ---------------------------------------------------------------- RP2040
def gera_pico():
    f = Folha("cronometro-rasp-pico", "Cronometro Hot Wheels - 6 pistas (RP2040)", [
        "Hardware sob CERN-OHL-S-2.0 - ver LICENSE-HARDWARE.txt",
        "Sensor: D0 ativo em 0 com carro; A0 do modulo nao usado.",
        "Nomes = GPIO. Na RP2040 roxa o furo muda: docs/pinout.md",
        "Tudo em 3,3 V: displays e sensores (TCRT5000, saida D0).",
    ])
    U = simbolo_lib("MCU_Module", "RaspberryPi_Pico")
    X, Y = 127.0, 132.08
    f.componente(U, "U1", "Raspberry Pi Pico", X, Y, pos_ref=(X - 20.32, Y - 41.91),
                 pos_val=(X + 12.7, Y - 41.91), just_ref="left", just_val="left")
    mapa = {f"GPIO{2+i}": f"SENSOR_{i+1}" for i in range(6)}
    mapa.update({f"GPIO{10+i}": f"DIO_{i+1}" for i in range(6)})
    mapa.update({"GPIO8": "LARGADA", "GPIO9": "CLK", "GPIO16": "BUZZER", "GPIO21": "BOTAO"})
    gnd = [num for num, p in U["pinos"].items() if p["nome"] == "GND"]
    # GND: os sete pinos estao empilhados no mesmo ponto; um simbolo liga todos.
    placa_generica(f, U, X, Y, mapa, {}, {"36": "+3V3", gnd[0]: "GND"}, pular=set(gnd[1:]))

    f.texto("Log serial: USB, ou UART0 em GPIO0/GPIO1 (sem ligacao aqui).\n"
            "Os pinos GPIO23/24/25/29 nao aparecem no simbolo e nao sao usados.\n"
            "AGND fica sem ligacao: o ADC nao e usado, e AGND e GND sao ambos\n"
            "power_out no simbolo -- uni-los seria erro de ERC.",
            91.44, 185.42, 1.27)
    modulos_e_controles(f, "+3V3")
    return f.salvar(os.path.join(RAIZ, "cronometro-rasp-pico", "kicad",
                                 "cronometro-rasp-pico.kicad_sch"))

# --------------------------------------------------------------- Arduino
def gera_uno():
    f = Folha("cronometro-arduino", "Cronometro Hot Wheels - 6 pistas (Arduino UNO/Nano)", [
        "Hardware sob CERN-OHL-S-2.0 - ver LICENSE-HARDWARE.txt",
        "Sensor: D0 ativo em 0 com carro; A0 do modulo nao usado.",
        "Sensores em A0..A5, nesta ordem (PCINT1). Largada em D2.",
        "Tudo em 5 V: displays e sensores (TCRT5000, saida D0).",
    ])
    U = simbolo_lib("MCU_Module", "Arduino_UNO_R3")
    X, Y = 127.0, 132.08
    f.componente(U, "A1", "Arduino UNO R3", X, Y, pos_ref=(X - 10.16, Y - 29.21),
                 pos_val=(X + 12.7, Y - 29.21), just_ref="left", just_val="left")
    mapa = {"D2": "LARGADA", "D3": "CLK", "D10": "BUZZER", "D11": "BOTAO",
            "A0": "SENSOR_1", "A1": "SENSOR_2", "A2": "SENSOR_3", "A3": "SENSOR_4"}
    mapa.update({f"D{4+i}": f"DIO_{i+1}" for i in range(6)})
    # A4/A5 aparecem DUAS vezes no simbolo (13/14 no header analogico e 31/32 no
    # header de I2C, o mesmo sinal). Liga-se pelo numero para escolher o 13/14.
    por_num = {"13": "SENSOR_5", "14": "SENSOR_6"}
    gnd = [num for num, p in U["pinos"].items() if p["nome"] == "GND"]
    placa_generica(f, U, X, Y, mapa, por_num, {"5": "+5V"}, pular=set(gnd))

    # Os tres GND do UNO sao power_in: ninguem "dirige" a rede, entao ela leva
    # um PWR_FLAG. Os tres pinos descem e se juntam numa barra curta.
    xs = sorted(f.pino(U, X, Y, num)[0] for num in gnd)
    yp = f.pino(U, X, Y, gnd[0])[1]
    yb = yp + PASSO
    for x in xs:
        f.fio(x, yp, x, yb)
    for a, b in zip(xs, xs[1:]):
        f.fio(a, yb, b, yb)
    xm = xs[len(xs) // 2]
    f.fio(xm, yb, xm, yb + PASSO)
    f.juncao(xm, yb)
    f.power("GND", xm, yb + PASSO, (0, 1))
    f.fio(xs[0] - 2 * PASSO, yb, xs[0], yb)
    f.juncao(xs[0], yb)
    f.pwr_flag(xs[0] - 2 * PASSO, yb, rot=180)

    f.texto("Log serial: USB (D0/D1), 115200 - sem ligacao aqui.\n"
            "Livres: D12 e D13. Os pinos 31/32 (SDA/SCL) sao o mesmo sinal de A4/A5.\n"
            "Nano: mesmos nomes de pino; A6/A7 do Nano sao so analogicos (sem PCINT).",
            91.44, 185.42, 1.27)
    modulos_e_controles(f, "+5V")
    return f.salvar(os.path.join(RAIZ, "cronometro-arduino", "kicad",
                                 "cronometro-arduino.kicad_sch"))

# -------------------------------------------------------------- verificar
# O ERC so ve regras eletricas (pino solto, power sem driver). Quem prova que
# cada fio chega no lugar certo e o NETLIST: exporta-se o netlist do proprio
# KiCad e confere-se, rede por rede, contra a pinagem do firmware. Os numeros
# de pino sao os do simbolo (MCU_Module do KiCad 10).
ESPERADO = {
    "cronometro-rasp-pico": dict(mcu="U1", clk="12", dio=["14", "15", "16", "17", "19", "20"],
                                 sens=["4", "5", "6", "7", "9", "10"], largada="11",
                                 buzzer="21", botao="27", v="+3V3"),
    "cronometro-arduino": dict(mcu="A1", clk="18", dio=["19", "20", "21", "22", "23", "24"],
                               sens=["9", "10", "11", "12", "13", "14"], largada="17",
                               buzzer="25", botao="26", v="+5V"),
}

def _cli(*args):
    r = subprocess.run([KICAD_CLI, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} falhou:\n{r.stdout}{r.stderr}")
    return r

def confere_netlist(projeto, arq_net):
    t = io.open(arq_net, encoding="utf-8").read()
    redes = {}
    for m in re.finditer(r'\(net\s+\(code\s+"?\d+"?\)\s+\(name\s+"([^"]*)"\)(.*?)(?=\(net\s+\(code|\Z)',
                         t, re.S):
        redes[m.group(1).lstrip("/")] = set(
            re.findall(r'\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)', m.group(2)))
    e, falhas = ESPERADO[projeto], []
    M = e["mcu"]

    def exige(rede, nos):
        if redes.get(rede, set()) != set(nos):
            falhas.append(f"{rede}: esperado {sorted(nos)}, obtido {sorted(redes.get(rede, set()))}")

    exige("CLK", [(M, e["clk"])] + [(f"J{k+1}", "1") for k in range(6)])
    for k in range(6):
        exige(f"DIO_{k+1}", [(M, e["dio"][k]), (f"J{k+1}", "2")])
        exige(f"SENSOR_{k+1}", [(M, e["sens"][k]), (f"J{k+7}", "3")])
    exige("LARGADA", [(M, e["largada"]), ("SW1", "1")])
    exige("BUZZER", [(M, e["buzzer"]), ("BZ1", "1")])
    exige("BOTAO", [(M, e["botao"]), ("SW2", "1")])
    v, gnd = redes.get(e["v"], set()), redes.get("GND", set())
    for k in range(6):
        for no, rede, nome in (((f"J{k+1}", "4"), v, e["v"]), ((f"J{k+7}", "1"), v, e["v"]),
                               ((f"J{k+1}", "3"), gnd, "GND"), ((f"J{k+7}", "2"), gnd, "GND")):
            if no not in rede:
                falhas.append(f"{no[0]}.{no[1]} fora de {nome}")
    for no in (("SW1", "2"), ("SW2", "2"), ("BZ1", "2")):
        if no not in gnd:
            falhas.append(f"{no[0]}.{no[1]} fora de GND")
    return falhas

def verificar(sch):
    projeto = os.path.splitext(os.path.basename(sch))[0]
    pasta = os.path.dirname(sch)
    docs = os.path.join(os.path.dirname(pasta), "docs")

    rel = os.path.join(pasta, "erc.rpt")
    _cli("sch", "erc", "--severity-all", "--format", "report", "-o", rel, sch)
    t = io.open(rel, encoding="utf-8", errors="replace").read()
    m = re.search(r"ERC messages: (\d+)\s+Errors (\d+)\s+Warnings (\d+)", t)
    print("   ERC:", " ".join(m.group(0).split()) if m else "(sem resumo no relatorio)")

    net = os.path.join(pasta, projeto + ".net")
    _cli("sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch)
    falhas = confere_netlist(projeto, net)
    os.remove(net)
    print("   netlist:", "todas as ligacoes conferem com a pinagem do firmware" if not falhas
          else "DIVERGENCIAS:\n     " + "\n     ".join(falhas))

    # Para ver sem abrir o KiCad (inclusive no GitHub): SVG e PDF em docs/.
    _cli("sch", "export", "svg", "-o", pasta, sch)
    os.replace(os.path.join(pasta, projeto + ".svg"), os.path.join(docs, "esquema-kicad.svg"))
    _cli("sch", "export", "pdf", "-o", os.path.join(docs, "esquema-kicad.pdf"), sch)
    print("   exportado: docs/esquema-kicad.svg e docs/esquema-kicad.pdf")
    return not falhas and m and m.group(2) == "0"

if __name__ == "__main__":
    ok = True
    for gerador in (gera_pico, gera_uno):
        caminho = gerador()
        print("gerado:", os.path.relpath(caminho, RAIZ))
        if "--verificar" in sys.argv:
            ok = verificar(caminho) and ok
    sys.exit(0 if ok else 1)
