# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Leonardo Roman da Rosa
"""
Gera o diagram.json do simulador Wokwi.

O diagrama e gerado, e nao editado a mao, por dois motivos: sao ~54 fios com
waypoints calculados, e o Wokwi NAO roteia nada -- sem waypoints ele liga
pino a pino em linha reta, o que faz a fiacao passar por cima dos digitos.
Ao final o script confere sobreposicao de pecas e de textos com as faixas
reservadas para fio.

    python tools/gen_diagram.py
"""
import json, io, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

N, PITCH = 6, 260
DL = [PITCH * i for i in range(N)]

DESCE_DISP = 120
SAI_DISP = "h-20"
ESQ, DIR = "h-30", "h30"

# Zonas livres reservadas para fio (ver NOTAS.md):
#   y  91..330  corredor A  -- CLK/VCC/GND dos displays (137..182) e DIO (232..292)
#   y 450..640  corredor B  -- sinal das barreiras (475..545)
#   x 430       coluna que sobe do Pico ate os dois corredores
# Nenhum texto pode encostar nessas faixas, nem na coluna x=430.

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
    parts.append({"type": "wokwi-text", "id": f"blbl{i+1}", "top": 330,
                  "left": DL[i] + 8, "attrs": {"text": f"TCRT5000 PISTA {i+1}"}})
    parts.append({"type": "wokwi-photoresistor-sensor", "id": f"s{i+1}",
                  "top": 362, "left": DL[i] + 11,
                  "attrs": {"lux": "0", "threshold": "2.5"}})

parts += [
  {"type": "wokwi-pi-pico", "id": "pico", "top": 640, "left": 460, "attrs": {}},
  {"type": "wokwi-slide-switch", "id": "porta", "top": 665, "left": 120,
   "attrs": {"value": ""}},
  {"type": "wokwi-pushbutton", "id": "btn1", "top": 665, "left": 800,
   "attrs": {"color": "blue", "label": "TESTE", "key": "d"}},
  {"type": "wokwi-buzzer", "id": "bz1", "top": 660, "left": 980, "attrs": {}},

  {"type": "wokwi-text", "id": "t_porta", "top": 720, "left": 20,
   "attrs": {"text": "PORTA DE LARGADA\nmetade DIREITA = abre, larga\nmetade esquerda = fecha, rearma"}},
  {"type": "wokwi-text", "id": "t_btn", "top": 790, "left": 720,
   "attrs": {"text": "tecla D: toque = rearma, segurar 1 s = corrida demo"}},

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
     "Tempos tambem na aba Serial Monitor.\n"
     "4 digitos = milissegundos:\n"
     "3721 le-se 3,721 s."}},

  {"type": "wokwi-text", "id": "t_ir", "top": 360, "left": 1560,
   "attrs": {"text":
     "SOBRE OS SENSORES\n\n"
     "Cada pista tem um modulo TCRT5000:\n"
     "VCC, GND, D0 e A0. So o D0 e ligado;\n"
     "o A0 fica solto.\n\n"
     "O Wokwi nao tem TCRT5000. A peca de\n"
     "luz usada aqui tem o MESMO header e a\n"
     "MESMA logica do modulo real:\n\n"
     "  escuro = nada refletindo = sem\n"
     "           carro          -> D0 = 1\n"
     "  claro  = carro refletindo -> D0 = 0\n\n"
     "Para passar um carrinho: clique no\n"
     "sensor e SUBA a luz.\n\n"
     "O LED IR do modulo e interno: nao ha\n"
     "nada para ligar alem dos tres fios."}},

]

w("pico:GP9", "d1:CLK", "gold", [ESQ, "*", SAI_DISP, f"v{DESCE_DISP}"])
for i in range(1, N):
    w(f"d{i}:CLK", f"d{i+1}:CLK", "gold",
      [SAI_DISP, f"v{DESCE_DISP}", "*", SAI_DISP, f"v{DESCE_DISP}"])

for i in range(N):
    w(f"pico:GP{10+i}", f"d{i+1}:DIO", "green", [ESQ, "*", SAI_DISP, f"v{200+12*i}"])

w("pico:3V3", "d1:VCC", "red", [DIR, "v-360", "*", SAI_DISP, f"v{DESCE_DISP}"])
w("pico:GND.2", "d1:GND", "black", [ESQ, "*", SAI_DISP, f"v{DESCE_DISP}"])
for i in range(1, N):
    w(f"d{i}:VCC", f"d{i+1}:VCC", "red",
      [SAI_DISP, f"v{DESCE_DISP}", "*", SAI_DISP, f"v{DESCE_DISP}"])
    w(f"d{i}:GND", f"d{i+1}:GND", "black",
      [SAI_DISP, f"v{DESCE_DISP}", "*", SAI_DISP, f"v{DESCE_DISP}"])

SAI_SENS = "h-35"
w("d1:VCC", "s1:VCC", "red",   [SAI_DISP, f"v{DESCE_DISP}", "*", SAI_SENS, "v110"])
w("d1:GND", "s1:GND", "black", [SAI_DISP, f"v{DESCE_DISP}", "*", SAI_SENS, "v110"])
for i in range(1, N):
    w(f"s{i}:VCC", f"s{i+1}:VCC", "red",   [SAI_SENS, "v110", "*", SAI_SENS, "v110"])
    w(f"s{i}:GND", f"s{i+1}:GND", "black", [SAI_SENS, "v110", "*", SAI_SENS, "v110"])
for i in range(N):
    w(f"pico:GP{2+i}", f"s{i+1}:DO", "blue",
      [ESQ, "*", SAI_SENS, f"v{150+12*i}"])   # o AO do modulo fica solto

w("pico:GP8", "porta:2", "cyan", [ESQ])
w("pico:GND.1", "porta:1", "black", [ESQ])
w("pico:GP21", "btn1:1.l", "orange", [DIR])
w("pico:GND.5", "btn1:2.r", "black", [DIR])
w("pico:GP16", "bz1:1", "purple", [DIR])
w("pico:GND.6", "bz1:2", "black", [DIR])

io.open("diagram.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps({"version": 1, "author": "Cronometro Hot Wheels 6 pistas",
                "editor": "wokwi", "parts": parts, "connections": conns},
               indent=2, ensure_ascii=False) + "\n")

# ---- conferencias ----
d = json.load(io.open("diagram.json", encoding="utf-8"))
ids = {p["id"] for p in d["parts"]}
ref = {c[0].split(":")[0] for c in d["connections"]} | {c[1].split(":")[0] for c in d["connections"]}
print("partes:", len(d["parts"]), "fios:", len(d["connections"]), "| orfas:", ref - ids or "nenhuma")

TAM = {"wokwi-tm1637-7segment": (159, 91), "wokwi-pi-pico": (79, 194),
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

FAIXAS = [("corredor A", 130, 300), ("corredor B", 470, 550)]
for p in d["parts"]:
    if p["type"] != "wokwi-text":
        continue
    _, x0, y0, x1, y1 = caixa(p)
    for nome, fy0, fy1 in FAIXAS:
        if y0 < fy1 and fy0 < y1 and x0 < 1500:
            print(f"  AVISO: texto {p['id']} invade {nome}")
    if x0 < 430 < x1 and y1 > 450:
        print(f"  AVISO: texto {p['id']} cruza a coluna x=430")
print("verificacao de textos concluida")
