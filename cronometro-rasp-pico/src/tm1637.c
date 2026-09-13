/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
#include "tm1637.h"
#include "config.h"

#include "pico/stdlib.h"
#include "hardware/gpio.h"

/*
 * CLK e push-pull: o mestre e o unico que o dirige, e com seis modulos
 * pendurados (cada um com seu pull-up de 10 k) um dreno aberto teria que
 * puxar ~1,7 k. DIO e dreno aberto emulado -- o valor de saida fica em 0
 * para sempre e o que muda e a direcao do pino, o que evita qualquer
 * glitch entre "escrever 0" e "virar saida".
 */
#define DLY() busy_wait_us_32(TM1637_BIT_US)

static inline void dio_baixo(const tm1637_t *d)  { gpio_set_dir(d->dio, GPIO_OUT); }
static inline void dio_solta(const tm1637_t *d)  { gpio_set_dir(d->dio, GPIO_IN);  }
static inline void clk_baixo(const tm1637_t *d)  { gpio_put(d->clk, 0); }
static inline void clk_alto(const tm1637_t *d)   { gpio_put(d->clk, 1); }

void tm1637_init(const tm1637_t *d)
{
    gpio_init(d->clk);
    gpio_put(d->clk, 1);
    gpio_set_dir(d->clk, GPIO_OUT);

    gpio_init(d->dio);
    gpio_put(d->dio, 0);          /* nunca muda; a direcao e que comanda */
    gpio_set_dir(d->dio, GPIO_IN);
    gpio_pull_up(d->dio);         /* garante o nivel alto mesmo sem o
                                     pull-up do modulo */
}

/* START: DIO desce enquanto CLK esta alto. */
static void inicio(const tm1637_t *d)
{
    clk_alto(d); dio_solta(d); DLY();
    dio_baixo(d);               DLY();
    clk_baixo(d);               DLY();
}

/* STOP: DIO sobe enquanto CLK esta alto. */
static void fim(const tm1637_t *d)
{
    clk_baixo(d); dio_baixo(d); DLY();
    clk_alto(d);                DLY();
    dio_solta(d);               DLY();
}

static bool escreve_byte(const tm1637_t *d, uint8_t b)
{
    for (int i = 0; i < 8; i++) {      /* LSB primeiro */
        clk_baixo(d);
        if (b & 1) dio_solta(d); else dio_baixo(d);
        b >>= 1;
        DLY();
        clk_alto(d);
        DLY();
    }
    /* ACK: o TM1637 puxa o DIO para baixo no nono clock. */
    clk_baixo(d);
    dio_solta(d);
    DLY();
    clk_alto(d);
    DLY();
    bool ack = (gpio_get(d->dio) == 0);
    clk_baixo(d);
    DLY();
    return ack;
}

bool tm1637_brilho(const tm1637_t *d, uint8_t brilho, bool ligado)
{
    inicio(d);
    bool ack = escreve_byte(d, 0x80 | (ligado ? 0x08 : 0x00) | (brilho & 0x07));
    fim(d);
    return ack;
}

bool tm1637_segmentos(const tm1637_t *d, const uint8_t seg[4])
{
    bool ack;

    inicio(d);
    ack = escreve_byte(d, 0x40);       /* escrita com endereco automatico */
    fim(d);

    inicio(d);
    ack &= escreve_byte(d, 0xC0);      /* comeca no digito 0 */
    for (int i = 0; i < 4; i++)
        ack &= escreve_byte(d, seg[i]);
    fim(d);

    return ack;
}
