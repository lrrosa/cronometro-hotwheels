/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
/*
 * display.h -- o que aparece em cada um dos seis TM1637.
 * Aqui mora a fonte de 7 segmentos e a formatacao; o protocolo esta em
 * tm1637.c. "pista" e sempre 0..N_PISTAS-1 (a pista 1 do painel e 0 aqui).
 */
#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>
#include <stdbool.h>

#define TEMPO_INVALIDO 0xFFFFFFFFu

void disp_init(void);

/* Acende tudo que o modulo tem: 7 segmentos mais ponto/dois-pontos. E o
   teste de fiacao do boot, e tambem o que revela se o modulo liga um ponto
   por digito ou so o dois-pontos central. */
void disp_tudo_aceso(int pista);

/* Quatro caracteres, da esquerda para a direita. Aceita 0-9, - , espaco e
   as letras que o 7 segmentos consegue desenhar (ver seg_char em display.c). */
void disp_texto(int pista, const char *s4);
void disp_texto_todos(const char *s4);

/* Tempo em milissegundos. Ate 9999 ms sai como S.mmm, ate 99999 como SS.mm,
   acima disso (ou TEMPO_INVALIDO) sai "----". */
void disp_tempo(int pista, uint32_t ms);

/* Colocacao 1..6 alinhada a direita, como no painel original. */
void disp_posicao(int pista, int pos);

/* Carro que nao cruzou o sensor. */
void disp_dnf(int pista);

/* true se o ultimo envio a esse display foi confirmado com ACK. */
bool disp_respondeu(int pista);

#endif /* DISPLAY_H */
