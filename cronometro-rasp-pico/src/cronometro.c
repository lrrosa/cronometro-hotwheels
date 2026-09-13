/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
#include "cronometro.h"
#include "config.h"
#include "display.h"
#include "som.h"

#include "pico/stdlib.h"
#include "pico/rand.h"
#include "hardware/gpio.h"

#include <stdio.h>

typedef enum { EST_ARMADO, EST_CORRENDO, EST_RESULTADO } estado_t;
typedef enum { FASE_POSICAO, FASE_TEMPO }                fase_t;

typedef struct {
    bool     chegou;
    uint32_t ms;        /* tempo desde a largada */
    int      posicao;   /* 1..6; 0 = nao chegou */
} pista_t;

/* ------------------------------------------------------------------ */
/* Compartilhado com a interrupcao                                     */
/* ------------------------------------------------------------------ */
static volatile uint64_t largada_us;
static volatile bool     largada_flag;   /* porta abriu  */
static volatile bool     fechou_flag;    /* porta fechou */
static volatile uint64_t sensor_us[N_PISTAS];
static volatile bool     sensor_flag[N_PISTAS];

/* ------------------------------------------------------------------ */
/* Estado do loop principal                                            */
/* ------------------------------------------------------------------ */
static estado_t estado;
static fase_t   fase;
static pista_t  pista[N_PISTAS];
static int      n_chegadas;

static uint64_t t0_us;            /* instante da largada                   */
static uint64_t t_primeiro_us;    /* instante do 1o colocado (0 = ninguem) */
static uint64_t t_resultado_us;   /* entrada em EST_RESULTADO              */
static uint64_t t_fase_us;        /* troca posicao <-> tempo               */
static uint64_t t_refresh_us;     /* ultimo refresh do cronometro          */
static uint64_t t_pisca_us;
static bool     pisca;
static int      armado_visual;    /* -1 forca reescrita dos displays       */

static bool     demo;
static uint32_t demo_ms[N_PISTAS];

#if USAR_BOTAO
static bool     botao_antes, botao_tratado;
static uint64_t botao_desde_us;
#endif
static bool     gesto_armado;
static uint64_t gesto_desde_us;

/* ------------------------------------------------------------------ */
/* Leitura de nivel ja com a polaridade da configuracao                */
/* ------------------------------------------------------------------ */
static inline bool porta_aberta(void)
{
    return (gpio_get(PIN_LARGADA) != 0) == (LARGADA_NIVEL_ABERTA != 0);
}

static inline bool sensor_ve_carro(int i)
{
    return (gpio_get(PIN_SENSOR[i]) != 0) == (SENSOR_NIVEL_CARRO != 0);
}

/* ------------------------------------------------------------------ */
/* Interrupcao: so carimba a hora. Toda decisao fica no loop.          */
/* ------------------------------------------------------------------ */
static void gpio_isr(uint gpio, uint32_t ev)
{
    const uint64_t agora  = time_us_64();
    const bool     subida = (ev & GPIO_IRQ_EDGE_RISE) != 0;

    if (gpio == PIN_LARGADA) {
        if (subida == (LARGADA_NIVEL_ABERTA != 0)) {
            /* A PRIMEIRA borda e a boa: o repique do microswitch vem
               depois dela, nunca antes. */
            if (!largada_flag) {
                largada_us   = agora;
                largada_flag = true;
            }
        } else {
            fechou_flag = true;
        }
        return;
    }

    for (int i = 0; i < N_PISTAS; i++) {
        if (gpio == PIN_SENSOR[i]) {
            if (subida == (SENSOR_NIVEL_CARRO != 0) && !sensor_flag[i]) {
                sensor_us[i]   = agora;
                sensor_flag[i] = true;
            }
            return;
        }
    }
}

static void limpa_sensores(void)
{
    for (int i = 0; i < N_PISTAS; i++) sensor_flag[i] = false;
}

/* ------------------------------------------------------------------ */
/* Transicoes                                                          */
/* ------------------------------------------------------------------ */
static void rearma(void)
{
    estado        = EST_ARMADO;
    armado_visual = -1;
    pisca         = true;
    t_pisca_us    = time_us_64();
    largada_flag  = false;
    fechou_flag   = false;
    limpa_sensores();
    printf("[armado] esperando a porta abrir\n");
}

static void inicia_corrida(uint64_t t0, bool eh_demo)
{
    t0_us         = t0;
    t_primeiro_us = 0;
    t_refresh_us  = 0;
    n_chegadas    = 0;
    demo          = eh_demo;

    for (int i = 0; i < N_PISTAS; i++) {
        pista[i].chegou  = false;
        pista[i].ms      = TEMPO_INVALIDO;
        pista[i].posicao = 0;
    }
    limpa_sensores();
    largada_flag = false;
    fechou_flag  = false;

    estado = EST_CORRENDO;
    som_bip(SOM_LARGADA_HZ, SOM_LARGADA_MS);
    printf("[largada]%s\n", eh_demo ? " corrida demo" : "");
}

static void registra_chegada(int i, uint64_t t)
{
    if (pista[i].chegou || t < t0_us) return;

    uint32_t ms = (uint32_t)((t - t0_us) / 1000u);
    if (ms < TEMPO_MIN_MS) {
        /* Nenhum carrinho faz a pista nesse tempo: e repique do
           microswitch ou sombra passando no sensor. */
        printf("[ruido] pista %d disparou em %u ms, ignorado\n", i + 1, ms);
        return;
    }

    pista[i].chegou  = true;
    pista[i].ms      = ms;
    pista[i].posicao = ++n_chegadas;
    if (t_primeiro_us == 0) t_primeiro_us = t;

    disp_posicao(i, pista[i].posicao);
    som_bip((uint16_t)(SOM_CHEGADA_HZ - 150 * pista[i].posicao),
            SOM_CHEGADA_MS);
    printf("  %do lugar  pista %d  %u.%03u s\n",
           pista[i].posicao, i + 1, ms / 1000u, ms % 1000u);
}

static void mostra_resultado(void)
{
    for (int i = 0; i < N_PISTAS; i++) {
        if (fase == FASE_POSICAO) {
            if (pista[i].chegou) disp_posicao(i, pista[i].posicao);
            else                 disp_dnf(i);
        } else {
            disp_tempo(i, pista[i].chegou ? pista[i].ms : TEMPO_INVALIDO);
        }
    }
}

static void finaliza(void)
{
    estado         = EST_RESULTADO;
    fase           = FASE_POSICAO;
    t_resultado_us = time_us_64();
    t_fase_us      = t_resultado_us;
    fechou_flag    = false;
    mostra_resultado();
    som_bip(SOM_FIM_HZ, SOM_FIM_MS);

    printf("[fim] %d de %d chegaram\n", n_chegadas, N_PISTAS);
    for (int pos = 1; pos <= n_chegadas; pos++)
        for (int i = 0; i < N_PISTAS; i++)
            if (pista[i].posicao == pos)
                printf("  %do  pista %d  %u.%03u s\n", pos, i + 1,
                       pista[i].ms / 1000u, pista[i].ms % 1000u);
    for (int i = 0; i < N_PISTAS; i++)
        if (!pista[i].chegou)
            printf("  --  pista %d  nao chegou\n", i + 1);
}

static void inicia_demo(void)
{
    for (int i = 0; i < N_PISTAS; i++) {
        demo_ms[i] = DEMO_MS_MIN + (get_rand_32() % (DEMO_MS_MAX - DEMO_MS_MIN));
        /* Empate em ms deixaria a ordem de chegada dependendo da ordem do
           laco, o que esconderia um erro de ordenacao em vez de testa-lo. */
        for (int j = 0; j < i; j++)
            if (demo_ms[i] == demo_ms[j]) demo_ms[i] += 1u + (uint32_t)i;
    }
    inicia_corrida(time_us_64(), true);
}

/* ------------------------------------------------------------------ */
/* Estados                                                             */
/* ------------------------------------------------------------------ */
static void tick_armado(void)
{
    if (largada_flag) {
        /* Le o carimbo ANTES de baixar a bandeira: enquanto ela esta em pe
           a ISR nao escreve por cima, mas depois de baixada um repique da
           porta ja poderia trocar largada_us debaixo da leitura. */
        const uint64_t t = largada_us;
        largada_flag = false;
        inicia_corrida(t, false);
        return;
    }
    limpa_sensores();   /* disparo fora de prova e so ruido */
    fechou_flag = false;

    /* Segurar um carrinho sobre o sensor da pista 1 por alguns segundos
       dispara a demo: testa o painel inteiro sem botao nenhum, e de quebra
       prova que a polaridade do sensor esta certa. */
    if (!sensor_ve_carro(0)) {
        gesto_desde_us = 0;
        gesto_armado   = true;
    } else if (gesto_armado) {
        if (gesto_desde_us == 0) {
            gesto_desde_us = time_us_64();
        } else if (time_us_64() - gesto_desde_us >= GESTO_DEMO_MS * 1000ull) {
            gesto_armado   = false;   /* sensor preso nao repete a demo */
            gesto_desde_us = 0;
            inicia_demo();
            return;
        }
    }

    const uint64_t agora = time_us_64();
    if (agora - t_pisca_us >= PISCA_MS * 1000ull) {
        t_pisca_us = agora;
        pisca = !pisca;
    }
    /* Porta aberta com a prova armada = ninguem vai largar: os tracos
       piscando pedem para fechar a porta. */
    int visual = (porta_aberta() && !pisca) ? 0 : 1;
    if (visual != armado_visual) {
        armado_visual = visual;
        disp_texto_todos(visual ? "----" : "    ");
    }
}

static void tick_correndo(void)
{
    /* 1. Recolhe o que os sensores marcaram e ordena por tempo ANTES de
          numerar: duas pistas podem disparar na mesma volta do loop, e a
          ordem do laco nao e a ordem de chegada. */
    int      idx[N_PISTAS];
    uint64_t ts[N_PISTAS];
    int      n = 0;

    for (int i = 0; i < N_PISTAS; i++) {
        if (!sensor_flag[i]) continue;
        uint64_t t = sensor_us[i];
        sensor_flag[i] = false;
        if (pista[i].chegou) continue;
        idx[n] = i; ts[n] = t; n++;
    }
    for (int a = 1; a < n; a++) {
        uint64_t t = ts[a];
        int      k = idx[a];
        int      b = a - 1;
        while (b >= 0 && ts[b] > t) {
            ts[b + 1] = ts[b]; idx[b + 1] = idx[b]; b--;
        }
        ts[b + 1] = t; idx[b + 1] = k;
    }
    for (int a = 0; a < n; a++) registra_chegada(idx[a], ts[a]);

    const uint64_t agora = time_us_64();
    const uint32_t el    = (uint32_t)((agora - t0_us) / 1000u);

    /* 2. Corrida demo: as chegadas entram pelo mesmo caminho das reais. */
    if (demo) {
        for (int i = 0; i < N_PISTAS; i++)
            if (!pista[i].chegou && el >= demo_ms[i])
                registra_chegada(i, t0_us + (uint64_t)demo_ms[i] * 1000u);
    }

    /* 3. Quem ainda nao chegou mostra o cronometro correndo. */
    if (agora - t_refresh_us >= REFRESH_CORRIDA_MS * 1000ull) {
        t_refresh_us = agora;
        for (int i = 0; i < N_PISTAS; i++)
            if (!pista[i].chegou) disp_tempo(i, el);
    }

    /* 4. Fim: todos chegaram, ou estourou o tempo limite, ou acabou a
          espera pelos retardatarios -- o que vier antes. */
    bool fim = (n_chegadas == N_PISTAS)
            || (agora - t0_us >= TEMPO_LIMITE_MS * 1000ull)
            || (t_primeiro_us != 0 &&
                agora - t_primeiro_us >= ESPERA_APOS_1o_MS * 1000ull);
    if (fim) finaliza();
}

static void tick_resultado(void)
{
    const uint64_t agora = time_us_64();
    limpa_sensores();

    uint32_t limite = (fase == FASE_POSICAO) ? MOSTRA_POSICAO_MS : MOSTRA_TEMPO_MS;
    if (agora - t_fase_us >= limite * 1000ull) {
        fase      = (fase == FASE_POSICAO) ? FASE_TEMPO : FASE_POSICAO;
        t_fase_us = agora;
        mostra_resultado();
    }

    if (fechou_flag) {          /* a porta voltou: proxima prova */
        fechou_flag = false;
        rearma();
        return;
    }
    /* Se a porta ja estava fechada (caiu durante a prova, por exemplo),
       rearma sozinho depois de um ciclo inteiro de resultado. */
    if (!porta_aberta() &&
        agora - t_resultado_us >= RESULTADO_MIN_MS * 1000ull)
        rearma();
}

/* ------------------------------------------------------------------ */
/* Botao TESTE: toque curto rearma, pressao longa roda a demo.         */
/* ------------------------------------------------------------------ */
static void trata_botao(void)
{
#if USAR_BOTAO
    const bool     apertado = (gpio_get(PIN_BOTAO) == 0);
    const uint64_t agora    = time_us_64();

    if (apertado && !botao_antes) {
        botao_desde_us = agora;
        botao_tratado  = false;
    }
    if (apertado && !botao_tratado &&
        agora - botao_desde_us >= BOTAO_LONGO_MS * 1000ull) {
        botao_tratado = true;
        inicia_demo();
    }
    if (!apertado && botao_antes && !botao_tratado &&
        agora - botao_desde_us >= DEBOUNCE_BOTAO_MS * 1000ull) {
        rearma();
    }
    botao_antes = apertado;
#endif
}

/* ------------------------------------------------------------------ */
/* Init                                                                */
/* ------------------------------------------------------------------ */
static void pinos_init(void)
{
    for (int i = 0; i < N_PISTAS; i++) {
        gpio_init(PIN_SENSOR[i]);
        gpio_set_dir(PIN_SENSOR[i], GPIO_IN);
        /* O LM393 do TCRT5000 tem saida em coletor aberto. O modulo ja traz
           o proprio pull-up; o interno fica em paralelo e cobre o caso de um
           fio solto, que assim le 1 = sem carro em vez de flutuar. */
        gpio_pull_up(PIN_SENSOR[i]);
    }

    gpio_init(PIN_LARGADA);
    gpio_set_dir(PIN_LARGADA, GPIO_IN);
    gpio_pull_up(PIN_LARGADA);

#if USAR_BOTAO
    gpio_init(PIN_BOTAO);
    gpio_set_dir(PIN_BOTAO, GPIO_IN);
    gpio_pull_up(PIN_BOTAO);
#endif
}

static void irqs_init(void)
{
    gpio_set_irq_enabled_with_callback(PIN_LARGADA,
        GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, true, gpio_isr);
    for (int i = 0; i < N_PISTAS; i++)
        gpio_set_irq_enabled(PIN_SENSOR[i],
            GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, true);
}

void cronometro_init(void)
{
    pinos_init();
    som_init();
    disp_init();

    /* Teste de fiacao: TUDO aceso (segmentos + pontos), depois o numero da
       pista. Se um display ficar apagado ou mostrar o numero de outra
       pista, o erro esta no DIO dele -- nao no firmware. O primeiro quadro
       tambem mostra quais separadores o modulo tem de verdade: ver
       DISPLAY_PONTO_DECIMAL em config.h. */
    for (int i = 0; i < N_PISTAS; i++) disp_tudo_aceso(i);
    som_bip(SOM_BOOT_HZ, SOM_BOOT_MS);
    sleep_ms(700);
    for (int i = 0; i < N_PISTAS; i++) disp_posicao(i, i + 1);
    sleep_ms(900);

    for (int i = 0; i < N_PISTAS; i++)
        if (!disp_respondeu(i))
            printf("[aviso] display da pista %d nao deu ACK\n", i + 1);

    irqs_init();
    rearma();
}

void cronometro_tick(void)
{
    trata_botao();
    switch (estado) {
    case EST_ARMADO:    tick_armado();    break;
    case EST_CORRENDO:  tick_correndo();  break;
    case EST_RESULTADO: tick_resultado(); break;
    }
}
