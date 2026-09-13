/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
/*
 * Cronometro de 6 pistas para pista de carrinhos Hot Wheels.
 *
 * Um microswitch na porta de largada marca o t0; um sensor de luz no fim
 * de cada pista marca a chegada; seis TM1637 mostram a colocacao e depois
 * o tempo. Alvo: RP2040 (Raspberry Pi Pico e clones).
 */
#include "pico/stdlib.h"
#include "cronometro.h"
#include "som.h"

#include <stdio.h>

int main(void)
{
    stdio_init_all();

    printf("\n=== cronometro-hotwheels ===\n");

    cronometro_init();

    while (true) {
        cronometro_tick();
        som_tick();
        /*
         * A precisao do cronometro nao depende deste intervalo: quem
         * carimba a hora e a interrupcao de GPIO, com time_us_64(). O loop
         * so decide e desenha.
         */
        sleep_ms(1);
    }
}
