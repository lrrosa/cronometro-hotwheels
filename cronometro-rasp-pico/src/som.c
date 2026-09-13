/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Leonardo Roman da Rosa */
#include "som.h"
#include "config.h"

#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/clocks.h"

#if USAR_BUZZER

#define PWM_TOP 4095   /* topo largo para o clkdiv nao saturar nos graves */

static uint     slice;
static uint64_t fim_us;
static bool     tocando;

void som_init(void)
{
    gpio_set_function(PIN_BUZZER, GPIO_FUNC_PWM);
    slice = pwm_gpio_to_slice_num(PIN_BUZZER);
    pwm_set_wrap(slice, PWM_TOP);
    pwm_set_gpio_level(PIN_BUZZER, 0);
    pwm_set_enabled(slice, false);
    tocando = false;
}

void som_bip(uint16_t hz, uint16_t ms)
{
    if (hz == 0 || ms == 0) return;

    float div = (float)clock_get_hz(clk_sys) / ((float)hz * (PWM_TOP + 1));
    if (div < 1.0f)   div = 1.0f;
    if (div > 255.0f) div = 255.0f;

    pwm_set_clkdiv(slice, div);
    pwm_set_wrap(slice, PWM_TOP);
    pwm_set_gpio_level(PIN_BUZZER, PWM_TOP / 2);
    pwm_set_enabled(slice, true);

    fim_us  = time_us_64() + (uint64_t)ms * 1000u;
    tocando = true;
}

void som_tick(void)
{
    if (!tocando) return;
    if (time_us_64() < fim_us) return;
    pwm_set_gpio_level(PIN_BUZZER, 0);
    pwm_set_enabled(slice, false);
    tocando = false;
}

#else  /* USAR_BUZZER */

void som_init(void) {}
void som_bip(uint16_t hz, uint16_t ms) { (void)hz; (void)ms; }
void som_tick(void) {}

#endif
