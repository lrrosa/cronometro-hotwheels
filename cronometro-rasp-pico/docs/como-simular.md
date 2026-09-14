# Como rodar no simulador Wokwi

O simulador roda o **firmware compilado de verdade** dentro de um RP2040
emulado — é o mesmo `.elf` que vai para a placa. Se funcionar aqui, o que
sobra para dar errado na bancada é fiação e sensor, não lógica.

## Uma vez só

1. No VS Code, instale a extensão **Wokwi for VS Code** e faça login
   (é gratuito; o login abre o navegador e grava o token em `~/.wokwi/`).
2. Abra **a pasta `cronometro-rasp-pico`** como raiz do workspace —
   não a pasta de cima. Os caminhos do `wokwi.toml` são relativos à raiz,
   e com a pasta errada o simulador reclama que não acha o firmware.

## Toda vez

1. Compile:

```powershell
& "C:\Program Files\Raspberry Pi\Pico SDK v1.5.1\pico-env.ps1"
& "C:\Program Files\Raspberry Pi\Pico SDK v1.5.1\ninja\ninja.exe" -C build
```

> Veio do zip do release? A pasta `build/` já traz o firmware padrão
> compilado: dá para pular este passo enquanto não mexer no código.

2. Abra `diagram.json`.
3. `Ctrl+Shift+P` → **Wokwi: Start Simulator**.

Mudou o código? Recompile e reinicie o simulador — ele relê o `.uf2`.

## O que fazer dentro do simulador

Assim que liga, os seis displays acendem tudo (segmentos e pontos), depois o número da raia,
e param em `----`: é o teste de fiação.

| Quero | Faço |
| --- | --- |
| **Ver uma corrida inteira** | aperte a tecla `D` e **segure 1 segundo** |
| Largar a prova | clique na **metade direita** da chavinha PORTA DE LARGADA |
| Passar um carrinho na raia N | clique no sensor TCRT5000 da raia N e **suba a luz** |
| Rearmar para a próxima | PORTA para a **esquerda** e sensores de volta ao escuro (ou toque `D`) |
| Ver os tempos em texto | aba **Serial Monitor** do simulador |

### O caminho realista

1. Chavinha à esquerda (porta fechada). Os displays mostram `----`.
2. Clique na **metade direita** da chavinha — é a porta abrindo. Sai o tom
   grave da largada e os seis displays começam a contar. (A chavinha é uma
   `wokwi-slide-switch`: ela vira ao receber o clique do lado para onde você
   quer levá-la; não precisa arrastar.)
3. Clique num sensor e **suba a luz** no controle que aparece — é o
   carrinho passando por cima e refletindo o infravermelho. Aquele display
   congela e passa a mostrar a colocação. (O Wokwi não tem TCRT5000; a peça
   de luz usada tem o mesmo header e a mesma lógica: escuro = sem carro,
   D0 em 1; claro = carro, D0 em 0.)
4. Repita nas outras raias, na ordem que quiser. A ordem dos cliques é a
   ordem de chegada.
5. Quem ficar no escuro vira `dnF`. A prova fecha sozinha 8 s depois do
   primeiro colocado.
6. No resultado, os displays alternam colocação (4,5 s) e tempo (7 s), e
   ficam assim enquanto a porta estiver aberta.
7. Clique na metade esquerda da chavinha: rearmado.

> Subir seis controles de luz na velocidade certa é chato — por isso existe a
> corrida demo (tecla `D` segurada). Ela sorteia seis tempos entre 2,4 e
> 4,6 s e **entra pelo mesmo caminho das chegadas reais**, então serve para
> conferir ordenação, formatação e o ciclo de resultado. O que ela *não*
> testa é a borda vinda do sensor — para isso, use o arraste manual em pelo
> menos uma raia.

## O que dá para conferir no simulador (e o que não dá)

**Dá:**

- a colocação sai na ordem certa, inclusive com duas raias chegando quase juntas;
- o tempo aparece no formato certo — `3721`, que se lê 3,721 s (o TM1637 do
  Wokwi é o de relógio, só com dois-pontos no meio, então o padrão é não
  acender separador nenhum abaixo de 10 s);
- os seis TM1637 funcionam com o **CLK compartilhado** — se houvesse conflito,
  displays vizinhos mostrariam lixo quando um deles é escrito;
- o repique do microswitch não antecipa nem duplica a largada (a chavinha do
  Wokwi tem bounce ligado de propósito);
- o rearme pela porta e o `dnF` de quem não chegou;
- a fiação: cada fio sai pela esquerda do módulo e desce até um corredor
  livre antes de correr na horizontal, então nada passa por cima dos
  dígitos. Se ainda assim algum fio incomodar, **arraste a peça** — o Wokwi
  refaz o traçado sozinho;
- o log serial completo de cada prova.

**Não dá** (só na bancada):

- a distância e o trimpot de cada TCRT5000 com os carros de verdade — é o
  ajuste físico que resta, ver [bom.md](bom.md);
- consumo dos seis displays no regulador de 3,3 V do Pico;
- ruído elétrico no cabo dos sensores.
