# Lista de material e cuidados elétricos

Vale para as duas versões do projeto (RP2040 e Arduino). Onde a tensão de
trabalho muda alguma coisa, está marcado.

## Material

| Qtd | Item | Observação |
| --- | --- | --- |
| 1 | Módulo RP2040 **ou** Arduino UNO/Nano | um dos dois; ver o README da raiz |
| 6 | Módulo display TM1637, 4 dígitos | dos 10 do pacote |
| 6 | **Módulo sensor IR TCRT5000** (VCC, GND, D0, A0) | só VCC, GND e D0 são ligados — ver Aviso 3 |
| 1 | Microswitch com alavanca | na porta que solta os carrinhos |
| 1 | Botão táctil (opcional) | TESTE / rearma |
| 1 | Buzzer passivo (opcional) | |
| 1 | Regulador 3,3 V AMS1117-3.3 | **recomendado na versão RP2040** — ver Aviso 2 |
| — | Fio, barra de pinos, fonte USB 5 V | |
| (10) | Módulos LDR já comprados | ficam de reserva: o TCRT5000 os substituiu |

## Aviso 1 — no RP2040, alimente tudo em 3,3 V, nunca 5 V

> **Este aviso é só da versão RP2040.** No Arduino o problema não existe:
> o ATmega328P é uma peça de 5 V, então o TM1637 vai em 5 V, na tensão
> nativa dele, e ainda fica mais brilhante.

O TM1637 funciona em 5 V, e é tentador ligá-lo no VBUS para os dígitos
ficarem mais brilhantes. **Não faça isso.** O DIO é bidirecional e o módulo
tem um pull-up interno para a própria alimentação: em 5 V, a linha DIO
descansa em 5 V, e é ela que entra direto no GPIO do RP2040 — que **não é
tolerante a 5 V**. Funciona por um tempo e depois mata o pino.

Em 3,3 V os dígitos ficam um pouco menos brilhantes e é só isso.

**Vale igual para o TCRT5000.** O D0 dele é a saída do LM393 em coletor
aberto, com pull-up para o VCC **do próprio módulo**. Alimentado em 5 V, o
D0 descansa em 5 V — de novo direto num GPIO que não tolera. Na versão
RP2040, displays **e** sensores vão em 3,3 V. O LM393 trabalha em 3,3 V
sem ressalva.

## Aviso 2 — consumo: displays e sensores ficam acesos o tempo todo

Os dois consumidores grandes são contínuos: os dígitos do TM1637 e o **LED
infravermelho de cada TCRT5000, que nunca apaga**. No módulo usado aqui o resistor desse LED é o marcado `181` (180 Ω), o que dá:

| | por módulo, 3,3 V | seis, 3,3 V | por módulo, 5 V | seis, 5 V |
| --- | --- | --- | --- | --- |
| TCRT5000 (LED IR + LED de força) | ~13 mA | ~80 mA | ~24 mA | ~145 mA |
| TM1637, brilho 4 | ~15–25 mA | ~90–150 mA | ~20–30 mA | ~120–180 mA |

São estimativas a partir dos resistores e do brilho — **meça** com tudo
aceso antes de fechar a caixa.

**Na versão RP2040** a soma, com o próprio RP2040, fica entre 200 e 260 mA
no pino 3V3, e a Raspberry recomenda não passar de ~300 mA ali. O teste de
fiação do boot, com todos os segmentos e pontos acesos, chega perto disso.
Por isso a recomendação é um **regulador 3,3 V separado** (AMS1117-3.3
alimentado pelo VBUS) para displays e sensores, com o **GND em comum** com o
Pico, deixando o 3V3 do Pico só para ele. Na RP2040 roxa isso pesa mais: o
regulador dela é um linear pequeno, e 250 mA descendo de 5 V para 3,3 V
viram calor. Esquecer a massa comum é a receita clássica para o TM1637
mostrar lixo.

**Na versão Arduino**, tudo em 5 V dá uns 300–380 mA. Por **USB** passa (o
polifusível é de 500 mA). Pelo **conector DC de 12 V**, não: o regulador da
placa teria que dissipar mais de 2 W. Alimente por USB, ou ponha 5 V direto
no pino 5 V.

`TM1637_BRILHO` está em **4** (de 0 a 7). Subir o brilho é o jeito mais
rápido de estourar essa conta.

## Aviso 3 — o sensor de chegada: TCRT5000

**Decidido: módulo TCRT5000** (a plaquinha com LM393 e trimpot), ligado pelo D0. O
raciocínio fica registrado aqui para a discussão não voltar depois.

### A conta

O tempo em que o carro tapa o sensor não depende do tamanho do sensor, e
sim do **comprimento do carro**: um Hot Wheels 1:64 tem ~68 mm. Somando uns
5 mm de feixe:

| Velocidade na chegada | Tempo com o feixe tapado |
| --- | --- |
| 2 m/s | 36 ms |
| 3 m/s | 24 ms |
| 4 m/s | 18 ms |

Agora o outro lado. No vídeo original os seis tempos foram 3.514, 3.630,
3.663, 3.680, 3.721 e 3.820 s. As diferenças entre colocações vizinhas:
**116, 33, 17, 41 e 99 ms**. Ou seja, a disputa mais apertada da prova foi
decidida por **17 ms** — e esse é o número que o sensor precisa resolver com
folga. Para não decidir nada no lugar do carro, o erro entre raias deveria
ficar abaixo de uns 2 ms.

### Por que não LDR

Um LDR de sulfeto de cádmio é um fotocondutor: a resistência muda porque
portadores são presos e liberados na rede cristalina, e isso é lento.

1. **O carro tapando a luz é a direção lenta.** O LDR sobe de resistência
   (escurecendo) bem mais devagar do que desce (clareando) — dezenas de
   milissegundos para chegar perto do valor de escuro.
2. **O que importa é quando ele cruza o limiar, não quando estabiliza.** Dá
   para ganhar tempo ajustando o trimpot com o comparador quase virando. Mas
   aí o ajuste fica na beira: qualquer mudança de luz do ambiente vira
   disparo falso ou chegada perdida.
3. **O erro entre raias é o que estraga, não o erro absoluto.** Se os seis
   sensores atrasassem exatamente igual, o atraso viraria um deslocamento
   constante: some na colocação e some na comparação entre raias. O problema
   é que **não atrasam igual** — LDRs do mesmo lote variam de 30 a 50 % na
   resistência, e cada trimpot fica num ponto ligeiramente diferente. Essa
   diferença é da mesma ordem dos 17 ms que separam duas colocações.
4. **E o modo de falha é o pior possível:** quanto mais rápido o carro,
   menor a janela de sombra. Se algum carro não conseguir manter o sensor
   tapado tempo suficiente para o LDR cruzar o limiar, será justamente **o
   carro mais rápido** que não vai registrar. Uma falha que escolhe o
   vencedor é pior do que uma falha aleatória.

### Por que o TCRT5000 serve

O TCRT5000 é um LED infravermelho e um fototransistor lado a lado, olhando
para o mesmo lado; o módulo acrescenta um comparador LM393 com trimpot. O
fototransistor responde em microssegundos, e o comparador também: a borda
chega ao pino em bem menos de 1 ms, muito abaixo dos 17 ms que decidem uma
colocação.

### O cuidado: ele é refletivo

Ao contrário de uma barreira (LED de um lado, receptor do outro), o TCRT5000
dispara quando **alguma coisa reflete** o infravermelho de volta. O ponto
exato em que ele vira depende de quanto o fundo do carro reflete e de quão
perto ele passa. É administrável, mas precisa ser feito:

1. **Monte por baixo da pista, olhando para cima**, por um furo no piso da
   raia, com o fundo do carro passando a **2–5 mm** do sensor. O TCRT5000 tem
   o pico de sensibilidade em ~2,5 mm e perde muito a partir de ~10 mm: a
   distância pesa mais do que a cor.
2. **Ajuste os seis trimpots com o mesmo carro** parado sobre cada sensor:
   gire até o LED de saída acender com o carro e apagar com a raia vazia, e
   deixe no meio dessa faixa.
3. **Teste com a frota de verdade.** Fundo preto fosco reflete pouco. Se
   algum carro não disparar, aproxime o sensor antes de mexer no trimpot.
4. **Tire luz direta de cima dos sensores.** Sol e lâmpada incandescente têm
   muito infravermelho.
5. **Na versão RP2040 os TCRT5000 vão em 3,3 V** (Aviso 1), o que dá menos
   corrente no LED IR e um pouco menos de alcance: fique no lado de baixo da
   faixa de distância, 2–3 mm.

### Polaridade: o D0 cai para 0 com o carro

Sem carro nada reflete e o D0 fica em **1**; com o carro em cima o
comparador vira, o D0 vai a **0** e o LED de saída do módulo acende. Por
isso `SENSOR_NIVEL_CARRO` é **0** nas duas versões.

Há lotes invertidos. Antes de montar as seis raias, confira num módulo só:
se o LED acende com o carro, está certo. Sem multímetro: com o firmware
rodando e a prova armada, segurar um carrinho sobre o sensor da raia 1 por
2 s tem que disparar a corrida demo.

O pino **A0** do módulo (a tensão analógica do fototransistor) fica solto.

### Se algum carro teimar em não disparar: a barreira

Se, depois de aproximar e ajustar, algum carro continuar falhando, aquele
ponto pode virar uma **barreira**: LED IR de um lado da raia, fototransistor
do outro. A borda passa a ser geométrica (o para-choque cortou o feixe) e não
depende do carro. **O firmware não muda** — só a polaridade: na barreira o
pino fica em 0 com o feixe passando e vai a 1 com o carro, então
`SENSOR_NIVEL_CARRO` volta para 1.

```
V+ ──[220 Ω em 3,3 V / 330 Ω em 5 V]── LED IR ── GND   (um lado da raia)

V+ ──[10 kΩ]──┬──────────── pino do sensor           (outro lado)
              │
         fototransistor (coletor em cima, emissor no GND)
```

### Como conferir na bancada, antes de fazer as seis

1. Solte **o mesmo carro** cinco vezes na **mesma raia** e olhe a dispersão
   dos tempos no log serial. É o ruído de base da raia.
2. Solte **o mesmo carro** uma vez em cada raia. As diferenças aqui são
   atrito da raia **mais** viés do sensor, misturados.
3. Para separar os dois: **troque os sensores de raia** e repita. O que
   andar junto com o sensor é viés de sensor; o que ficar na raia é atrito.

Se o viés de sensor passar de uns poucos milissegundos, a colocação de uma
chegada apertada não é confiável — e é aí que o infravermelho paga.

## Sobre o display: dois-pontos ou ponto decimal?

Existem dois tipos de módulo TM1637 de 4 dígitos vendidos com a mesma
descrição:

- o **azul**, de relógio — só um par de dois-pontos no meio;
- o **preto de 0,56"**, com **dois headers**, um de cada lado, os dois com
  CLK, DIO, GND e 5V (o que facilita encadear um display no outro). O vidro
  dele tem um ponto embaixo de cada dígito, além do dois-pontos.

Só que ter o pontinho no vidro não garante que ele esteja ligado ao TM1637:
em vários lotes do preto só o dois-pontos está. Não dá para saber olhando,
por isso o teste de fiação do boot acende **tudo** — todos os segmentos e
todos os pontos. Ligue uma vez e veja:

| O que acendeu no primeiro quadro | `DISPLAY_PONTO_DECIMAL` | O tempo sai |
| --- | --- | --- |
| um ponto embaixo de cada dígito | `1` | `3.721`, como no vídeo |
| só os dois pontinhos do meio | `0` (padrão) | `3721`, lê-se 3,721 s |

No simulador sempre parece o segundo caso, porque a peça do Wokwi é a de
relógio. Acender o dois-pontos num tempo abaixo de 10 s leria `37:21`, que é
pior do que não ter separador.

Acima de 10 s o separador acende nos dois casos, de propósito: sem ele,
`1234` tanto seria 1,234 s quanto 12,34 s.

## Se um display não acender

O firmware confere o **ACK** de cada TM1637 e avisa no log serial qual raia
não respondeu. Como o CLK é comum, o padrão da falha diz onde está o defeito:

| Sintoma | Onde olhar |
| --- | --- |
| **Um** display apagado, os outros bem | o DIO daquele display, ou a alimentação dele |
| **Todos** apagados | o CLK (GP9), ou a massa comum |
| Todos mostram lixo / piscam junto | massa comum ruim, ou alimentação com queda |
| Um mostra o número de outra raia no teste inicial | dois DIO trocados |
