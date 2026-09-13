/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
/*
 * tm1637.h -- driver bit-bang para o display TM1637 de 4 digitos.
 *
 * O TM1637 usa dois fios (CLK/DIO) num protocolo parecido com I2C mas sem
 * endereco: quem escolhe o chip e a linha DIO. Por isso os seis displays
 * dividem o mesmo CLK e so o DIO e individual -- ver README.
 */
#ifndef TM1637_H
#define TM1637_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint8_t clk;
    uint8_t dio;
} tm1637_t;

/* Prepara os pinos. Pode ser chamado varias vezes com o mesmo CLK. */
void tm1637_init(const tm1637_t *d);

/* brilho 0..7; ligado=false apaga sem perder o conteudo. */
bool tm1637_brilho(const tm1637_t *d, uint8_t brilho, bool ligado);

/* Quatro bytes de segmentos, da esquerda para a direita.
   bit0=a bit1=b bit2=c bit3=d bit4=e bit5=f bit6=g bit7=ponto/dois-pontos.
   Retorna false se o display nao deu ACK (fio solto, modulo sem energia). */
bool tm1637_segmentos(const tm1637_t *d, const uint8_t seg[4]);

#endif /* TM1637_H */
