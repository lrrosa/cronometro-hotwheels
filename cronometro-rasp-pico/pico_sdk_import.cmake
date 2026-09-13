# pico_sdk_import.cmake -- atalho padrao para importar o Pico SDK.
#
# Copie este arquivo do diretorio /external/ do Pico SDK ou use este snippet,
# que e funcionalmente equivalente. Procura por PICO_SDK_PATH em ordem:
#   1) argumento -DPICO_SDK_PATH=...
#   2) variavel de ambiente PICO_SDK_PATH
#   3) PICO_SDK_FETCH_FROM_GIT  (clona automaticamente)

if (DEFINED ENV{PICO_SDK_PATH} AND (NOT PICO_SDK_PATH))
    set(PICO_SDK_PATH $ENV{PICO_SDK_PATH})
    message("Usando PICO_SDK_PATH de variavel de ambiente: ${PICO_SDK_PATH}")
endif ()

if (DEFINED ENV{PICO_SDK_FETCH_FROM_GIT} AND (NOT PICO_SDK_FETCH_FROM_GIT))
    set(PICO_SDK_FETCH_FROM_GIT $ENV{PICO_SDK_FETCH_FROM_GIT})
endif ()

if (NOT PICO_SDK_PATH AND PICO_SDK_FETCH_FROM_GIT)
    include(FetchContent)
    set(FETCHCONTENT_BASE_DIR_SAVE ${FETCHCONTENT_BASE_DIR})
    set(FETCHCONTENT_BASE_DIR ${CMAKE_BINARY_DIR}/_deps)
    FetchContent_Declare(
        pico_sdk
        GIT_REPOSITORY https://github.com/raspberrypi/pico-sdk.git
        GIT_TAG        master
    )
    FetchContent_GetProperties(pico_sdk)
    if (NOT pico_sdk_POPULATED)
        message("Baixando Pico SDK ...")
        FetchContent_Populate(pico_sdk)
        set(PICO_SDK_PATH ${pico_sdk_SOURCE_DIR})
    endif ()
    set(FETCHCONTENT_BASE_DIR ${FETCHCONTENT_BASE_DIR_SAVE})
endif ()

if (NOT PICO_SDK_PATH)
    message(FATAL_ERROR
        "PICO_SDK_PATH nao definido. Defina a variavel de ambiente PICO_SDK_PATH "
        "ou passe -DPICO_SDK_PATH=/caminho/para/pico-sdk no cmake.")
endif ()

get_filename_component(PICO_SDK_PATH "${PICO_SDK_PATH}" REALPATH BASE_DIR "${CMAKE_BINARY_DIR}")
if (NOT EXISTS ${PICO_SDK_PATH})
    message(FATAL_ERROR "Diretorio PICO_SDK_PATH '${PICO_SDK_PATH}' nao existe")
endif ()

set(PICO_SDK_INIT_CMAKE_FILE ${PICO_SDK_PATH}/pico_sdk_init.cmake)
if (NOT EXISTS ${PICO_SDK_INIT_CMAKE_FILE})
    message(FATAL_ERROR
        "Diretorio em PICO_SDK_PATH '${PICO_SDK_PATH}' nao parece conter o Pico SDK")
endif ()

set(PICO_SDK_PATH ${PICO_SDK_PATH} CACHE PATH "Path to the Raspberry Pi Pico SDK" FORCE)

include(${PICO_SDK_INIT_CMAKE_FILE})
