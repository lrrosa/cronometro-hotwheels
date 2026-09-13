/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
#include "config.h"

/*
 * Pista 1 a esquerda, pista 6 a direita -- a mesma ordem em que os
 * displays aparecem no painel e em diagram.json.
 *
 * Os sensores ficam em GPIOs contiguos de proposito: facil de conferir no
 * cabo flat e permite ler os seis de uma vez com gpio_get_all() se um dia
 * for preciso amostrar por polling em vez de interrupcao.
 */
const uint8_t PIN_SENSOR[N_PISTAS] = {  2,  3,  4,  5,  6,  7 };
const uint8_t PIN_TM_DIO[N_PISTAS] = { 10, 11, 12, 13, 14, 15 };
