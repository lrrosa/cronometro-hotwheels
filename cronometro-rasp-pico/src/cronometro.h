/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
/*
 * cronometro.h -- maquina de estados da prova.
 *
 *   ARMADO  --(porta abre)-->  CORRENDO  --(todos chegaram | tempo)-->
 *   RESULTADO  --(porta fecha | botao)-->  ARMADO
 */
#ifndef CRONOMETRO_H
#define CRONOMETRO_H

void cronometro_init(void);
void cronometro_tick(void);

#endif /* CRONOMETRO_H */
