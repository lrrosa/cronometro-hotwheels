/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
/*
 * som.h -- bips no buzzer passivo. Nao bloqueia: som_bip() so arma o tom e
 * som_tick() o desliga na hora certa, porque o loop principal nao pode
 * parar enquanto a prova corre.
 */
#ifndef SOM_H
#define SOM_H

#include <stdint.h>

void som_init(void);
void som_bip(uint16_t hz, uint16_t ms);
void som_tick(void);

#endif /* SOM_H */
