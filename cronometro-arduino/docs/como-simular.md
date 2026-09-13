# Como rodar no simulador — versão Arduino

Dois caminhos. O primeiro não exige instalar nada.

## Caminho 1 — wokwi.com (recomendado)

O Wokwi compila o sketch na nuvem; a sua máquina só precisa do navegador.

1. [wokwi.com](https://wokwi.com) → **New Project** → **Arduino Uno**.
2. Aba `sketch.ino`: apague tudo, cole
   [../cronometro-arduino.ino](../cronometro-arduino.ino).
3. Aba `diagram.json`: apague tudo, cole [../diagram.json](../diagram.json).
4. **Play** (▶). A primeira compilação demora uns segundos.

Salve o projeto na sua conta para não perder — e guarde o link, porque é
mais rápido reabrir do que colar de novo.

## Caminho 2 — simulador local, na extensão do VS Code

Funciona igual à versão RP2040, e pelo mesmo motivo: **a extensão Wokwi não
compila nada — ela só carrega um binário já pronto** num microcontrolador
emulado. Para o RP2040 esse binário é o `.uf2` do Pico SDK; para o Arduino é
o `.hex` do avr-gcc. O que faltava aqui era quem produzisse o `.hex`, e é
isso que o `arduino-cli` resolve. O `wokwi.toml` é só o bilhete dizendo onde
o binário está.

O `arduino-cli` e o core `arduino:avr` **já estão instalados** nesta
máquina. Então:

1. Compile, de dentro da pasta `cronometro-arduino`:

```powershell
& "C:\Users\Leonardo\arduino-cli\arduino-cli.exe" compile -b arduino:avr:uno --warnings all --output-dir build .
```

2. Abra **a pasta `cronometro-arduino` como raiz do workspace** do VS Code
   (não a pasta de cima — os caminhos do `wokwi.toml` são relativos à raiz).
3. Abra `diagram.json` e rode `Ctrl+Shift+P` → **Wokwi: Start Simulator**.

O `--output-dir build` é o que faz o `.hex` e o `.elf` caírem onde o
[wokwi.toml](../wokwi.toml) espera. Mudou o sketch? Recompile e reinicie o
simulador.

Com o `.elf` presente a extensão também dá **depuração**: pontos de parada e
inspeção de variáveis dentro do VS Code, o que o wokwi.com não oferece.

### Qual dos dois usar

| | wokwi.com | VS Code |
| --- | --- | --- |
| Compilar antes | não | sim |
| Editar o sketch | no navegador | no seu editor, com git |
| Depurador | não | sim (precisa do `.elf`) |
| Bom para | ver funcionando, mostrar para alguém | trabalhar no código |

## O que fazer dentro do simulador

Assim que liga, os seis displays acendem tudo (segmentos e pontos), depois o número da raia, e
param em `----`: é o teste de fiação.

| Quero | Faço |
| --- | --- |
| **Ver uma corrida inteira** | aperte a tecla `D` e **segure 1 segundo** |
| Largar a prova | clique na **metade direita** da chavinha PORTA DE LARGADA |
| Passar um carrinho na raia N | clique no sensor TCRT5000 da raia N e **suba a luz** |
| Rearmar para a próxima | PORTA para a **esquerda** e sensores de volta ao escuro (ou toque `D`) |
| Ver os tempos em texto | aba **Serial Monitor**, 115200 |

### O caminho realista

1. Chavinha PORTA à esquerda (porta fechada). Displays em `----`.
2. Clique na **metade direita** da PORTA — é a porta abrindo. Sai o tom
   grave da largada e os seis displays começam a contar. (As chavinhas do
   Wokwi viram ao receber o clique do lado para onde você quer levá-las;
   não precisa arrastar.)
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
7. Clique na metade esquerda da PORTA: rearmado.

> Subir seis controles de luz na velocidade certa é chato — por isso existe a corrida
> demo (tecla `D` segurada). Ela sorteia seis tempos entre 2,4 e 4,6 s e
> **entra pelo mesmo caminho das chegadas reais**, então serve para conferir
> ordenação, formatação e o ciclo de resultado. O que ela *não* testa é a
> borda vinda do pino — para isso, suba a luz de um sensor à mão em pelo
> menos uma raia.

## O que dá para conferir aqui

- a colocação sai na ordem certa, inclusive com duas raias quase juntas;
- o tempo sai como `3721`, que se lê 3,721 s (o TM1637 do Wokwi é o de
  relógio, só com dois-pontos no meio — e o módulo azul do pacote de 10
  também é, por isso `DISPLAY_PONTO_DECIMAL` está em `0`);
- **a interrupção de mudança de pino** funciona com os seis sensores: se a
  `PCINT1` estivesse mal configurada, alguma raia simplesmente não
  registraria;
- os seis TM1637 funcionam com o **CLK compartilhado** — se houvesse
  conflito, displays vizinhos mostrariam lixo quando um deles é escrito;
- o repique do microswitch não antecipa nem duplica a largada (a chavinha
  do Wokwi tem bounce ligado de propósito);
- o rearme pela porta e o `dnF` de quem não chegou;
- o log serial completo de cada prova.

## O que **não** dá (só na bancada)

- a distância e o trimpot de cada TCRT5000 com os carros de verdade — é o
  ajuste físico que resta, ver
  [a lista de material](../../cronometro-rasp-pico/docs/bom.md);
- consumo dos seis displays a 5 V (por USB dá; pelo conector DC de 12 V o
  regulador esquenta — ver [diferencas-rp2040.md](diferencas-rp2040.md));
- ruído elétrico no cabo dos sensores.

## Se mexer no diagrama

`diagram.json` é **gerado**, não editado à mão:

```bash
python tools/gen_diagram.py
```

O script calcula os waypoints de cada fio (sem eles o Wokwi liga pino a pino
em linha reta, e a fiação passa por cima dos dígitos), confere se alguma
peça ou texto invade as faixas reservadas para fiação, e ainda confere se os
pinos do diagrama batem com os do sketch.
