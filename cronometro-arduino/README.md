# Cronômetro Hot Wheels — 6 pistas (Arduino UNO / Nano)

Mesmo projeto da pasta [`cronometro-rasp-pico`](../cronometro-rasp-pico/),
portado para o **ATmega328P**. Comportamento idêntico; o que muda é a
plataforma, e isso está registrado em
[docs/diferencas-rp2040.md](docs/diferencas-rp2040.md).

- Um **microswitch** na porta que solta os carrinhos marca o `t0`.
- Um **sensor infravermelho TCRT5000** no fim de cada raia marca a chegada,
  pela saída digital D0.
- Seis **displays TM1637** mostram a **colocação** (1 a 6) assim que cada
  carro cruza, e depois o **tempo** (`3721` = 3,721 s).

O código é **um arquivo só** de propósito: assim cabe num único "colar" no
wokwi.com, que compila na nuvem e não exige nada instalado.

## Desenhos

- [**Diagrama de fiação**](docs/fiacao-arduino.svg) — módulos, barramentos e cada fio com o
  nome do pino. É o que se segue na montagem.
- [**Esquema KiCad 10**](kicad/) — abra `kicad/cronometro-arduino.kicad_pro`; também
  exportado em [SVG](docs/esquema-kicad.svg) e [PDF](docs/esquema-kicad.pdf).

![Diagrama de fiação](docs/fiacao-arduino.svg)

Os dois são gerados pelos scripts em `tools/`, na raiz do repositório — ver o
README de lá.

## Rodar no simulador — sem instalar nada

1. Abra **[wokwi.com](https://wokwi.com)** → *New Project* → **Arduino Uno**.
2. Na aba `sketch.ino`, apague tudo e cole o conteúdo de
   [cronometro-arduino.ino](cronometro-arduino.ino).
3. Na aba `diagram.json`, apague tudo e cole o conteúdo de
   [diagram.json](diagram.json).
4. Play. Passo a passo do que fazer dentro do simulador em
   [docs/como-simular.md](docs/como-simular.md).

> Vantagem deste caminho: não precisa compilar nada. Mas o **simulador
> local do VS Code também funciona** — ver
> [docs/como-simular.md](docs/como-simular.md).

## Compilar e gravar na placa

O **arduino-cli** já está instalado nesta máquina, em
`C:\Users\Leonardo\arduino-cli\arduino-cli.exe`, com o core `arduino:avr`.
Ele não está no PATH; ou use o caminho completo, ou rode uma vez:

```powershell
[Environment]::SetEnvironmentVariable('Path', $env:Path + ';C:\Users\Leonardo\arduino-cli', 'User')
```

Compilar (de dentro da pasta `cronometro-arduino`):

```powershell
& "C:\Users\Leonardo\arduino-cli\arduino-cli.exe" compile -b arduino:avr:uno --warnings all --output-dir build .
```

Gravar (troque a porta pela que aparecer em `arduino-cli board list`):

```powershell
& "C:\Users\Leonardo\arduino-cli\arduino-cli.exe" upload -b arduino:avr:uno -p COM3 .
```

Para Nano, troque `arduino:avr:uno` por `arduino:avr:nano` (se a placa for
clone com bootloader antigo: `arduino:avr:nano:cpu=atmega328old`).

Pelo **Arduino IDE** funciona igual: abra a pasta, escolha a placa, Upload.

**Ocupação medida** (compilado, não estimado): programa **9202 bytes**,
28 % dos 32 KB do UNO (29 % dos 30 KB do Nano, que tem bootloader maior);
variáveis globais **465 bytes**, 22 % da RAM, sobrando 1583 bytes. Cabe com
muita folga.

## Ligações

| Função | Pino | Observação |
| --- | --- | --- |
| Sensores TCRT5000 (D0) das raias 1 a 6 | **A0 a A5** | **a ordem é obrigatória** — ver abaixo |
| Microswitch da porta | D2 | precisa ser D2 ou D3 (interrupção externa) |
| TM1637 **CLK** (comum aos seis) | D3 | |
| TM1637 DIO das raias 1 a 6 | D4, D5, D6, D7, D8, D9 | |
| Buzzer passivo (opcional) | D10 | |
| Botão TESTE / rearma (opcional) | D11 | |
| Log serial | D0/D1 (USB), 115200 | |
| Alimentação | 5 V e GND | displays e sensores |

Sobram livres só **D12 e D13**. Tabela completa, com as duas placas, em
[docs/pinout.md](docs/pinout.md).

**Por que os sensores têm que ser A0..A5, nessa ordem:** o ATmega328P só
tem **duas** interrupções externas de verdade (D2 e D3) — não dão para seis
pistas. A saída é a interrupção de *mudança de pino*: A0–A5 são a PORTC
inteira, e as seis cabem numa única `PCINT1`. A rotina lê a porta de uma vez
e descobre quem mudou pelo XOR com a leitura anterior. Isso amarra a raia
*i* ao pino A*i* — por isso não existe tabela de pinos para elas, ao
contrário dos displays.

**Tudo em 5 V**, e aqui isso é uma vantagem: o TM1637 trabalha na tensão
nativa dele (fica mais brilhante) e o DIO em 5 V não é problema nenhum,
porque o 328P é uma peça de 5 V. Na versão RP2040 isso era a armadilha mais
perigosa do projeto.

## Como se comporta

| Estado | Displays | Sai daqui quando |
| --- | --- | --- |
| **Armado** | `----` fixo (ou piscando, se a porta estiver aberta) | a porta abre |
| **Correndo** | cronômetro correndo; quem chega troca para a colocação | todos chegam, ou 8 s depois do 1º, ou 15 s no total |
| **Resultado** | alterna colocação (4,5 s) ↔ tempo (7 s) | a porta fecha (ou o botão TESTE) |

- Carro que não passa pelo sensor aparece como `dnF` e `----`.
- **Fechar a porta rearma** — não precisa de botão para a próxima prova.
- Ao ligar, cada display acende **tudo** (segmentos e pontos) e depois o
  número da própria raia:
  se um ficar apagado ou mostrar o número de outra raia, o erro está no DIO
  dele, não no código. O primeiro quadro também revela se o módulo liga um
  ponto por dígito — ver `DISPLAY_PONTO_DECIMAL`.
- **Corrida demo** (para ver o painel sem carrinho): segure o botão TESTE
  por 1 s, ou segure um carrinho sobre o sensor da raia 1 por 2 s com a prova armada.

## Ajustes

Tudo no bloco **CONFIGURAÇÃO** no topo de
[cronometro-arduino.ino](cronometro-arduino.ino):

| Constante | Para quê |
| --- | --- |
| `SENSOR_NIVEL_CARRO` | `0` (padrão) é o TCRT5000: D0 cai com o carro. `1` se o seu lote for invertido |
| `LARGADA_NIVEL_ABERTA` | idem, para o microswitch (contato NA ou NF) |
| `DISPLAY_PONTO_DECIMAL` | `0` (padrão) para o módulo de dois-pontos; `1` para o de ponto por dígito |
| `TM1637_BRILHO` | 0 a 7 — mexe direto no consumo |
| `TEMPO_MIN_MS` | piso abaixo do qual a chegada é considerada ruído |
| `ESPERA_APOS_1o_MS` | quanto esperar os retardatários depois do 1º |
| `USAR_BUZZER` / `USAR_BOTAO` | `0` libera o D10 / D11 |

`N_PISTAS` **não** é ajustável para cima aqui: seis é o teto do 328P, porque
a PORTC só expõe seis pinos no conector. Ver
[docs/diferencas-rp2040.md](docs/diferencas-rp2040.md).

## Material

O mesmo da versão RP2040 —
[lista completa e os avisos elétricos](../cronometro-rasp-pico/docs/bom.md),
inclusive por que o sensor é o TCRT5000 e não LDR, e como montá-lo.

Por causa dos 5 V, aqui **displays e sensores vão direto no 5 V** da placa, e
não é preciso o regulador 3,3 V separado que a versão RP2040 recomenda. A
conta de consumo continua valendo: por USB passa, pelo conector DC de 12 V o
regulador do UNO esquenta.
