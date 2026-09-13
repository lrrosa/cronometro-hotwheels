# O que muda do RP2040 para o ATmega328P

As duas versões fazem a mesma coisa e têm a mesma máquina de estados. Este
arquivo registra só onde a plataforma obrigou a mudar alguma coisa — para
quando um dia for preciso mexer numa e lembrar de mexer na outra.

## 1. Interrupções — a diferença que teve consequência de projeto

| | RP2040 | ATmega328P |
| --- | --- | --- |
| Interrupção por borda | em **qualquer** GPIO, com callback por pino | só **D2 (INT0)** e **D3 (INT1)** |
| Saída para os 6 sensores | um `gpio_set_irq_enabled` por pino | **PCINT** — interrupção de *mudança de pino* |

No AVR, os sensores foram para **A0–A5**, que são a PORTC inteira e caem
todas na `PCINT1`. A rotina lê `PINC` de uma vez e descobre quem mudou pelo
XOR com a leitura anterior:

```c
ISR(PCINT1_vect) {
    const unsigned long agora = micros();
    const uint8_t atual = PINC & 0x3F;
    const uint8_t mudou = atual ^ pincAnt;
    pincAnt = atual;
    ...
}
```

Três consequências:

- **A raia *i* tem que estar em A*i*.** Não existe tabela de pinos para os
  sensores, ao contrário dos displays. Trocar duas de lugar troca as raias.
- **Seis é o teto.** A PORTC só expõe seis pinos no conector (PC6 é o
  RESET). No Nano existem A6/A7, mas eles são **só analógicos**: não têm
  registrador de entrada digital nem PCINT. Na versão RP2040 sobravam pinos
  para oito ou nove raias; aqui, não.
- **Dois sensores que disparem dentro da mesma interrupção recebem o mesmo
  carimbo** e o desempate cai na ordem das raias. Na prática isso exige uma
  diferença menor que o tempo de uma ISR (~5 µs) — uns 15 µm de pista.

A largada ficou em **D2 (INT0)**, com interrupção só dela, porque é a borda
mais importante do sistema.

## 2. Relógio

| | RP2040 | ATmega328P |
| --- | --- | --- |
| Função | `time_us_64()` | `micros()` |
| Largura | 64 bits (não estoura nunca) | **32 bits, estoura em 71,6 min** |
| Resolução | 1 µs | **4 µs** (prescaler /64 do Timer0) |

4 µs é 250 vezes mais fino que o milissegundo que a prova precisa, então a
resolução não é problema. O estouro é: **toda conta de tempo é subtração sem
sinal** (`agora - t0`), que atravessa o estouro corretamente. Em nenhum
lugar existe `agora > t0 + X`, que quebraria. O `somTick()` compara
`(long)(millis() - somFimMs) < 0` pelo mesmo motivo.

`micros()` **pode** ser chamada dentro de uma ISR no AVR: a implementação do
core trata o estouro pendente do Timer0 antes de montar o valor.

## 3. Tensão — aqui o AVR é melhor

O 328P é uma peça de **5 V**, e o TM1637 também. Some a armadilha mais
perigosa da versão RP2040: lá, alimentar o display em 5 V colocaria 5 V no
DIO (pelo pull-up do módulo) direto num pino que **não é tolerante a 5 V**.

O mesmo vale para o TCRT5000, cujo D0 tem pull-up para o VCC do módulo:
aqui ele vai em 5 V sem risco. E os dois ganham com isso — os dígitos ficam
mais brilhantes, e o LED IR do sensor recebe quase o dobro de corrente (o
resistor dele é o mesmo), o que dá mais alcance.

**Consumo:** seis TM1637 a 5 V no brilho 4 dão uns 120–180 mA, e os seis
TCRT5000 mais ~145 mA (o LED IR nunca apaga). Com a placa, 300–380 mA. O
UNO por **USB** aguenta (o polifusível é de 500 mA). Pelo **conector DC de
12 V**, não: o regulador dissiparia mais de 2 W. Alimente por USB ou ponha
5 V direto no pino 5 V.

## 4. Velocidade

16 MHz contra 125 MHz, e no Arduino `digitalWrite`/`pinMode` custam alguns
microssegundos cada (contra alguns nanossegundos do acesso direto ao
registrador). O bit-bang dos TM1637 ficou em ~1,2 ms por display, ~7 ms para
os seis, contra ~4 ms no RP2040.

Não muda nada de importante: com `REFRESH_CORRIDA_MS` em 43, isso é ~17 % do
tempo, e **a precisão do cronômetro não depende do laço** — quem carimba a
hora é a interrupção. Se um dia incomodar, o caminho é acesso direto a
registrador no lugar de `digitalWrite`, não baixar o `TM1637_BIT_US`.

## 5. Memória

2 KB de RAM contra 264 KB. Duas consequências no estilo do código:

- todo texto de log vai em `F("...")`, que o deixa na flash;
- os tempos da corrida demo são `uint16_t` em vez de `uint32_t`.

O sketch usa bem menos que os 2 KB, mas o hábito do `F()` é o que evita a
surpresa de a RAM acabar em silêncio quando alguém acrescentar mensagens.

## 6. Aleatoriedade

Na versão RP2040, `get_rand_32()` do SDK. No AVR, `random()` precisa de
semente, e o truque clássico — `randomSeed(analogRead(A0))` — **não serve
aqui**, porque A0–A5 estão todos ocupados pelas barreiras e nenhum está
solto para captar ruído.

A semente é `micros()` no instante em que a pessoa dispara a primeira
corrida demo. É um gesto humano: a variação natural entre execuções é de
milhares de microssegundos, muito mais do que a demo precisa.

## 7. Ferramentas

| | RP2040 | Arduino |
| --- | --- | --- |
| Compilar | Pico SDK 1.5.1 + CMake + Ninja | Arduino IDE ou `arduino-cli` |
| Gravar | segurar BOOTSEL, copiar `.uf2` | bootloader serial, pelo USB |
| Simulador | extensão Wokwi do VS Code | os dois: extensão do VS Code **ou** wokwi.com (compila na nuvem) |
| Organização | vários `.c`/`.h` | **um `.ino` só**, para caber num paste |

A última linha é o motivo de o código Arduino estar num arquivo só, ainda
que a versão RP2040 seja modular: colar dois arquivos no wokwi.com e apertar
play é o caminho mais curto entre a ideia e ver a coisa funcionando. Mas com
o `arduino-cli` instalado o simulador local do VS Code também roda esta
versão — a extensão Wokwi nunca compilou nada, ela só carrega o binário
pronto, e o `.hex` do avr-gcc serve tão bem quanto o `.uf2` do Pico SDK.

**Ocupação, medida na compilação:** 9202 bytes de programa (28 % do UNO) e
465 bytes de RAM (22 %), sobrando 1583. Contra os 85 KB do binário RP2040 —
que tem 2 MB de flash e 264 KB de RAM para gastar.

## O que NÃO mudou

Vale listar, porque foi o objetivo: máquina de estados, ordenação das
chegadas por carimbo antes de numerar, a regra da primeira borda na largada,
`TEMPO_MIN_MS`, os três caminhos de fim de prova, o rearme pela porta, o
teste de fiação no boot com verificação de ACK, a corrida demo entrando pelo
mesmo caminho das chegadas reais, o `REFRESH_CORRIDA_MS` de 43, os sons e o
formato do tempo. Os nomes das funções são os mesmos, em camelCase.
