/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
/*
 * config.h -- pinos e constantes do cronometro de 6 pistas.
 *
 * Todos os numeros aqui sao GPIOs do RP2040, NAO posicoes fisicas do modulo.
 * A tabela GPIO -> furo de cada placa esta em docs/pinout.md.
 */
#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>
#include <stdbool.h>

/* ------------------------------------------------------------------- */
/* Pistas                                                               */
/* ------------------------------------------------------------------- */
#define N_PISTAS 6

/* ------------------------------------------------------------------- */
/* GPIOs                                                                */
/* ------------------------------------------------------------------- */
/* Saida digital D0 do modulo TCRT5000 de cada pista (ver docs/bom.md). */
extern const uint8_t PIN_SENSOR[N_PISTAS];
/* DIO de cada TM1637, um por pista. O CLK e comum aos seis. */
extern const uint8_t PIN_TM_DIO[N_PISTAS];

#define PIN_TM_CLK    9   /* CLK compartilhado pelos 6 displays        */
#define PIN_LARGADA   8   /* microswitch da porta que solta os carros  */
#define PIN_BOTAO    21   /* botao TESTE / REARMA (opcional)           */
#define PIN_BUZZER   16   /* buzzer passivo (opcional)                 */

#define USAR_BUZZER   1   /* 0 desliga o som e libera o GP16           */
#define USAR_BOTAO    1   /* 0 desliga o botao extra e libera o GP21   */

/* ------------------------------------------------------------------- */
/* Polaridades                                                          */
/* ------------------------------------------------------------------- */
/*
 * Nivel do D0 do modulo quando o carrinho esta SOBRE o sensor.
 *
 * No TCRT5000 o LM393 tem saida em coletor aberto e o modulo ja traz o
 * pull-up: sem carro nada reflete e o D0 fica em 1; com o carro em cima o
 * fototransistor conduz, o comparador vira e o D0 cai para 0. Ou seja:
 * carro = borda de DESCIDA, e o LED de saida do modulo acende.
 *
 * CONFIRA NO SEU MODULO antes de montar as seis pistas -- ha lote que sai
 * invertido. Ligue um so, ponha um carrinho em cima e veja o LED: se ele
 * acender com o carro, este valor esta certo. Outro teste, sem multimetro:
 * com a prova armada, segurar um carrinho sobre o sensor da pista 1 por
 * 2 s tem que disparar a corrida demo (ver GESTO_DEMO_MS).
 */
#ifndef SENSOR_NIVEL_CARRO      /* o release compila variantes com -D */
#define SENSOR_NIVEL_CARRO 0
#endif

/*
 * Nivel do pino de largada com a porta ABERTA.
 * Microswitch ligado entre o GPIO e o GND, com pull-up interno:
 * porta fechada = contato fechado = 0; porta abre = 1.
 */
#define LARGADA_NIVEL_ABERTA 1

/* ------------------------------------------------------------------- */
/* Tempos (ms)                                                          */
/* ------------------------------------------------------------------- */
#define TEMPO_MIN_MS         150  /* chegada antes disso = ruido, ignora */
#define TEMPO_LIMITE_MS    15000  /* fim da prova por tempo absoluto     */
#define ESPERA_APOS_1o_MS   8000  /* fim da prova apos o primeiro colocado*/

#define MOSTRA_POSICAO_MS   4500  /* colocacao no ciclo de resultado     */
#define MOSTRA_TEMPO_MS     7000  /* tempo no ciclo de resultado         */
#define PISCA_MS             400  /* meio periodo do pisca-pisca         */

/*
 * Quanto o placar fica na tela antes de rearmar sozinho. So vale quando a
 * porta JA esta fechada (corrida demo, ou porta que caiu durante a prova);
 * na prova de verdade o operador rearma fechando a porta, quando quiser.
 * Dois ciclos inteiros de colocacao + tempo.
 */
#define RESULTADO_MIN_MS   23000

/*
 * Periodo do cronometro correndo na tela. NAO use um numero redondo: com
 * 50 ms o ultimo digito do milissegundo fica parado em 0 e o penultimo so
 * alterna 0/5, o que parece display quebrado. Com 43 ms os dez algarismos
 * aparecem e a leitura fica com cara de cronometro de verdade.
 */
#define REFRESH_CORRIDA_MS    43

/*
 * A largada nao tem janela de debounce por tempo: o repique do microswitch
 * so acontece DEPOIS da primeira borda, entao a primeira e sempre a boa e
 * a ISR guarda essa. Este valor e so do botao de teste.
 */
#define DEBOUNCE_BOTAO_MS     20
#define BOTAO_LONGO_MS      1000  /* pressao longa do botao = corrida demo*/
#define GESTO_DEMO_MS       2000  /* carrinho sobre o sensor 1 = demo    */

/* ------------------------------------------------------------------- */
/* Sons (Hz, ms) -- o buzzer do Wokwi e onda quadrada, entao grave soa   */
/* melhor que agudo. A largada e um tom longo e baixo, de buzina.        */
/* ------------------------------------------------------------------- */
#define SOM_LARGADA_HZ     330
#define SOM_LARGADA_MS     600
#define SOM_CHEGADA_HZ    1400   /* cai 150 Hz por colocacao             */
#define SOM_CHEGADA_MS      70
#define SOM_FIM_HZ         220
#define SOM_FIM_MS         450
#define SOM_BOOT_HZ        880
#define SOM_BOOT_MS         80

/* ------------------------------------------------------------------- */
/* Displays                                                             */
/* ------------------------------------------------------------------- */
#define TM1637_BRILHO     4  /* 0..7 -- ver docs/bom.md sobre consumo    */
#define TM1637_BIT_US     5  /* meio periodo do clock bit-bang (~60 kHz) */

/*
 *   0 = so o dois-pontos central e ligado. O tempo sai "3721" e se le
 *       3,721 s. E o que o TM1637 do Wokwi modela.
 *   1 = cada digito tem o proprio ponto ligado -> "3.721", como no video
 *       original.
 *
 * O vidro do modulo preto de 0,56" TEM os pontinhos, mas em varios lotes
 * eles nao estao ligados no TM1637 -- so o dois-pontos esta. Nao da para
 * saber olhando: o teste de fiacao do boot acende TODOS os segmentos e
 * TODOS os pontos (0xFF em cada digito) justamente para isso. Ligue uma
 * vez e veja o que acendeu:
 *   um ponto embaixo de cada digito  -> ponha 1
 *   so os dois pontinhos do meio     -> deixe 0
 * No simulador sempre parece o caso 0, porque a peca do Wokwi e a de
 * relogio.
 *
 * Acima de 10 s o separador acende nos dois casos -- ver disp_tempo().
 */
#ifndef DISPLAY_PONTO_DECIMAL   /* o release compila variantes com -D */
#define DISPLAY_PONTO_DECIMAL 0
#endif

/* ------------------------------------------------------------------- */
/* Corrida demo (simulador e bancada)                                   */
/* ------------------------------------------------------------------- */
#define DEMO_MS_MIN  2400
#define DEMO_MS_MAX  4600

#endif /* CONFIG_H */
