# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Leonardo Roman da Rosa
cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

project(cronometro-rasp-pico C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(cronometro-rasp-pico
    src/main.c
    src/config.c
    src/cronometro.c
    src/display.c
    src/tm1637.c
    src/som.c
)

target_include_directories(cronometro-rasp-pico PRIVATE src)

target_link_libraries(cronometro-rasp-pico
    pico_stdlib
    pico_rand
    hardware_gpio
    hardware_pwm
    hardware_clocks
)

# UART0 (GP0/GP1) e o que o monitor serial do Wokwi mostra.
# USB tambem fica ligado, que e o mais pratico na placa real.
pico_enable_stdio_uart(cronometro-rasp-pico 1)
pico_enable_stdio_usb(cronometro-rasp-pico 1)

# Variantes do release (tools/empacotar_release.py): 0 ou 1 sobrescrevem os
# padroes de src/config.h sem editar o arquivo. Vazio = vale o config.h.
set(PONTO_DECIMAL "" CACHE STRING "DISPLAY_PONTO_DECIMAL (0/1)")
set(SENSOR_NIVEL "" CACHE STRING "SENSOR_NIVEL_CARRO (0/1)")
if(NOT PONTO_DECIMAL STREQUAL "")
    target_compile_definitions(cronometro-rasp-pico PRIVATE DISPLAY_PONTO_DECIMAL=${PONTO_DECIMAL})
endif()
if(NOT SENSOR_NIVEL STREQUAL "")
    target_compile_definitions(cronometro-rasp-pico PRIVATE SENSOR_NIVEL_CARRO=${SENSOR_NIVEL})
endif()

pico_add_extra_outputs(cronometro-rasp-pico)
