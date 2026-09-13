# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Leonardo Roman da Rosa
"""
Gera o diagram.json do simulador Wokwi -- versao Arduino UNO.

O diagrama e gerado, e nao editado a mao: sao ~54 fios com waypoints
calculados, e o Wokwi NAO roteia nada -- sem waypoints ele liga pino a pino
em linha reta, o que faz a fiacao passar por cima dos digitos.

A geometria e diferente da versao RP2040 por causa da placa: no UNO os
pinos DIGITAIS ficam na borda de CIMA e os ANALOGICOS na de BAIXO. Por isso
a placa fica no meio do desenho, com os displays em cima (D3..D9 sobem) e
as barreiras embaixo (A0..A5 descem). Nenhum fio precisa contornar a placa.

    python tools/gen_diagram.py
"""
import json, io, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

N, PITCH = 6, 260
DL = [PITCH * i for i in range(N)]

# Faixas livres reservadas para fio:
#   y 120..320  corredor A -- CLK/VCC/GND (137..182) e DIO (232..292)
#   y 330..355  faixa fina, so para os fios dos controles
#   y 600..790  corredor B -- sinais das barreiras
# Nenhum texto pode encostar nelas.
SOBE_DISP = "v-90"    # saida dos pinos digitais do UNO rumo ao corredor A
SOBE_CTRL = "v-20"    # saida dos pinos digitais rumo aos controles
DESCE_UNO = "v60"     # saida dos pinos analogicos/alimentacao rumo ao B
SAI_DISP, DESCE_DISP = "h-20", "v120"
SAI_BARR = "h-35"

UNO_LEFT, UNO_TOP = 380, 360

parts, conns = [], []
def w(a, b, cor, wp=None): conns.append([a, b, cor, wp or []])

for i in range(N):
    parts.append({"type": "wokwi-text", "id": f"lbl{i+1}", "top": -62,
                  "left": DL[i] + 45, "attrs": {"text": f"PISTA {i+1}"}})
for i in range(N):
    parts.append({"type": "wokwi-tm1637-7segment", "id": f"d{i+1}", "top": 0,
                  "left": DL[i], "attrs": {"color": "green"}})

# Sensor TCRT5000 de cada pista. O Wokwi nao tem TCRT5000, mas a peca de luz
# dele tem o mesmo header (VCC/GND/DO/AO) e a mesma logica do modulo real:
# escuro (nada refletindo, sem carro) -> DO = 1; claro (carro refletindo) ->
# DO = 0. Por isso o lux comeca em 0 e "passar um carrinho" e SUBIR a luz.
for i in range(N):
    parts.append({"type": "wokwi-text", "id": f"blbl{i+1}", "top": 800,
                  "left": DL[i] + 8, "attrs": {"text": f"TCRT5000 PISTA {i+1}  (A{i})"}})
    parts.append({"type": "wokwi-photoresistor-sensor", "id": f"s{i+1}",
                  "top": 832, "left": DL[i] + 11,
                  "attrs": {"lux": "0", "threshold": "2.5"}})

parts += [
  {"type": "wokwi-arduino-uno", "id": "uno", "top": UNO_TOP, "left": UNO_LEFT,
   "attrs": {}},
  {"type": "wokwi-slide-switch", "id": "porta", "top": 390, "left": 700,
   "attrs": {"value": ""}},
  {"type": "wokwi-pushbutton", "id": "btn1", "top": 490, "left": 700,
   "attrs": {"color": "blue", "label": "TESTE", "key": "d"}},
  {"type": "wokwi-buzzer", "id": "bz1", "top": 390, "left": 900, "attrs": {}},

  {"type": "wokwi-text", "id": "t_porta", "top": 445, "left": 690,
   "attrs": {"text": "PORTA DE LARGADA (D2)\nmetade DIREITA = abre, larga"}},
  {"type": "wokwi-text", "id": "t_btn", "top": 560, "left": 680,
   "attrs": {"text": "tecla D: toque = rearma, segurar 1 s = demo"}},

  {"type": "wokwi-text", "id": "t_ajuda", "top": 0, "left": 1560,
   "attrs": {"text":
     "COMO USAR\n\n"
     "1) Ver uma corrida inteira:\n"
     "   segure a tecla D por 1 segundo.\n\n"
     "2) Corrida manual:\n"
     "   - PORTA para a direita (larga)\n"
     "   - clique num sensor e SUBA a luz:\n"
     "     e o carrinho refletindo\n"
     "   - a ordem dos cliques e a ordem\n"
     "     de chegada\n"
     "   - quem ficar no escuro vira dnF\n\n"
     "3) Rearmar: PORTA para a esquerda e\n"
     "   sensores de volta ao escuro.\n\n"
     "Tempos tambem na aba Serial Monitor\n"
     "(115200). 4 digitos = milissegundos:\n"
     "3721 le-se 3,721 s."}},

  {"type": "wokwi-text", "id": "t_ir", "top": 380, "left": 1560,
   "attrs": {"text":
     "SOBRE OS SENSORES\n\n"
     "Cada pista tem um modulo TCRT5000:\n"
     "VCC, GND, D0 e A0. So o D0 e ligado;\n"
     "o A0 fica solto.\n\n"
     "Os seis D0 TEM que ficar em A0..A5:\n"
     "sao a PORTC inteira, e so assim\n"
     "cabem numa unica interrupcao de\n"
     "mudanca de pino (PCINT1). O 328P so\n"
     "tem duas interrupcoes externas.\n\n"
     "O Wokwi nao tem TCRT5000. A peca de\n"
     "luz usada aqui tem o MESMO header e\n"
     "a MESMA logica:\n\n"
     "  escuro = sem carro  -> D0 = 1\n"
     "  claro  = carro      -> D0 = 0\n\n"
     "Para passar um carrinho: clique no\n"
     "sensor e SUBA a luz."}},
]

# ---- CLK comum: UNO -> d1, depois de um display para o vizinho --------
w("uno:3", "d1:CLK", "gold", [SOBE_DISP, "*", SAI_DISP, DESCE_DISP])
for i in range(1, N):
    w(f"d{i}:CLK", f"d{i+1}:CLK", "gold",
      [SAI_DISP, DESCE_DISP, "*", SAI_DISP, DESCE_DISP])

# ---- DIO: um por pista (D4..D9), cada um num corredor proprio ---------
for i in range(N):
    w(f"uno:{4+i}", f"d{i+1}:DIO", "green",
      [SOBE_DISP, "*", SAI_DISP, f"v{200+12*i}"])

# ---- Alimentacao: so dois fios longos, o resto em cascata -------------
w("uno:5V",    "d1:VCC", "red",   [DESCE_UNO, "*", SAI_DISP, DESCE_DISP])
w("uno:GND.2", "d1:GND", "black", [DESCE_UNO, "*", SAI_DISP, DESCE_DISP])
for i in range(1, N):
    w(f"d{i}:VCC", f"d{i+1}:VCC", "red",
      [SAI_DISP, DESCE_DISP, "*", SAI_DISP, DESCE_DISP])
    w(f"d{i}:GND", f"d{i+1}:GND", "black",
      [SAI_DISP, DESCE_DISP, "*", SAI_DISP, DESCE_DISP])

# ---- Barreiras: 5 V e GND descem pela esquerda, fora de tudo ----------
w("d1:VCC", "s1:VCC", "red",   [SAI_DISP, DESCE_DISP, "*", SAI_BARR, "v-120"])
w("d1:GND", "s1:GND", "black", [SAI_DISP, DESCE_DISP, "*", SAI_BARR, "v-120"])
for i in range(1, N):
    w(f"s{i}:VCC", f"s{i+1}:VCC", "red",   [SAI_BARR, "v-120", "*", SAI_BARR, "v-120"])
    w(f"s{i}:GND", f"s{i+1}:GND", "black", [SAI_BARR, "v-120", "*", SAI_BARR, "v-120"])
for i in range(N):
    w(f"uno:A{i}", f"s{i+1}:DO", "blue",
      [DESCE_UNO, "*", SAI_BARR, f"v-{180+12*i}"])   # o AO do modulo fica solto

# ---- Controles: GND em cascata, um unico fio ate a placa --------------
w("uno:2",     "porta:2",    "cyan",   [SOBE_CTRL])
w("uno:GND.1", "porta:1",    "black",  [SOBE_CTRL])
w("porta:1",   "btn1:2.r",   "black",  [])
w("btn1:2.r",  "bz1:2",      "black",  [])
w("uno:11",    "btn1:1.l",   "orange", [SOBE_CTRL])
w("uno:10",    "bz1:1",      "purple", [SOBE_CTRL])

io.open("diagram.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps({"version": 1, "author": "Cronometro Hot Wheels 6 pistas (Arduino)",
                "editor": "wokwi", "parts": parts, "connections": conns},
               indent=2, ensure_ascii=False) + "\n")

# ---------------------------- conferencias ----------------------------
d = json.load(io.open("diagram.json", encoding="utf-8"))
ids = {p["id"] for p in d["parts"]}
ref = {c[0].split(":")[0] for c in d["connections"]} | {c[1].split(":")[0] for c in d["connections"]}
print("partes:", len(d["parts"]), "fios:", len(d["connections"]), "| orfas:", ref - ids or "nenhuma")

TAM = {"wokwi-tm1637-7segment": (159, 91), "wokwi-arduino-uno": (259, 201),
       "wokwi-slide-switch": (60, 40), "wokwi-pushbutton": (68, 50),
       "wokwi-buzzer": (60, 60), "wokwi-photoresistor-sensor": (137, 72)}
def caixa(p):
    if p["type"] in TAM:
        wd, ht = TAM[p["type"]]
    else:  # texto: ~7.5 px por caractere, 17 px por linha
        ls = p["attrs"]["text"].split("\n")
        wd, ht = int(max(len(l) for l in ls) * 7.5), len(ls) * 17
    return (p["id"], p["left"], p["top"], p["left"] + wd, p["top"] + ht)

cx = [caixa(p) for p in d["parts"]]
bat = [(a[0], b[0]) for i, a in enumerate(cx) for b in cx[i+1:]
       if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]]
print("sobreposicoes peca/texto:", bat or "nenhuma")

FAIXAS = [("corredor A", 130, 300), ("corredor B", 600, 790)]
ok = True
for p in d["parts"]:
    if p["type"] != "wokwi-text":
        continue
    _, x0, y0, x1, y1 = caixa(p)
    for nome, fy0, fy1 in FAIXAS:
        if y0 < fy1 and fy0 < y1 and x0 < 1500:
            print(f"  AVISO: texto {p['id']} invade {nome}"); ok = False
print("textos fora das faixas de fiacao" if ok else "  >>> corrija os avisos acima")

# Conferencia dos pinos usados contra o sketch.
import re
ino = io.open("cronometro-arduino.ino", encoding="utf-8").read()
def num(nome):
    return int(re.search(r"const uint8_t %s\s*=\s*(\d+)" % nome, ino).group(1))
esperado = {"3": num("PIN_TM_CLK"), "2": num("PIN_LARGADA"),
            "10": num("PIN_BUZZER"), "11": num("PIN_BOTAO")}
for pino, valor in esperado.items():
    assert int(pino) == valor, f"pino {pino} do diagrama nao bate com o sketch"
dio = [int(x) for x in re.search(r"PIN_TM_DIO\[N_PISTAS\]\s*=\s*\{([^}]*)\}", ino).group(1).split(",")]
assert dio == [4, 5, 6, 7, 8, 9], f"PIN_TM_DIO mudou no sketch: {dio}"
print("pinos do diagrama conferem com o sketch")
