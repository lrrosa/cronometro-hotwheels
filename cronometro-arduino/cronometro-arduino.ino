/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
/*
 * Cronometro de 6 pistas para pista de carrinhos Hot Wheels.
 * Versao Arduino UNO / Nano (ATmega328P, 16 MHz).
 *
 * Um microswitch na porta de largada marca o t0; um modulo infravermelho
 * TCRT5000 no fim de cada pista marca a chegada; seis displays TM1637
 * mostram a colocacao e depois o tempo.
 *
 * Gemeo da versao RP2040 (pasta cronometro-rasp-pico), com o mesmo
 * comportamento. As diferencas de plataforma estao em docs/diferencas-rp2040.md.
 *
 * Arquivo unico de proposito: assim cabe num unico "colar" no wokwi.com,
 * que compila na nuvem e nao precisa de nada instalado.
 */
#include <avr/interrupt.h>

/* =================================================================== */
/* CONFIGURACAO -- e aqui que se mexe                                   */
/* =================================================================== */

const uint8_t N_PISTAS = 6;

/*
 * PINOS
 *
 * Os sensores NAO tem tabela: o D0 deles precisa estar em A0..A5, nesta
 * ordem, porque sao a PORTC inteira e assim os seis cabem numa unica
 * interrupcao de mudanca de pino (PCINT1). O ATmega328P so tem DUAS
 * interrupcoes externas de verdade (D2 e D3) -- nao dariam para seis pistas.
 * A pista 1 e A0, a pista 6 e A5. O pino A0 do modulo (analogico) fica solto.
 */
const uint8_t PIN_LARGADA = 2;   /* microswitch da porta -- tem que ser D2
                                    (INT0) ou D3 (INT1)                  */
const uint8_t PIN_TM_CLK  = 3;   /* CLK comum aos seis displays          */
const uint8_t PIN_TM_DIO[N_PISTAS] = { 4, 5, 6, 7, 8, 9 };
const uint8_t PIN_BUZZER  = 10;  /* buzzer passivo (opcional)            */
const uint8_t PIN_BOTAO   = 11;  /* botao TESTE / REARMA (opcional)      */

#define USAR_BUZZER 1            /* 0 desliga o som e libera o D10       */
#define USAR_BOTAO  1            /* 0 desliga o botao e libera o D11     */

/*
 * POLARIDADES
 *
 * Nivel do D0 do modulo quando o carrinho esta SOBRE o sensor.
 *
 * No TCRT5000 o LM393 tem saida em coletor aberto e o modulo ja traz o
 * pull-up: sem carro nada reflete e o D0 fica em 1; com o carro em cima o
 * fototransistor conduz, o comparador vira e o D0 cai para 0. Ou seja:
 * carro = borda de DESCIDA, e o LED de saida do modulo acende.
 *
 * CONFIRA NO SEU MODULO antes de montar as seis pistas -- ha lote que sai
 * invertido. Ligue um so, ponha um carrinho em cima e veja o LED: se ele
 * acender com o carro, este valor esta certo. Sem multimetro: com a prova
 * armada, segurar um carrinho sobre o sensor da pista 1 por 2 s tem que
 * disparar a corrida demo (ver GESTO_DEMO_MS).
 */
#ifndef SENSOR_NIVEL_CARRO      /* o release compila variantes com -D */
#define SENSOR_NIVEL_CARRO 0
#endif

/*
 * Nivel do pino de largada com a porta ABERTA.
 * Microswitch entre o pino e o GND, com pull-up interno: porta fechada =
 * contato fechado = 0; porta abre = 1.
 */
#define LARGADA_NIVEL_ABERTA 1

/* TEMPOS (ms) */
const uint16_t TEMPO_MIN_MS       = 150;   /* chegada antes disso = ruido  */
const uint16_t TEMPO_LIMITE_MS    = 15000; /* fim da prova por tempo       */
const uint16_t ESPERA_APOS_1o_MS  = 8000;  /* fim apos o primeiro colocado */

const uint16_t MOSTRA_POSICAO_MS  = 4500;
const uint16_t MOSTRA_TEMPO_MS    = 7000;
const uint16_t RESULTADO_MIN_MS   = 23000; /* rearme automatico, so com a
                                              porta ja fechada            */
const uint16_t PISCA_MS           = 400;

/*
 * Periodo do cronometro correndo na tela. NAO use numero redondo: com 50 ms
 * o ultimo digito do milissegundo fica parado em 0 e o penultimo so alterna
 * 0/5, o que parece display quebrado. Com 43 os dez algarismos aparecem.
 */
const uint8_t  REFRESH_CORRIDA_MS = 43;

const uint16_t DEBOUNCE_BOTAO_MS  = 20;    /* so do botao de teste: a
                                              largada nao precisa, ver ISR */
const uint16_t BOTAO_LONGO_MS     = 1000;  /* pressao longa = corrida demo */
const uint16_t GESTO_DEMO_MS      = 2000;  /* carrinho sobre o sensor 1    */

/* DISPLAYS */
const uint8_t TM1637_BRILHO = 4;  /* 0..7 -- mexe direto no consumo       */
const uint8_t TM1637_BIT_US = 5;  /* meio periodo do clock bit-bang       */

/*
 *   0 = so o dois-pontos central e ligado: o tempo sai "3721" e se le
 *       3,721 s. E o que o TM1637 do Wokwi modela.
 *   1 = cada digito tem o proprio ponto ligado -> "3.721", como no video.
 *
 * O vidro do modulo preto de 0,56" TEM os pontinhos, mas em varios lotes
 * eles nao estao ligados no TM1637 -- so o dois-pontos esta. Nao da para
 * saber olhando: o teste de fiacao do boot acende TODOS os segmentos e
 * TODOS os pontos (0xFF em cada digito) justamente para isso. Ligue uma vez
 * e veja o que acendeu:
 *   um ponto embaixo de cada digito  -> ponha 1
 *   so os dois pontinhos do meio     -> deixe 0
 * No simulador sempre parece o caso 0, porque a peca do Wokwi e a de relogio.
 *
 * Acima de 10 s o separador acende nos dois casos -- ver dispTempo().
 */
#ifndef DISPLAY_PONTO_DECIMAL   /* o release compila variantes com -D */
#define DISPLAY_PONTO_DECIMAL 0
#endif

/* CORRIDA DEMO */
const uint16_t DEMO_MS_MIN = 2400;
const uint16_t DEMO_MS_MAX = 4600;

const uint16_t SOM_LARGADA_HZ = 330,  SOM_LARGADA_MS = 600;
const uint16_t SOM_CHEGADA_HZ = 1400, SOM_CHEGADA_MS = 70;
const uint16_t SOM_FIM_HZ     = 220,  SOM_FIM_MS     = 450;
const uint16_t SOM_BOOT_HZ    = 880,  SOM_BOOT_MS    = 80;

const uint32_t TEMPO_INVALIDO = 0xFFFFFFFFUL;

/* =================================================================== */
/* TM1637 -- protocolo de dois fios                                     */
/* =================================================================== */
/*
 * O TM1637 nao tem endereco: quem seleciona o chip e a linha DIO, porque a
 * transacao so comeca numa condicao de START (DIO descendo com CLK alto).
 * Por isso os seis displays dividem o mesmo CLK -- enquanto se escreve numa
 * pista, os outros cinco veem o clock com o DIO deles parado em nivel alto
 * e ignoram tudo. Sao 7 pinos em vez de 12.
 *
 * CLK e push-pull (so o mestre o dirige). DIO e dreno aberto emulado: para
 * soltar a linha o pino vira entrada com pull-up; para puxar para baixo,
 * primeiro se desliga o pull-up (digitalWrite LOW com o pino ainda entrada)
 * e so entao ele vira saida. Essa ordem importa: fazer pinMode(OUTPUT) com
 * o bit de PORT ainda em 1 faria o pino dirigir 5 V na linha.
 */
#define TM_DLY() delayMicroseconds(TM1637_BIT_US)

static inline void dioSolta(uint8_t p) { pinMode(p, INPUT_PULLUP); }
static inline void dioBaixo(uint8_t p) { digitalWrite(p, LOW); pinMode(p, OUTPUT); }
static inline void clkAlto(void)       { digitalWrite(PIN_TM_CLK, HIGH); }
static inline void clkBaixo(void)      { digitalWrite(PIN_TM_CLK, LOW); }

static void tmInicio(uint8_t dio)   /* START: DIO desce com CLK alto */
{
    clkAlto(); dioSolta(dio); TM_DLY();
    dioBaixo(dio);            TM_DLY();
    clkBaixo();               TM_DLY();
}

static void tmFim(uint8_t dio)      /* STOP: DIO sobe com CLK alto */
{
    clkBaixo(); dioBaixo(dio); TM_DLY();
    clkAlto();                 TM_DLY();
    dioSolta(dio);             TM_DLY();
}

static bool tmByte(uint8_t dio, uint8_t b)
{
    for (uint8_t i = 0; i < 8; i++) {        /* LSB primeiro */
        clkBaixo();
        if (b & 1) dioSolta(dio); else dioBaixo(dio);
        b >>= 1;
        TM_DLY();
        clkAlto();
        TM_DLY();
    }
    clkBaixo();                              /* ACK no nono clock */
    dioSolta(dio);
    TM_DLY();
    clkAlto();
    TM_DLY();
    const bool ack = (digitalRead(dio) == LOW);
    clkBaixo();
    TM_DLY();
    return ack;
}

static bool tmBrilho(uint8_t dio, uint8_t brilho, bool ligado)
{
    tmInicio(dio);
    const bool ack = tmByte(dio, 0x80 | (ligado ? 0x08 : 0x00) | (brilho & 0x07));
    tmFim(dio);
    return ack;
}

static bool tmSegmentos(uint8_t dio, const uint8_t seg[4])
{
    tmInicio(dio);
    bool ack = tmByte(dio, 0x40);            /* escrita com auto-incremento */
    tmFim(dio);

    tmInicio(dio);
    ack &= tmByte(dio, 0xC0);                /* comeca no digito 0 */
    for (uint8_t i = 0; i < 4; i++) ack &= tmByte(dio, seg[i]);
    tmFim(dio);

    return ack;
}

/* =================================================================== */
/* Display: fonte de 7 segmentos e formatacao                           */
/* =================================================================== */
#define PONTO 0x80

static bool ackOk[N_PISTAS];

/* bit0=a (topo) ... bit6=g (meio), bit7=ponto/dois-pontos */
static uint8_t segChar(char c)
{
    switch (c) {
    case '0': return 0x3F;  case '1': return 0x06;  case '2': return 0x5B;
    case '3': return 0x4F;  case '4': return 0x66;  case '5': return 0x6D;
    case '6': return 0x7D;  case '7': return 0x07;  case '8': return 0x7F;
    case '9': return 0x6F;
    case ' ': return 0x00;  case '-': return 0x40;  case '_': return 0x08;
    case 'A': return 0x77;  case 'b': return 0x7C;  case 'C': return 0x39;
    case 'd': return 0x5E;  case 'E': return 0x79;  case 'F': return 0x71;
    case 'H': return 0x76;  case 'h': return 0x74;  case 'I': return 0x06;
    case 'L': return 0x38;  case 'n': return 0x54;  case 'o': return 0x5C;
    case 'P': return 0x73;  case 'r': return 0x50;  case 'S': return 0x6D;
    case 't': return 0x78;  case 'U': return 0x3E;  case 'u': return 0x1C;
    default:  return 0x00;
    }
}

static void dispEnvia(uint8_t pista, const uint8_t seg[4])
{
    if (pista >= N_PISTAS) return;
    ackOk[pista] = tmSegmentos(PIN_TM_DIO[pista], seg);
}

static void dispTexto(uint8_t pista, const char *s4)
{
    uint8_t seg[4] = { 0, 0, 0, 0 };
    for (uint8_t i = 0; i < 4 && s4[i] != '\0'; i++) seg[i] = segChar(s4[i]);
    dispEnvia(pista, seg);
}

/* Acende tudo que o modulo tem: 7 segmentos mais ponto/dois-pontos. E o
   teste de fiacao do boot, e tambem o que revela se o modulo liga um ponto
   por digito ou so o dois-pontos central. */
static void dispTudoAceso(uint8_t pista)
{
    const uint8_t seg[4] = { 0xFF, 0xFF, 0xFF, 0xFF };
    dispEnvia(pista, seg);
}

static void dispTextoTodos(const char *s4)
{
    for (uint8_t p = 0; p < N_PISTAS; p++) dispTexto(p, s4);
}

static void dispTempo(uint8_t pista, uint32_t ms)
{
    uint8_t seg[4];

    if (ms == TEMPO_INVALIDO || ms >= 100000UL) {
        dispTexto(pista, "----");
        return;
    }

    if (ms < 10000UL) {                      /* S.mmm */
        seg[0] = segChar('0' + (uint8_t)(ms / 1000UL));
        seg[1] = segChar('0' + (uint8_t)((ms / 100UL) % 10UL));
        seg[2] = segChar('0' + (uint8_t)((ms / 10UL)  % 10UL));
        seg[3] = segChar('0' + (uint8_t)(ms % 10UL));
#if DISPLAY_PONTO_DECIMAL
        seg[0] |= PONTO;
#endif
    } else {                                 /* SS.mm */
        seg[0] = segChar('0' + (uint8_t)(ms / 10000UL));
        seg[1] = segChar('0' + (uint8_t)((ms / 1000UL) % 10UL));
        seg[2] = segChar('0' + (uint8_t)((ms / 100UL)  % 10UL));
        seg[3] = segChar('0' + (uint8_t)((ms / 10UL)   % 10UL));
        /*
         * Aqui o separador acende nos DOIS tipos de modulo, de proposito.
         * Sem separador nenhum, "1234" seria 1,234 s ou 12,34 s -- nao da
         * para saber. Aceso, o modulo de ponto mostra 12.34 e o de relogio
         * mostra 12:34; os dois se leem igual, e o separador apagado passa
         * a significar "este tempo esta no formato S.mmm".
         */
#if DISPLAY_PONTO_DECIMAL
        seg[1] |= PONTO;
#else
        /* No modulo de relogio o dois-pontos e um so, e qual digito carrega
           o bit que o acende muda de implementacao para implementacao.
           Marcar os dois primeiros acende do mesmo jeito. */
        seg[0] |= PONTO;
        seg[1] |= PONTO;
#endif
    }
    dispEnvia(pista, seg);
}

static void dispPosicao(uint8_t pista, uint8_t pos)
{
    char s[5] = "    ";
    if (pos >= 1 && pos <= 9) s[3] = (char)('0' + pos);
    dispTexto(pista, s);
}

static void dispInit(void)
{
    pinMode(PIN_TM_CLK, OUTPUT);
    digitalWrite(PIN_TM_CLK, HIGH);
    for (uint8_t p = 0; p < N_PISTAS; p++) dioSolta(PIN_TM_DIO[p]);

    /* So depois que os seis DIO existem como pino e que da para falar com
       qualquer um: o CLK e comum, e um DIO ainda flutuando poderia ser lido
       como um START pelo modulo vizinho. */
    for (uint8_t p = 0; p < N_PISTAS; p++) {
        ackOk[p] = tmBrilho(PIN_TM_DIO[p], TM1637_BRILHO, true);
        dispTexto(p, "    ");
    }
}

/* =================================================================== */
/* Som -- nao bloqueante                                                */
/* =================================================================== */
#if USAR_BUZZER
static unsigned long somFimMs;
static bool          somTocando;

static void somBip(uint16_t hz, uint16_t ms)
{
    if (hz == 0 || ms == 0) return;
    tone(PIN_BUZZER, hz);
    somFimMs   = millis() + ms;
    somTocando = true;
}

static void somTick(void)
{
    if (!somTocando) return;
    if ((long)(millis() - somFimMs) < 0) return;
    noTone(PIN_BUZZER);
    somTocando = false;
}
#else
static void somBip(uint16_t hz, uint16_t ms) { (void)hz; (void)ms; }
static void somTick(void) {}
#endif

/* =================================================================== */
/* Estado                                                               */
/* =================================================================== */
enum estado_t { EST_ARMADO, EST_CORRENDO, EST_RESULTADO };
enum fase_t   { FASE_POSICAO, FASE_TEMPO };

struct pista_t {
    bool     chegou;
    uint32_t ms;        /* tempo desde a largada */
    uint8_t  posicao;   /* 1..6; 0 = nao chegou  */
};

/* --- compartilhado com as interrupcoes --- */
static volatile unsigned long largadaUs;
static volatile bool          largadaFlag;   /* porta abriu  */
static volatile bool          fechouFlag;    /* porta fechou */
static volatile unsigned long sensorUs[N_PISTAS];
static volatile bool          sensorFlag[N_PISTAS];
static volatile uint8_t       pincAnt;       /* ultimo estado de A0..A5 */

/* --- so do laco principal --- */
static estado_t estado;
static fase_t   fase;
static pista_t  pista[N_PISTAS];
static uint8_t  nChegadas;

static unsigned long t0Us;           /* instante da largada, em micros    */
static unsigned long tPrimeiroUs;    /* 1o colocado (0 = ninguem ainda)   */
static unsigned long tResultadoMs;
static unsigned long tFaseMs;
static unsigned long tRefreshMs;
static unsigned long tPiscaMs;
static bool          pisca;
static int8_t        armadoVisual;   /* -1 forca reescrita dos displays   */

static bool     demo;
static uint16_t demoMs[N_PISTAS];
static bool     sementeFeita;

#if USAR_BOTAO
static bool          botaoAntes, botaoTratado;
static unsigned long botaoDesdeMs;
#endif
static bool          gestoArmado;
static unsigned long gestoDesdeMs;

/* =================================================================== */
/* Interrupcoes -- so carimbam a hora. Toda decisao fica no laco.        */
/* =================================================================== */
/*
 * As seis barreiras estao na PORTC e compartilham a PCINT1. A ISR le a
 * porta inteira de uma vez e descobre quem mudou pelo XOR com a leitura
 * anterior -- uma unica interrupcao cobre as seis pistas.
 */
ISR(PCINT1_vect)
{
    const unsigned long agora = micros();
    const uint8_t atual = PINC & 0x3F;
    const uint8_t mudou = atual ^ pincAnt;
    pincAnt = atual;

    for (uint8_t i = 0; i < N_PISTAS; i++) {
        if (!(mudou & _BV(i))) continue;
        const bool alto = (atual & _BV(i)) != 0;
        if (alto == (SENSOR_NIVEL_CARRO != 0) && !sensorFlag[i]) {
            sensorUs[i]   = agora;
            sensorFlag[i] = true;
        }
    }
}

static void isrLargada(void)
{
    const unsigned long agora  = micros();
    const bool          aberta = (digitalRead(PIN_LARGADA) != LOW)
                                 == (LARGADA_NIVEL_ABERTA != 0);
    if (aberta) {
        /* A PRIMEIRA borda e a boa: o repique do microswitch vem depois
           dela, nunca antes. Por isso nao existe janela de debounce aqui. */
        if (!largadaFlag) {
            largadaUs   = agora;
            largadaFlag = true;
        }
    } else {
        fechouFlag = true;
    }
}

static void limpaSensores(void)
{
    for (uint8_t i = 0; i < N_PISTAS; i++) sensorFlag[i] = false;
}

static inline bool portaAberta(void)
{
    return (digitalRead(PIN_LARGADA) != LOW) == (LARGADA_NIVEL_ABERTA != 0);
}

static inline bool carroSobreSensor(uint8_t i)
{
    return ((PINC & _BV(i)) != 0) == (SENSOR_NIVEL_CARRO != 0);
}

/* =================================================================== */
/* Log serial                                                           */
/* =================================================================== */
static void serialTempo(uint32_t ms)
{
    Serial.print(ms / 1000UL);
    Serial.print('.');
    const uint16_t f = (uint16_t)(ms % 1000UL);
    if (f < 100) Serial.print('0');
    if (f < 10)  Serial.print('0');
    Serial.print(f);
    Serial.print(F(" s"));
}

/* =================================================================== */
/* Transicoes                                                           */
/* =================================================================== */
static void rearma(void)
{
    estado       = EST_ARMADO;
    armadoVisual = -1;
    pisca        = true;
    tPiscaMs     = millis();
    largadaFlag  = false;
    fechouFlag   = false;
    limpaSensores();
    Serial.println(F("[armado] esperando a porta abrir"));
}

static void iniciaCorrida(unsigned long t0, bool ehDemo)
{
    t0Us        = t0;
    tPrimeiroUs = 0;
    tRefreshMs  = 0;
    nChegadas   = 0;
    demo        = ehDemo;

    for (uint8_t i = 0; i < N_PISTAS; i++) {
        pista[i].chegou  = false;
        pista[i].ms      = TEMPO_INVALIDO;
        pista[i].posicao = 0;
    }
    limpaSensores();
    largadaFlag = false;
    fechouFlag  = false;

    estado = EST_CORRENDO;
    somBip(SOM_LARGADA_HZ, SOM_LARGADA_MS);
    if (ehDemo) Serial.println(F("[largada] corrida demo"));
    else        Serial.println(F("[largada]"));
}

static void registraChegada(uint8_t i, unsigned long t)
{
    if (pista[i].chegou) return;

    const unsigned long dt = t - t0Us;        /* subtracao sem sinal:
                                                 sobrevive ao estouro de
                                                 micros() aos 71 minutos   */
    if (dt > 3600000000UL) return;            /* chegou "antes" da largada */

    const uint32_t ms = (uint32_t)(dt / 1000UL);
    if (ms < TEMPO_MIN_MS) {
        /* Nenhum carrinho faz a pista nesse tempo: e repique do microswitch
           ou sujeira passando na barreira. */
        Serial.print(F("[ruido] pista "));
        Serial.print(i + 1);
        Serial.print(F(" disparou em "));
        Serial.print(ms);
        Serial.println(F(" ms, ignorado"));
        return;
    }

    pista[i].chegou  = true;
    pista[i].ms      = ms;
    pista[i].posicao = ++nChegadas;
    if (tPrimeiroUs == 0) tPrimeiroUs = t;

    dispPosicao(i, pista[i].posicao);
    somBip((uint16_t)(SOM_CHEGADA_HZ - 150 * pista[i].posicao), SOM_CHEGADA_MS);

    Serial.print(F("  "));
    Serial.print(pista[i].posicao);
    Serial.print(F("o lugar  pista "));
    Serial.print(i + 1);
    Serial.print(F("  "));
    serialTempo(ms);
    Serial.println();
}

static void mostraResultado(void)
{
    for (uint8_t i = 0; i < N_PISTAS; i++) {
        if (fase == FASE_POSICAO) {
            if (pista[i].chegou) dispPosicao(i, pista[i].posicao);
            else                 dispTexto(i, " dnF");
        } else {
            dispTempo(i, pista[i].chegou ? pista[i].ms : TEMPO_INVALIDO);
        }
    }
}

static void finaliza(void)
{
    estado       = EST_RESULTADO;
    fase         = FASE_POSICAO;
    tResultadoMs = millis();
    tFaseMs      = tResultadoMs;
    fechouFlag   = false;
    mostraResultado();
    somBip(SOM_FIM_HZ, SOM_FIM_MS);

    Serial.print(F("[fim] "));
    Serial.print(nChegadas);
    Serial.print(F(" de "));
    Serial.print(N_PISTAS);
    Serial.println(F(" chegaram"));

    for (uint8_t pos = 1; pos <= nChegadas; pos++)
        for (uint8_t i = 0; i < N_PISTAS; i++)
            if (pista[i].posicao == pos) {
                Serial.print(F("  "));
                Serial.print(pos);
                Serial.print(F("o  pista "));
                Serial.print(i + 1);
                Serial.print(F("  "));
                serialTempo(pista[i].ms);
                Serial.println();
            }
    for (uint8_t i = 0; i < N_PISTAS; i++)
        if (!pista[i].chegou) {
            Serial.print(F("  --  pista "));
            Serial.print(i + 1);
            Serial.println(F("  nao chegou"));
        }
}

static void iniciaDemo(void)
{
    if (!sementeFeita) {
        /* micros() no instante em que a pessoa apertou o botao: e a melhor
           fonte de aleatoriedade que este chip tem, ja que todos os pinos
           analogicos estao ocupados pelas barreiras. */
        randomSeed(micros());
        sementeFeita = true;
    }
    for (uint8_t i = 0; i < N_PISTAS; i++) {
        demoMs[i] = (uint16_t)random(DEMO_MS_MIN, DEMO_MS_MAX);
        /* Empate em ms deixaria a ordem de chegada dependendo da ordem do
           laco, o que esconderia um erro de ordenacao em vez de testa-lo. */
        for (uint8_t j = 0; j < i; j++)
            if (demoMs[i] == demoMs[j]) demoMs[i] += 1 + i;
    }
    iniciaCorrida(micros(), true);
}

/* =================================================================== */
/* Estados                                                              */
/* =================================================================== */
static void tickArmado(void)
{
    if (largadaFlag) {
        /* Le o carimbo ANTES de limpar a bandeira: enquanto ela esta em
           pe, a ISR nao escreve por cima. */
        const unsigned long t = largadaUs;
        largadaFlag = false;
        iniciaCorrida(t, false);
        return;
    }
    limpaSensores();          /* disparo fora de prova e so ruido */
    fechouFlag = false;

    /* Segurar um carrinho sobre o sensor da pista 1 por alguns segundos
       dispara a demo: testa o painel inteiro sem botao nenhum, e de quebra
       prova que a polaridade do sensor esta certa. */
    const unsigned long agora = millis();
    if (!carroSobreSensor(0)) {
        gestoDesdeMs = 0;
        gestoArmado  = true;
    } else if (gestoArmado) {
        if (gestoDesdeMs == 0) {
            gestoDesdeMs = agora;
        } else if (agora - gestoDesdeMs >= GESTO_DEMO_MS) {
            gestoArmado  = false;   /* sensor preso nao repete a demo */
            gestoDesdeMs = 0;
            iniciaDemo();
            return;
        }
    }

    if (agora - tPiscaMs >= PISCA_MS) {
        tPiscaMs = agora;
        pisca = !pisca;
    }
    /* Porta aberta com a prova armada = ninguem vai largar: os tracos
       piscando pedem para fechar a porta. */
    const int8_t visual = (portaAberta() && !pisca) ? 0 : 1;
    if (visual != armadoVisual) {
        armadoVisual = visual;
        dispTextoTodos(visual ? "----" : "    ");
    }
}

static void tickCorrendo(void)
{
    /* 1. Recolhe o que as barreiras marcaram e ordena por tempo ANTES de
          numerar: duas pistas podem disparar na mesma volta do laco, e a
          ordem do laco nao e a ordem de chegada. */
    uint8_t       idx[N_PISTAS];
    unsigned long ts[N_PISTAS];
    uint8_t       n = 0;

    for (uint8_t i = 0; i < N_PISTAS; i++) {
        if (!sensorFlag[i]) continue;
        const unsigned long t = sensorUs[i];   /* le antes de limpar */
        sensorFlag[i] = false;
        if (pista[i].chegou) continue;
        idx[n] = i; ts[n] = t; n++;
    }
    for (uint8_t a = 1; a < n; a++) {
        const unsigned long t = ts[a];
        const uint8_t       k = idx[a];
        int8_t b = (int8_t)a - 1;
        while (b >= 0 && (long)(ts[b] - t) > 0) {
            ts[b + 1] = ts[b]; idx[b + 1] = idx[b]; b--;
        }
        ts[b + 1] = t; idx[b + 1] = k;
    }
    for (uint8_t a = 0; a < n; a++) registraChegada(idx[a], ts[a]);

    const unsigned long agoraUs = micros();
    const uint32_t      el      = (uint32_t)((agoraUs - t0Us) / 1000UL);

    /* 2. Corrida demo: as chegadas entram pelo mesmo caminho das reais. */
    if (demo) {
        for (uint8_t i = 0; i < N_PISTAS; i++)
            if (!pista[i].chegou && el >= demoMs[i])
                registraChegada(i, t0Us + (unsigned long)demoMs[i] * 1000UL);
    }

    /* 3. Quem ainda nao chegou mostra o cronometro correndo. */
    const unsigned long agoraMs = millis();
    if (agoraMs - tRefreshMs >= REFRESH_CORRIDA_MS) {
        tRefreshMs = agoraMs;
        for (uint8_t i = 0; i < N_PISTAS; i++)
            if (!pista[i].chegou) dispTempo(i, el);
    }

    /* 4. Fim: todos chegaram, ou estourou o tempo limite, ou acabou a
          espera pelos retardatarios -- o que vier antes. */
    const bool fim = (nChegadas == N_PISTAS)
                  || (el >= TEMPO_LIMITE_MS)
                  || (tPrimeiroUs != 0 &&
                      (agoraUs - tPrimeiroUs) / 1000UL >= ESPERA_APOS_1o_MS);
    if (fim) finaliza();
}

static void tickResultado(void)
{
    const unsigned long agora = millis();
    limpaSensores();

    const uint16_t limite = (fase == FASE_POSICAO) ? MOSTRA_POSICAO_MS
                                                   : MOSTRA_TEMPO_MS;
    if (agora - tFaseMs >= limite) {
        fase    = (fase == FASE_POSICAO) ? FASE_TEMPO : FASE_POSICAO;
        tFaseMs = agora;
        mostraResultado();
    }

    if (fechouFlag) {          /* a porta voltou: proxima prova */
        fechouFlag = false;
        rearma();
        return;
    }
    /* Se a porta ja estava fechada (caiu durante a prova, por exemplo),
       rearma sozinho depois de dois ciclos inteiros de resultado. */
    if (!portaAberta() && agora - tResultadoMs >= RESULTADO_MIN_MS) rearma();
}

/* Botao TESTE: toque curto rearma, pressao longa roda a corrida demo. */
static void trataBotao(void)
{
#if USAR_BOTAO
    const bool          apertado = (digitalRead(PIN_BOTAO) == LOW);
    const unsigned long agora    = millis();

    if (apertado && !botaoAntes) {
        botaoDesdeMs = agora;
        botaoTratado = false;
    }
    if (apertado && !botaoTratado && agora - botaoDesdeMs >= BOTAO_LONGO_MS) {
        botaoTratado = true;
        iniciaDemo();
    }
    if (!apertado && botaoAntes && !botaoTratado &&
        agora - botaoDesdeMs >= DEBOUNCE_BOTAO_MS) {
        rearma();
    }
    botaoAntes = apertado;
#endif
}

/* =================================================================== */
/* setup / loop                                                         */
/* =================================================================== */
void setup(void)
{
    Serial.begin(115200);
    Serial.println(F("\n=== cronometro-hotwheels (Arduino) ==="));

    /* D0 dos TCRT5000 em A0..A5. O LM393 deles tem saida em coletor aberto e
       o modulo ja traz o proprio pull-up; o interno fica em paralelo e cobre
       o caso de um fio solto, que assim le 1 = sem carro em vez de flutuar. */
    for (uint8_t i = 0; i < N_PISTAS; i++) pinMode(A0 + i, INPUT_PULLUP);
    pinMode(PIN_LARGADA, INPUT_PULLUP);
#if USAR_BOTAO
    pinMode(PIN_BOTAO, INPUT_PULLUP);
#endif

    dispInit();

    /* Teste de fiacao: TUDO aceso (segmentos + pontos), depois o numero da
       pista. Se um display ficar apagado ou mostrar o numero de outra pista,
       o erro esta no DIO dele -- nao no firmware. O primeiro quadro tambem
       mostra quais separadores o modulo tem de verdade: ver
       DISPLAY_PONTO_DECIMAL. */
    for (uint8_t i = 0; i < N_PISTAS; i++) dispTudoAceso(i);
    somBip(SOM_BOOT_HZ, SOM_BOOT_MS);
    delay(700);
    somTick();
    for (uint8_t i = 0; i < N_PISTAS; i++) dispPosicao(i, i + 1);
    delay(900);

    for (uint8_t i = 0; i < N_PISTAS; i++)
        if (!ackOk[i]) {
            Serial.print(F("[aviso] display da pista "));
            Serial.print(i + 1);
            Serial.println(F(" nao deu ACK"));
        }

    /* Interrupcoes: PCINT1 cobre as seis barreiras de uma vez; a largada
       tem INT0 so para ela. */
    pincAnt  = PINC & 0x3F;
    PCIFR    = _BV(PCIF1);      /* descarta pendencia antes de habilitar.
                                   Atribuicao, nao |= : escrever 1 num bit
                                   de PCIFR e o que o limpa, entao um |=
                                   limparia tambem os flags das outras
                                   portas. */
    PCMSK1  |= 0x3F;            /* PCINT8..PCINT13 = A0..A5 */
    PCICR   |= _BV(PCIE1);
    attachInterrupt(digitalPinToInterrupt(PIN_LARGADA), isrLargada, CHANGE);

    rearma();
}

void loop(void)
{
    trataBotao();
    switch (estado) {
    case EST_ARMADO:    tickArmado();    break;
    case EST_CORRENDO:  tickCorrendo();  break;
    case EST_RESULTADO: tickResultado(); break;
    }
    somTick();
    /*
     * A precisao do cronometro nao depende deste intervalo: quem carimba a
     * hora e a interrupcao, com micros(). O laco so decide e desenha.
     */
    delay(1);
}
