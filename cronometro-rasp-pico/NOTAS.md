# Notas do projeto — decisões, medidas e armadilhas

Histórico do que foi decidido e por quê, para não refazer o raciocínio
depois. Escrito na primeira montagem do firmware + simulador (set/2026).

## Ponto de partida

`projeto.txt` e três capturas do vídeo original. Do vídeo saiu o
comportamento do painel, que não estava escrito em lugar nenhum:

- durante a prova os displays das raias que ainda não chegaram ficam
  ocupados (no vídeo, com todos os segmentos acesos);
- **assim que um carro cruza, aquele display passa a mostrar a colocação**,
  um dígito só, alinhado à direita;
- alguns segundos depois, todos trocam para o tempo, no formato `3.721` —
  quatro dígitos com o ponto **depois do primeiro**, o que só é possível nos
  módulos TM1637 com ponto decimal por dígito, não nos de relógio.

Aqui a raia que ainda corre mostra o **cronômetro correndo** em vez de
`8888`: é mais informativo e prova na hora que a largada pegou.

## Decisões de hardware

**Os seis TM1637 dividem o mesmo CLK.** O TM1637 não tem endereço — quem
seleciona o chip é a linha DIO, porque a transação só começa numa condição
de START (DIO descendo com CLK alto). Enquanto se escreve numa raia, os
outros cinco veem o clock com o DIO deles parado em nível alto e ignoram
tudo. Custa 7 GPIOs em vez de 12 e um fio curto entre displays vizinhos em
vez de doze fios até o Pico. `src/config.c` tem a tabela `PIN_TM_DIO[]`;
voltar para um CLK por display é mudar a estrutura em `display.c` para
guardar um `clk` diferente por raia — o driver já recebe `{clk, dio}` por
display justamente para isso.

**CLK é push-pull, DIO é dreno aberto emulado.** O CLK só é dirigido pelo
mestre, e com seis módulos pendurados (cada um com seu pull-up de 10 k) um
dreno aberto teria que puxar ~1,7 k. Já o DIO precisa ser solto para o
display dar ACK: o valor de saída fica em 0 para sempre e o que muda é a
**direção do pino** — assim nunca existe o instante entre "escrever 0" e
"virar saída" que geraria um pulso espúrio.

**Sensores em GPIOs contíguos (GP2–GP7)** — não por necessidade (a captura
é por interrupção, com carimbo de `time_us_64()`), mas porque isso deixa a
porta aberta para amostrar as seis raias num único `gpio_get_all()` se um
dia o polling for preferível, e porque facilita conferir o cabo flat.

**Nada em GP23/24/25/29.** No Pico oficial são o regulador, o sensor de VBUS
e o LED, e nem saem nos furos. Usá-los amarraria o projeto à placa roxa.

## Decisões de firmware

**A interrupção só carimba a hora.** Toda decisão fica no laço principal.
Isso é o que permite escrever nos seis displays por bit-bang (uns 4 ms por
rodada de atualização) sem perder precisão: o `time_us_64()` do carimbo já
aconteceu. A precisão do cronômetro **não depende** do período do laço.

**A primeira borda da largada é a boa.** Microswitch repica, mas o repique
vem sempre *depois* da primeira transição, nunca antes. Então não existe
janela de debounce por tempo na largada: a ISR guarda a primeira borda e
ignora as seguintes até o laço consumir. Uma janela por tempo aqui só
atrasaria o `t0` sem ganhar nada.

**As chegadas são ordenadas por tempo antes de numerar.** Duas raias podem
disparar dentro da mesma volta do laço, e nesse caso a ordem em que os
*flags* são varridos é a ordem das raias, não a ordem de chegada — numerar
direto daria a 1ª colocação para a raia de número menor. O laço recolhe
todos os eventos pendentes, ordena por carimbo e só então atribui as
colocações. É o tipo de erro que aparece uma vez em cada vinte provas e
depois nunca mais, então melhor não deixar existir. A corrida demo sorteia
tempos garantidamente **distintos** pela mesma razão: se dois pudessem
empatar em ms, o desempate cairia na ordem do laço e esconderia justamente
o erro que se quer testar.

**`TEMPO_MIN_MS` (150 ms) é o piso do que é uma chegada.** Abaixo disso é
repique do microswitch ou sombra, e a raia continua armada — o disparo é
descartado, não marcado como chegada. Vai para o log como `[ruido]`.

**A prova fecha por três caminhos:** todos chegaram, 8 s depois do primeiro
colocado, ou 15 s no total. O segundo é o que importa na prática: numa prova
com 4 carros, esperar os 15 s cheios deixaria o painel parado à toa.

**Fechar a porta rearma.** É o gesto que o operador faz de qualquer jeito
para montar a próxima prova, então não precisa de botão. O botão TESTE
existe para abortar e para a corrida demo, e é opcional (`USAR_BOTAO`).

**`REFRESH_CORRIDA_MS` = 43, e não 50.** Com 50 ms o último dígito do
milissegundo fica parado em 0 e o penúltimo só alterna 0/5 — parece display
quebrado. Com 43 os dez algarismos aparecem e a leitura fica com cara de
cronômetro de verdade. Qualquer valor não redondo serve; o que não serve é
um divisor de 10.

**Duas maneiras de rodar a corrida demo**, porque cada uma cobre um caso:
segurar o botão (rápido, é o que se usa no simulador) e **tapar o sensor da
raia 1 por 2 s** (funciona na bancada sem botão nenhum, só com a mão — e de
quebra prova que a polaridade do sensor está certa). A segunda só rearma
depois que o sensor volta ao repouso, senão um sensor com fio solto ficaria
disparando demos em série.

**As chegadas da demo entram pelo mesmo `registra_chegada()` das reais.**
Um modo demo que escrevesse direto no resultado testaria só a formatação.
Assim ele testa ordenação, colocação, som, log e ciclo de resultado — tudo
menos a borda do GPIO.

**Teste de fiação no boot:** `8888` em todos, depois o número da própria
raia em cada um. Um display apagado ou mostrando o número de outra raia
aponta o defeito no DIO daquele display, sem precisar depurar firmware. O
ACK de cada TM1637 também é conferido e vai para o log serial.

## Armadilhas de hardware anotadas antes de montar

- **TM1637 em 5 V queima o GPIO.** O DIO é bidirecional e o pull-up do
  módulo o mantém na tensão de alimentação; o RP2040 não é tolerante a 5 V.
  Tudo em 3,3 V. Detalhes em `docs/bom.md`.
- **Consumo:** seis TM1637 no brilho máximo podem passar de 200 mA, contra
  ~300 mA que o regulador do Pico entrega. Por isso `TM1637_BRILHO` = 4.
- **O LDR é o ponto fraco, e a conta que eu tinha feito estava errada.**
  Na primeira versão destas notas eu calculei a sombra a partir da largura
  do sensor (~10 mm → ~3 ms). Está errado: quem define quanto tempo o feixe
  fica tapado é o **comprimento do carro** (~68 mm), não o sensor. São
  18–36 ms conforme a velocidade — tempo bem maior do que eu supunha.
  Só que a conclusão **não melhorou**, mudou de motivo: o problema não é a
  janela ser curta demais, é o **atraso do LDR não ser igual nas seis
  raias**. Os tempos do vídeo original separam colocações vizinhas por 116,
  33, **17**, 41 e 99 ms — a disputa mais apertada foi decidida por 17 ms, e
  a diferença de resposta entre LDRs do mesmo lote é dessa mesma ordem.
  E o modo de falha é o pior possível: quanto mais rápido o carro, menor a
  janela; quem o LDR tem mais chance de perder é justamente **o mais
  rápido**. Uma falha que escolhe o vencedor é pior do que uma aleatória.
  Veredito: **barreira infravermelha** (LED IR + fototransistor atravessando
  a raia), que responde em microssegundos e cuja borda é geométrica, não
  fotométrica. Refletivo tipo TCRT5000 **não** serve para prova: o ponto de
  disparo depende da cor e da altura do carro. Detalhes e o circuito de três
  componentes em `docs/bom.md`.
  **Nada disso muda o firmware:** a chegada é borda num pino digital e
  `SENSOR_NIVEL_CARRO` cobre a polaridade. Os módulos LDR já comprados
  também não se perdem — o LM393 deles aceita um fototransistor no lugar do
  LDR.

## Sobre o simulador

`diagram.json` + `wokwi.toml`, no mesmo esquema do projeto Pong: a extensão
**Wokwi for VS Code** roda o `.elf` compilado de verdade num RP2040 emulado.
A pasta `cronometro-rasp-pico` tem que ser a **raiz do workspace**, senão os
caminhos do `wokwi.toml` não batem.

Escolhas do diagrama que não são cosméticas:

- **Chave deslizante, não botão, para a porta de largada.** A porta é um
  estado (aberta/fechada), não um toque. Com a chave, "fechar a porta"
  rearma de verdade, que é o ciclo real. O contato da direita fica **solto**
  de propósito: quem define o nível alto é o pull-up interno do RP2040,
  exatamente como no circuito real com o microswitch ligado ao GND.
- **Bounce ligado na chave.** É o que testa a regra da primeira borda.
- **Uma fileira de seis**, displays e sensores alinhados, raia 1 à esquerda,
  em vez do 3×2 do painel original — no simulador a corrida fica legível da
  esquerda para a direita.
- Alimentação e CLK em **cascata** de um módulo para o vizinho, que é como
  se cabeia de verdade e reduz de 42 para 14 os fios longos até o Pico.

### O que a primeira rodada no Wokwi ensinou

Três coisas só apareceram com o simulador aberto, e as três são sobre o
`diagram.json`, não sobre o firmware:

- **Sem waypoints, o Wokwi liga pino a pino em linha reta.** Não há
  roteamento automático. Como os pinos do TM1637 e do módulo de sensor ficam
  todos na **borda esquerda**, encadear a alimentação de um módulo para o
  vizinho desenhava uma linha reta por cima da cara do display — três riscos
  atravessando os seis dígitos. A correção é a mini-linguagem de waypoints
  (`"h-20"`, `"v120"`, com `"*"` separando o lado de origem do de destino):
  todo fio **sai para a esquerda e desce até um corredor livre** antes de
  correr na horizontal. Como os dois pinos de um encadeamento têm o mesmo
  deslocamento dentro da peça, dar o mesmo `v` nas duas pontas garante um
  traço perfeitamente horizontal por baixo dos módulos.
- **A ordem do array `parts` é a ordem de desenho, e quem vem depois fica
  por cima — inclusive capturando o clique.** Um `wokwi-text` posicionado
  em cima da chave deslizante deixou a chave **impossível de usar**. Textos
  agora ficam em regiões onde nenhuma peça e nenhum fio passam (rótulos
  acima dos displays, bloco de ajuda à direita da pista 6).
- **O layout tem que reservar corredores**, não só espaçar as peças: uma
  faixa horizontal livre entre displays e sensores, outra entre sensores e
  o Pico, e uma coluna livre entre cada par de módulos. O Pico foi parar no
  vão entre os módulos 2 e 3 para que os fios da coluna esquerda dele subam
  por essa coluna sem atravessar peça nenhuma.

Uma consequência prática do primeiro ponto: **arrastar uma peça no Wokwi
refaz o traçado**. Se um fio incomodar, mover a peça é mais rápido do que
mexer nos waypoints.

Mais duas descobertas, da segunda rodada:

- **O `wokwi-tm1637-7segment` é o módulo de relógio.** O bit 7 de um dígito
  acende os **dois-pontos centrais**, não um ponto decimal — então o tempo
  saía `37:21` em vez de `3.721`. `DISPLAY_PONTO_DECIMAL` passou a ser `0`
  por padrão: quatro dígitos limpos, `3721`, que se lê 3,721 s. Só que isso
  criou uma ambiguidade — sem separador, `1234` tanto pode ser 1,234 s como
  12,34 s. A saída foi dar um *significado* ao separador: **acima de 10 s ele
  acende nos dois tipos de módulo**. Aceso quer dizer "formato SS.mm",
  apagado quer dizer "formato S.mmm". No módulo de ponto sai `12.34`, no de
  relógio `12:34`, e os dois se leem igual.
- **O Wokwi não tem fototransistor nem barreira óptica.** Tem LDR e tem
  receptor IR de 38 kHz — e o de 38 kHz não serve para barreira, porque tem
  AGC e espera rajadas, não feixe contínuo. A barreira virou então **o que o
  GPIO realmente enxerga**: pull-up de 10 kΩ para 3V3 e uma chave para o GND,
  com a `wokwi-slide-switch` fazendo o papel do fototransistor (esquerda =
  conduzindo = feixe passando = 0; direita = aberto = carro cortou = 1).
  Ficou mais honesto que o módulo LDR *e* mais rápido de usar: um clique por
  chegada, e o estado de cada raia fica visível. Os LEDs IR não entram no
  diagrama de propósito — são um ramo sempre aceso que nunca toca o Pico.

### Som

O buzzer do Wokwi é onda quadrada, e agudo curto some. A largada virou um
tom **grave e longo** (330 Hz, 600 ms — cara de buzina de largada), a
chegada um bip curto que **desce 150 Hz por colocação** (dá para ouvir quem
chegou em que lugar sem olhar), e o fim da prova um 220 Hz de 450 ms. Tudo
em `config.h`, na seção de sons.

### Tempo de placar

Colocação 4,5 s e tempo 7 s, alternando. Com a porta **aberta** o placar
fica lá até alguém fechá-la — é o caso real, o operador lê com calma. O
rearme automático (`RESULTADO_MIN_MS`, 23 s = dois ciclos inteiros) só vale
quando a porta já está fechada, que é o caso da corrida demo.

O que o simulador cobre e o que não cobre está em `docs/como-simular.md`.
Resumo do que **não** cobre: velocidade do sensor, consumo e ruído de cabo.

## O port para Arduino

Feito depois que a versão RP2040 estava pronta, e de propósito **sem**
reescrever a lógica: mesma máquina de estados, mesmos tempos, mesmos nomes
de função em camelCase. O detalhamento está em
`../cronometro-arduino/docs/diferencas-rp2040.md`; aqui ficam só as três
coisas que mudaram alguma **decisão**, não só a sintaxe.

- **O ATmega328P só tem duas interrupções externas** (D2 e D3) — não dão
  para seis pistas. A saída foi a interrupção de *mudança de pino*: as seis
  barreiras foram para **A0–A5**, que são a PORTC inteira e caem todas numa
  única `PCINT1`; a rotina lê `PINC` de uma vez e descobre quem mudou pelo
  XOR com a leitura anterior. Isso **amarra a raia *i* ao pino A*i***, e
  fixa o teto do projeto em **seis raias** nessa placa: a PORTC só expõe
  seis pinos no conector, e o A6/A7 do Nano é só analógico, sem PCINT.
- **Os 5 V do AVR resolvem de graça a armadilha mais perigosa do RP2040.**
  Lá, alimentar o TM1637 em 5 V colocaria 5 V no DIO, por causa do pull-up
  do módulo, direto num pino que não tolera isso. No Arduino o display vai
  na tensão nativa dele e ainda fica mais brilhante. A única mudança de
  material é o resistor do LED IR: 330 Ω em 5 V no lugar de 220 Ω.
- **`micros()` tem 32 bits e estoura em 71,6 minutos.** Toda conta de tempo
  virou subtração sem sinal (`agora - t0`), que atravessa o estouro
  corretamente — em lugar nenhum existe `agora > t0 + X`. Escrever isso
  expôs um detalhe que estava **errado também no RP2040**: em `tick_armado`
  a bandeira da largada era baixada *antes* de o carimbo ser lido, e um
  repique da porta nesse intervalo podia trocar `largada_us` debaixo da
  leitura. Agora as duas versões leem o carimbo primeiro. É o mesmo cuidado
  que o laço já tinha com os sensores, que eu não tinha aplicado aqui.

Sobre ferramentas: o código Arduino está num arquivo `.ino` só porque o
caminho mais curto para ver a coisa rodando é colá-lo no **wokwi.com**, que
compila na nuvem. Antes de o `arduino-cli` existir nesta máquina, o sketch
foi verificado com `arm-none-eabi-g++ -fsyntax-only -Wall -Wextra` contra um
stub da API do Arduino — vale registrar que isso **funcionou**: quando o
avr-gcc finalmente compilou o sketch com `--warnings all`, não apareceu
nenhum aviso novo (os únicos que saíram são do `new.cpp` do próprio core do
Arduino). É um truque reaproveitável quando falta o compilador certo: pega
todo erro de C++ e de tipo, só não pega o que é específico do alvo.

Hoje o `arduino-cli` 1.5.2 está instalado em `C:\Users\Leonardo\arduino-cli`
com o core `arduino:avr`, e a compilação de verdade mede: **9202 bytes de
programa (28 % do UNO, 29 % do Nano) e 465 bytes de RAM (22 %)**. Isso
também destravou o **simulador local** para a versão Arduino: a extensão
Wokwi do VS Code nunca compilou nada — ela carrega um binário pronto, e o
`.hex` do avr-gcc serve tão bem quanto o `.uf2` do Pico SDK. O que faltava
era quem produzisse o `.hex`.

## TCRT5000, desenhos e preparação para o GitHub (set/2026)

**O sensor virou TCRT5000**, por decisão de projeto: é o módulo à mão. O
raciocínio contra o LDR continua valendo (a disputa mais apertada do vídeo foi
decidida por 17 ms), e o TCRT5000 é infravermelho de verdade — fototransistor
e LM393, resposta em microssegundos. A ressalva que eu tinha anotado contra
ele ("é refletivo, depende do carro") não sumiu: virou **instrução de
montagem**. Por baixo da pista, olhando para cima, com o fundo do carro a
2–5 mm, e os seis trimpots ajustados com o mesmo carro. Se algum carro teimar,
aquele ponto vira barreira sem mexer no firmware — só a polaridade.

Três coisas saíram das fotos dos módulos, e não de datasheet:

- **O D0 do TCRT5000 cai para 0 com o carro** (coletor aberto do LM393, com
  pull-up no módulo). `SENSOR_NIVEL_CARRO` virou `0` nas duas versões. No
  Wokwi, a peça de luz tem o mesmo header (VCC/GND/DO/AO) e a mesma lógica —
  escuro = sem carro = 1 —, então o diagrama voltou a usá-la, com `lux` em 0.
- **O pull-up do D0 vai para o VCC do módulo.** É a armadilha do TM1637 de
  novo: no RP2040, sensor alimentado em 5 V põe 5 V num GPIO que não tolera.
  Na versão Pico, displays **e** sensores vão em 3,3 V.
- **O resistor do LED IR é o `181` (180 Ω), e esse LED nunca apaga**: ~13 mA
  por módulo em 3,3 V, ~24 mA em 5 V. Somado aos displays, o 3V3 do Pico
  chega a 200–260 mA, perto do que a Raspberry recomenda para esse pino. Daí a
  recomendação de um regulador 3,3 V separado na versão RP2040.

E uma do display: o módulo preto de 0,56" tem um ponto embaixo de cada dígito
**no vidro**, mas isso não garante que o ponto esteja ligado ao TM1637. Não dá
para saber olhando, então o teste de fiação do boot passou a acender `0xFF` —
todos os segmentos e todos os pontos —, e o primeiro quadro diz qual valor de
`DISPLAY_PONTO_DECIMAL` usar.

### Os diagramas de fiação (SVG)

O pedido era "como no simulador, mas mais fácil de entender". O simulador
desenha 48 fios porque cada módulo puxa a própria alimentação até a placa; o
diagrama troca isso por **barramentos** de V+, GND e CLK com derivações
curtas. Sobram ~18 fios desenhados — que é também como se cabeia de verdade.

Olhar o render achou três defeitos que o código não mostrava: o barramento de
CLK começava no pino da placa e deixava a derivação do display 1 **solta no
ar** (o display 1 fica à esquerda do pino); os rótulos dos pinos ficavam logo
abaixo do pad e eram **atravessados pela própria derivação**; e as notas do
rodapé vazavam da caixa. Vale para qualquer desenho gerado: ler o código não
substitui olhar a imagem.

Depois, olhando o desenho pronto, apareceram **fios de sinal passando uns por
cima dos outros**: D4/D5 e A4/A5 no Arduino, GP10/GP11 e GP6/GP7 no Pico, e
ainda o fio do display 1 cortando a descida do CLK. A causa é geométrica.
Cada fio é um "Z" — desce do módulo, anda numa faixa, desce no pino — e dois
Zs se cruzam quando o trecho horizontal de um contém o pad ou o pino do
outro. A correção não foi trocar a ordem das faixas: foi escolher os pinos da
placa de modo que os trechos horizontais fiquem **disjuntos**, o que elimina
o cruzamento em qualquer ordem, e tirar o CLK da borda de cima da placa. Como
"parece certo" já tinha falhado uma vez, o gerador agora **confere** segmento
a segmento e sai com erro se achar cruzamento — e antes se autotesta contra o
caso D4/D5 antigo, para o "nenhum cruzamento" dele valer alguma coisa. O único
cruzamento entre fios que não dá para evitar (o 3V3 da placa passando pela
coluna de GND) ganhou uma ponte em arco.

### Os esquemas do KiCad

Gerados por `tools/gen_kicad_sch.py`, que **lê os símbolos da biblioteca do
KiCad instalado** — posição e número de cada pino — em vez de copiá-los.
Ligações por rótulo de rede, alimentação por símbolo de power (rotacionado na
ponta de cada toco, porque os pinos de um header ficam a 2,54 mm e símbolos em
pé se sobreporiam), no-connect em todo pino livre. Duas decisões foram impostas
pelo ERC:

- **Arduino:** os três GND do símbolo do UNO são `power_in` e nada "dirige" a
  rede — ela leva um `PWR_FLAG`.
- **Pico:** o AGND fica sem ligação. Ele e o GND são `power_out` no símbolo, e
  uni-los é erro de ERC; como o ADC não é usado, não faz falta.

**ERC limpo não prova que o esquema está certo** — prova que não há pino solto
nem alimentação sem fonte. Um rótulo `DIO_3` no pino errado passa no ERC. Por
isso o `--verificar` exporta o **netlist** pelo próprio KiCad e confere rede
por rede contra a pinagem do firmware. Os dois esquemas saíram com ERC 0/0 e o
netlist conferindo em todas as redes.

O ERC também não vê **texto encavalado**, e dois casos só apareceram no render
(o painel do navegador não abria o SVG exportado, de 1,2 MB; o Edge do Windows
em modo headless renderizou recortes em PNG sem instalar nada):

- **O KiCad compõe o ângulo de um campo com a rotação do símbolo**, e quando a
  soma dá 180° desenha na horizontal mas **inverte a justificação**. Com o
  campo a 0°, o "GND" de um símbolo girado saía vertical; com o campo a 90°,
  saía horizontal mas em cima do próprio desenho — só nos símbolos girados
  90°, não nos de 270°, e foi essa assimetria que denunciou a regra. O certo é
  girar o campo por −rotação: a soma zera e nada é invertido.
- **Rótulo de rede fica acima do fio**, não centrado nele. Nos TCRT5000 o
  `SENSOR_n` do pino 3 subia até encostar no "GND" do pino 2, logo acima; o
  toco do rótulo ficou mais comprido para desencontrar os dois na horizontal.

### Repositório

A pasta do Pico virou `cronometro-rasp-pico`, e o alvo do CMake mudou junto,
para o `.uf2` ter o nome da pasta. O repositório vai se chamar
`cronometro-hotwheels`, com licença GPL-3.0-or-later. Ficam **fora** dele,
pelo `.gitignore` da raiz, as fotos de anúncio em `módulos/` e as capturas do
vídeo original — são de terceiros. O `projeto.txt`, as notas iniciais com os links do
anúncio e do vídeo, também fica fora.

**Licença dupla, a mesma do Pong:** software (firmwares, geradores, circuito do
simulador) em GPL-3.0-or-later; hardware (KiCad, diagramas de fiação, `bom.md`,
`pinout.md`) em CERN-OHL-S-2.0, com o texto em `LICENSE-HARDWARE.txt` e o
detalhamento por arquivo em `NOTICE`. A fronteira que vale lembrar: o script
que gera um desenho é software, mas o desenho que ele produz é hardware — por
isso os SVGs levam `SPDX-License-Identifier: CERN-OHL-S-2.0` e o carimbo dos
esquemas repete a linha de licença dos esquemas do Pong.

## Estado atual

- **RP2040:** compila limpo no Pico SDK 1.5.1 (`build/cronometro-rasp-pico.uf2`).
- **Arduino:** compila limpo no `arduino-cli` 1.5.2 — 9252 bytes de programa
  (28 %) e 465 bytes de RAM (22 %).
- **Simuladores:** Wokwi das duas versões, com o TCRT5000 modelado pela peça de
  luz. As duas rodaram no VS Code antes da troca de sensor.
- **Desenhos:** diagramas de fiação em SVG e esquemas do KiCad 10 das duas
  placas, com ERC 0/0 e netlist conferido.
- Nada montado em hardware.

## Próximos passos prováveis

1. Um TCRT5000 por baixo de uma raia: achar a distância e o ponto do trimpot
   que disparam com **todos** os carros da coleção e não disparam com a raia
   vazia.
2. Ligar um display e olhar o primeiro quadro do boot: ponto por dígito
   (`DISPLAY_PONTO_DECIMAL = 1`) ou só dois-pontos (`0`).
3. Na versão RP2040, medir a corrente do 3V3 com tudo aceso e decidir pelo
   regulador separado.
4. Mesmo carro, cinco descidas na mesma raia, e olhar a dispersão no log
   serial. Depois trocar os sensores de raia, para separar viés de sensor de
   atrito de raia.
5. Publicar no GitHub como `cronometro-hotwheels`.
6. Só então o painel e a fiação definitiva.
