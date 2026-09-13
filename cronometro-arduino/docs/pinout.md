# Pinagem — Arduino UNO / Nano (ATmega328P)

Aqui não existe o problema que a versão RP2040 tem com as placas clone: o
nome serigrafado na placa **é** o nome usado no código. `D4` é `D4` no UNO e
no Nano. Por isso esta página não traz tabela de posição física — traz o
mapeamento para as portas do AVR, que é o que importa para entender as
amarrações.

Os pinos ficam no bloco **CONFIGURAÇÃO** no topo de
[../cronometro-arduino.ino](../cronometro-arduino.ino).

## Sinais do projeto

| Função | Pino | Porta AVR | Dir | Observação |
| --- | --- | --- | --- | --- |
| TCRT5000 raia 1 (D0) | **A0** | PC0 | IN | ativo em 0; o pull-up já vem no módulo |
| TCRT5000 raia 2 (D0) | **A1** | PC1 | IN | |
| TCRT5000 raia 3 (D0) | **A2** | PC2 | IN | |
| TCRT5000 raia 4 (D0) | **A3** | PC3 | IN | |
| TCRT5000 raia 5 (D0) | **A4** | PC4 | IN | (é também o SDA do I²C, se um dia precisar) |
| TCRT5000 raia 6 (D0) | **A5** | PC5 | IN | (SCL) |
| Microswitch da porta | **D2** | PD2 | IN | **INT0** — contato para GND, pull-up interno |
| TM1637 **CLK** (comum) | **D3** | PD3 | OUT | vai nos seis displays |
| TM1637 DIO raia 1 | **D4** | PD4 | I/O | dreno aberto emulado |
| TM1637 DIO raia 2 | **D5** | PD5 | I/O | |
| TM1637 DIO raia 3 | **D6** | PD6 | I/O | |
| TM1637 DIO raia 4 | **D7** | PD7 | I/O | |
| TM1637 DIO raia 5 | **D8** | PB0 | I/O | |
| TM1637 DIO raia 6 | **D9** | PB1 | I/O | |
| Buzzer passivo | **D10** | PB2 | OUT | opcional (`USAR_BUZZER`) |
| Botão TESTE / rearma | **D11** | PB3 | IN | opcional (`USAR_BOTAO`) |
| Log serial | D0 / D1 | PD0/PD1 | — | 115200, pelo USB |
| **5 V** | — | — | — | displays e sensores |
| **GND** | — | — | — | massa comum |

Sobram livres **D12 (PB4)** e **D13 (PB5)**. Só.

## As três amarrações que não dá para mexer

1. **Os sensores têm que ser A0–A5, nessa ordem.** O 328P só tem duas
   interrupções externas de verdade (D2 e D3); para seis pistas a saída é a
   interrupção de mudança de pino, e A0–A5 são a PORTC inteira, que cai toda
   numa única `PCINT1`. A rotina lê `PINC` de uma vez. Trocar dois sensores
   de pino troca as raias.
2. **A largada tem que ser D2 ou D3.** São os únicos pinos com interrupção
   externa. D3 já é o CLK dos displays, então sobra D2.
3. **Seis raias é o teto.** A PORTC só expõe seis pinos no conector — PC6 é
   o RESET. O Nano tem A6/A7, mas eles são **só analógicos**: não têm
   registrador de entrada digital nem PCINT, e portanto não servem para
   sensor. Para sete ou mais raias, o caminho é outro micro (o RP2040 da
   pasta vizinha tem folga para nove).

## Armadilhas conhecidas desta pinagem

- **`tone()` usa o Timer2**, e isso desliga o `analogWrite` dos pinos **D3 e
  D11**. Aqui não dá problema porque D3 é saída digital (CLK) e D11 é
  entrada (botão) — nenhum dos dois usa PWM. Mas se um dia alguém quiser um
  LED com brilho variável, não pode ser nesses dois.
- **D10 a D13 são o barramento SPI** (SS, MOSI, MISO, SCK). O projeto usa
  D10 e D11 para buzzer e botão. Se um dia entrar um cartão SD para gravar
  os tempos, mude buzzer e botão para D12/D13 antes de ligar o SPI.
- **D13 tem o LED de bordo**, com resistor para o GND. Não serve como
  entrada com pull-up (o LED puxa o nível para baixo). Se precisar de mais
  uma entrada, use D12.
- **D0/D1 são a serial**. Ligar qualquer coisa neles atrapalha a gravação
  pelo USB e o log dos tempos.

## Cabeamento sugerido

Cada TM1637 precisa de 4 fios e cada TCRT5000 de 3 (VCC, GND e D0 — o A0
do módulo fica solto; não confundir com o **pino** A0 do Arduino, que recebe
o D0 do sensor da raia 1). Em vez de puxar tudo até a placa:

- **5 V e GND** em duas barras percorrendo o painel, com os módulos
  pendurados nelas (é assim que o `diagram.json` e o
  [diagrama de fiação](fiacao-arduino.svg) estão desenhados).
- **CLK** também em cascata, um fio curto de um display para o outro. O
  módulo preto de 0,56" tem header dos dois lados, o que deixa isso trivial.
- Só os **6 DIO** dos displays e os **6 D0** dos sensores voltam
  individualmente à placa.
