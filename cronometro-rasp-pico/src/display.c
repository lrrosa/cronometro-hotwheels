/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
#include "display.h"
#include "config.h"
#include "tm1637.h"

#include <string.h>

static tm1637_t dsp[N_PISTAS];
static bool     ack_ok[N_PISTAS];

#define PONTO 0x80

/* Fonte de 7 segmentos: bit0=a (topo) ... bit6=g (meio). */
static uint8_t seg_char(char c)
{
    switch (c) {
    case '0': return 0x3F;
    case '1': return 0x06;
    case '2': return 0x5B;
    case '3': return 0x4F;
    case '4': return 0x66;
    case '5': return 0x6D;
    case '6': return 0x7D;
    case '7': return 0x07;
    case '8': return 0x7F;
    case '9': return 0x6F;
    case ' ': return 0x00;
    case '-': return 0x40;
    case '_': return 0x08;
    case 'A': return 0x77;
    case 'b': return 0x7C;
    case 'C': return 0x39;
    case 'd': return 0x5E;
    case 'E': return 0x79;
    case 'F': return 0x71;
    case 'H': return 0x76;
    case 'h': return 0x74;
    case 'I': return 0x06;
    case 'J': return 0x1E;
    case 'L': return 0x38;
    case 'n': return 0x54;
    case 'o': return 0x5C;
    case 'P': return 0x73;
    case 'r': return 0x50;
    case 'S': return 0x6D;
    case 't': return 0x78;
    case 'U': return 0x3E;
    case 'u': return 0x1C;
    default:  return 0x00;
    }
}

static void envia(int p, const uint8_t seg[4])
{
    if (p < 0 || p >= N_PISTAS) return;
    ack_ok[p] = tm1637_segmentos(&dsp[p], seg);
}

void disp_init(void)
{
    for (int p = 0; p < N_PISTAS; p++) {
        dsp[p].clk = PIN_TM_CLK;
        dsp[p].dio = PIN_TM_DIO[p];
        tm1637_init(&dsp[p]);
    }
    /*
     * So depois que os seis DIO existem como pino e que da para falar com
     * qualquer um deles: o CLK e comum, e um DIO ainda flutuando poderia
     * ser lido como um START pelo modulo vizinho.
     */
    for (int p = 0; p < N_PISTAS; p++) {
        ack_ok[p] = tm1637_brilho(&dsp[p], TM1637_BRILHO, true);
        disp_texto(p, "    ");
    }
}

void disp_texto(int pista, const char *s4)
{
    uint8_t seg[4];
    for (int i = 0; i < 4; i++)
        seg[i] = (s4[i] != '\0') ? seg_char(s4[i]) : 0x00;
    envia(pista, seg);
}

void disp_tudo_aceso(int pista)
{
    const uint8_t seg[4] = { 0xFF, 0xFF, 0xFF, 0xFF };
    envia(pista, seg);
}

void disp_texto_todos(const char *s4)
{
    for (int p = 0; p < N_PISTAS; p++)
        disp_texto(p, s4);
}

void disp_tempo(int pista, uint32_t ms)
{
    uint8_t seg[4];

    if (ms == TEMPO_INVALIDO || ms >= 100000u) {
        disp_texto(pista, "----");
        return;
    }

    if (ms < 10000u) {                       /* S.mmm */
        seg[0] = seg_char('0' + (ms / 1000u));
        seg[1] = seg_char('0' + (ms / 100u) % 10u);
        seg[2] = seg_char('0' + (ms / 10u)  % 10u);
        seg[3] = seg_char('0' + (ms % 10u));
#if DISPLAY_PONTO_DECIMAL
        seg[0] |= PONTO;
#endif
    } else {                                 /* SS.mm */
        seg[0] = seg_char('0' + (ms / 10000u));
        seg[1] = seg_char('0' + (ms / 1000u) % 10u);
        seg[2] = seg_char('0' + (ms / 100u)  % 10u);
        seg[3] = seg_char('0' + (ms / 10u)   % 10u);
        /*
         * Aqui o separador acende nos DOIS tipos de modulo, de proposito.
         * Sem separador nenhum, "1234" seria 1,234 s ou 12,34 s -- nao da
         * para saber. Aceso, o modulo de ponto mostra 12.34 e o de relogio
         * mostra 12:34; os dois se leem como 12,34 s, e o separador apagado
         * passa a significar "este tempo esta no formato S.mmm".
         */
#if DISPLAY_PONTO_DECIMAL
        seg[1] |= PONTO;
#else
        /* No modulo de relogio o dois-pontos e um so, e qual digito carrega
           o bit que o acende muda de implementacao para implementacao.
           Marcar os dois primeiros acende do mesmo jeito, e nao existe
           "dois-pontos no lugar errado" num display que so tem um. */
        seg[0] |= PONTO;
        seg[1] |= PONTO;
#endif
    }
    envia(pista, seg);
}

void disp_posicao(int pista, int pos)
{
    char s[5] = "    ";
    if (pos >= 1 && pos <= 9)
        s[3] = (char)('0' + pos);
    disp_texto(pista, s);
}

void disp_dnf(int pista)
{
    disp_texto(pista, " dnF");
}

bool disp_respondeu(int pista)
{
    if (pista < 0 || pista >= N_PISTAS) return false;
    return ack_ok[pista];
}
