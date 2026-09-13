# Pinagem

Os GPIOs ficam em [../src/config.h](../src/config.h) e
[../src/config.c](../src/config.c). O **firmware é o mesmo** para o Pico
oficial e para a RP2040 roxa — o RP2040 é idêntico, o que muda é em qual
furo da placa cada GPIO aparece.

**Posições físicas** na numeração padrão do Pico: pino 1 no canto do USB,
1–20 descem a coluna esquerda, 21–40 sobem a direita.

## Sinais do projeto

| Função | GPIO | Dir | Pico oficial | RP2040 roxa | Observação |
| --- | --- | --- | --- | --- | --- |
| TCRT5000 raia 1 (D0) | GP2 | IN | 4 | **3** | ativo em 0; o pull-up já vem no módulo |
| TCRT5000 raia 2 (D0) | GP3 | IN | 5 | **4** | |
| TCRT5000 raia 3 (D0) | GP4 | IN | 6 | **5** | |
| TCRT5000 raia 4 (D0) | GP5 | IN | 7 | **7** | |
| TCRT5000 raia 5 (D0) | GP6 | IN | 9 | **8** | |
| TCRT5000 raia 6 (D0) | GP7 | IN | 10 | **9** | |
| Microswitch da porta | GP8 | IN | 11 | **10** | contato para GND, pull-up interno |
| TM1637 **CLK** (comum) | GP9 | OUT | 12 | **11** | vai nos seis displays |
| TM1637 DIO raia 1 | GP10 | I/O | 14 | **12** | dreno aberto emulado |
| TM1637 DIO raia 2 | GP11 | I/O | 15 | **13** | |
| TM1637 DIO raia 3 | GP12 | I/O | 16 | **14** | |
| TM1637 DIO raia 4 | GP13 | I/O | 17 | **16** | |
| TM1637 DIO raia 5 | GP14 | I/O | 19 | **17** | |
| TM1637 DIO raia 6 | GP15 | I/O | 20 | **18** | |
| Buzzer passivo | GP16 | OUT | 21 | **19** | opcional (`USAR_BUZZER`) |
| Botão TESTE / rearma | GP21 | IN | 27 | **24** | opcional (`USAR_BOTAO`) |
| UART0 TX / RX (log) | GP0 / GP1 | — | 1 / 2 | 1 / 2 | opcional; o USB também loga |
| **3,3 V** | — | — | 36 | 36 | displays e sensores (ou regulador separado, ver bom.md) |
| **GND** | — | — | 3, 8, 13, 18, 23, 28, 38 | 6, 15, 35, 38 | massa comum |
| +5 V (não usado) | — | — | 40 (VBUS) | 40 (VBUS) | **não** ligue nos TM1637 |

Sobram livres: GP17 a GP20, GP22, GP26 a GP28 (os três com ADC). Dá para
crescer para 8 ou 9 raias sem reorganizar nada — só estender as tabelas de
`config.c` e `N_PISTAS`.

## Por que estes GPIOs

- **Sensores em GP2–GP7, contíguos.** Facilita conferir o cabo flat e
  permite ler as seis raias num único `gpio_get_all()`, caso um dia se
  queira amostrar por polling em vez de interrupção.
- **GP0/GP1 livres** para a UART0, que é o que o monitor serial do Wokwi lê.
- **GP16 (buzzer)** é canal A do slice 0 do PWM e não disputa nada.
- **Nada em GP23, GP24, GP25 nem GP29.** No Pico oficial esses pinos são do
  regulador, do sensor de VBUS e do LED, e nem aparecem nos furos; na roxa
  aparecem, mas usá-los amarraria o projeto a uma placa só.

## Pinagem completa das duas placas

| Pos | Pico oficial | RP2040 roxa |
| --- | --- | --- |
| 1 | GP0 | GP0 |
| 2 | GP1 | GP1 |
| 3 | GND | **GP2** |
| 4 | **GP2** | **GP3** |
| 5 | **GP3** | **GP4** |
| 6 | **GP4** | GND |
| 7 | **GP5** | **GP5** |
| 8 | GND | **GP6** |
| 9 | **GP6** | **GP7** |
| 10 | **GP7** | **GP8** |
| 11 | **GP8** | **GP9** |
| 12 | **GP9** | **GP10** |
| 13 | GND | **GP11** |
| 14 | **GP10** | **GP12** |
| 15 | **GP11** | GND |
| 16 | **GP12** | **GP13** |
| 17 | **GP13** | **GP14** |
| 18 | GND | **GP15** |
| 19 | **GP14** | **GP16** |
| 20 | **GP15** | GP17 |
| 21 | **GP16** | GP18 |
| 22 | GP17 | GP19 |
| 23 | GND | GP20 |
| 24 | GP18 | **GP21** |
| 25 | GP19 | GP22 |
| 26 | GP20 | GP23 |
| 27 | **GP21** | GP24 |
| 28 | GND | GP25 |
| 29 | GP22 | AGND |
| 30 | RUN | GP26/A0 |
| 31 | GP26/ADC0 | GP27/A1 |
| 32 | GP27/ADC1 | GP28/A2 |
| 33 | AGND | GP29/A3 |
| 34 | GP28/ADC2 | RUN |
| 35 | ADC_VREF | **GND** |
| 36 | **3V3** | **3V3** |
| 37 | 3V3_EN | 3V3_EN |
| 38 | **GND** | **GND** |
| 39 | VSYS | VIN |
| 40 | VBUS (+5 V) | VBUS (+5 V) |

Em **negrito**, as posições que o projeto usa em cada placa. Repare que a
coluna da roxa está deslocada: **confira no silk da sua placa antes de
soldar** — se o furo marcado GP16 não bater com a tabela, o módulo é da
outra variante.

## Cabeamento sugerido

Cada TM1637 precisa de 4 fios e cada TCRT5000 de 3 (VCC, GND e D0 — o A0
fica solto). Em vez de puxar tudo até o Pico:

- **3,3 V e GND** em duas barras que percorrem o painel, com os módulos
  pendurados nelas (é assim que o `diagram.json` e o
  [diagrama de fiação](fiacao-pico.svg) estão desenhados). Se usar o
  regulador 3,3 V separado recomendado em [bom.md](bom.md), é ele que
  alimenta as barras — com o GND ligado ao do Pico.
- **CLK** também em cascata, um fio curto de um display para o outro. O
  módulo preto de 0,56" tem header dos dois lados, o que deixa isso trivial.
- Só os **6 DIO** dos displays e os **6 D0** dos sensores voltam
  individualmente ao Pico.

Dá 14 fios longos em vez de 42.
