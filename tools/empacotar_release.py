# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Leonardo Roman da Rosa
"""
Monta os pacotes de release, um por placa, em dist/:

    python tools/empacotar_release.py 1.0.0

    dist/cronometro-hotwheels-rasp-pico-v1.0.0.zip
    dist/cronometro-hotwheels-arduino-v1.0.0.zip

Cada zip abre numa pasta com o nome do projeto da placa. No Arduino isso nao
e enfeite: o IDE so abre o .ino se ele estiver numa pasta de mesmo nome.
Dentro fica a mesma estrutura do repositorio -- por isso os links relativos
dos documentos continuam valendo --, sem as ferramentas de desenvolvimento e
com o que interessa a quem vai montar:

- LEIA-ME.txt: a montagem em ordem, em texto puro;
- LICENSE, LICENSE-HARDWARE.txt e NOTICE;
- o diagrama de fiacao tambem em PNG, que qualquer visualizador abre;
- build/ com o binario padrao, no caminho que o wokwi.toml espera: o
  simulador do VS Code roda direto do zip, sem compilar nada;
- no Pico, quatro .uf2 prontos (ponto decimal x polaridade do sensor): gravar
  um .uf2 nao exige nada, recompilar exige o Pico SDK;
- no Arduino, a lista de material, que no repositorio mora na pasta do Pico.

Link que aponta para fora do pacote vira URL do GitHub fixada na tag da
versao, e o script confere que todo link relativo que sobrou existe dentro
do zip.

Requisitos: Pico SDK 1.5.1 (PICO_ENV_CMD aponta o pico-env.cmd), arduino-cli
com o core arduino:avr (ARDUINO_CLI) e Microsoft Edge (EDGE) para o PNG. O
release tem que corresponder a um commit: com a arvore suja o script para, a
menos que receba --permitir-sujo (para testar).
"""
import hashlib, io, os, posixpath, re, shutil, struct, subprocess, sys, tempfile, time, zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/lrrosa/cronometro-hotwheels"
PICO_ENV_CMD = os.environ.get("PICO_ENV_CMD",
                              r"C:\Program Files\Raspberry Pi\Pico SDK v1.5.1\pico-env.cmd")
EDGE = os.environ.get("EDGE", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
ARDUINO_CLI = (os.environ.get("ARDUINO_CLI") or shutil.which("arduino-cli")
               or os.path.join(os.path.expanduser("~"), "arduino-cli", "arduino-cli.exe"))

LICENCAS = {"LICENSE": "LICENSE", "LICENSE-HARDWARE.txt": "LICENSE-HARDWARE.txt",
            "NOTICE": "NOTICE"}

# (ponto decimal, sensor invertido, sufixo do .uf2)
VARIANTES_PICO = [(0, 0, ""), (1, 0, "-ponto-decimal"), (0, 1, "-sensor-invertido"),
                  (1, 1, "-ponto-decimal-sensor-invertido")]

# ------------------------------------------------------------------ listas
def arquivos_pico():
    pasta = "cronometro-rasp-pico"
    rel = ["README.md", "CMakeLists.txt", "pico_sdk_import.cmake", "diagram.json", "wokwi.toml",
           "docs/bom.md", "docs/como-simular.md", "docs/pinout.md",
           "docs/esquema-kicad.pdf", "docs/esquema-kicad.svg", "docs/fiacao-pico.svg",
           "kicad/cronometro-rasp-pico.kicad_pro", "kicad/cronometro-rasp-pico.kicad_sch"]
    rel += sorted("src/" + f for f in os.listdir(os.path.join(RAIZ, pasta, "src"))
                  if f.endswith((".c", ".h")))
    mapa = {f"{pasta}/{r}": r for r in rel}
    mapa.update(LICENCAS)
    return pasta, mapa

def arquivos_arduino():
    pasta = "cronometro-arduino"
    rel = ["README.md", "cronometro-arduino.ino", "diagram.json", "wokwi.toml",
           "docs/como-simular.md", "docs/diferencas-rp2040.md", "docs/pinout.md",
           "docs/esquema-kicad.pdf", "docs/esquema-kicad.svg", "docs/fiacao-arduino.svg",
           "kicad/cronometro-arduino.kicad_pro", "kicad/cronometro-arduino.kicad_sch"]
    mapa = {f"{pasta}/{r}": r for r in rel}
    mapa["cronometro-rasp-pico/docs/bom.md"] = "docs/bom.md"   # a lista vale para as duas
    mapa.update(LICENCAS)
    return pasta, mapa

# ------------------------------------------------------------------- links
LINK = re.compile(r"(\]\()([^)\s]+)(\))")

def _rel(alvo_pkg, base_pkg):
    return posixpath.relpath("/p/" + alvo_pkg, "/p/" + base_pkg if base_pkg else "/p")

def _versionado(caminho_repo):
    r = subprocess.run(["git", "-C", RAIZ, "ls-files", "--", caminho_repo],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())

def reescreve_links(texto, repo_md, pkg_md, mapa, dirs, tag, existentes):
    base_repo, base_pkg = posixpath.dirname(repo_md), posixpath.dirname(pkg_md)

    def troca(m):
        alvo = m.group(2)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", alvo) or alvo.startswith("#"):
            return m.group(0)
        caminho, _, ancora = alvo.partition("#")
        repo_alvo = posixpath.normpath(posixpath.join(base_repo, caminho))
        if repo_alvo in mapa:
            novo = _rel(mapa[repo_alvo], base_pkg)
            dentro = posixpath.normpath(posixpath.join(base_pkg, novo))
        elif repo_alvo in dirs:
            novo = _rel(dirs[repo_alvo], base_pkg) + "/"
            dentro = dirs[repo_alvo]
        else:
            if not _versionado(repo_alvo):
                sys.exit(f"link para algo que nao esta no repositorio: {repo_md} -> {alvo}")
            tipo = "tree" if os.path.isdir(os.path.join(RAIZ, repo_alvo)) else "blob"
            return m.group(1) + f"{REPO}/{tipo}/{tag}/{repo_alvo}" + (
                "#" + ancora if ancora else "") + m.group(3)
        if dentro not in existentes:
            sys.exit(f"link quebrado no pacote: {pkg_md} -> {alvo}")
        return m.group(1) + novo + ("#" + ancora if ancora else "") + m.group(3)

    return LINK.sub(troca, texto)

def nota_no_readme(texto, tag):
    linhas = texto.split("\n")
    i = next(k for k, l in enumerate(linhas) if l.startswith("# "))
    nota = ["", f"> **Pacote do release {tag}.** O repositório completo — histórico, notas de",
            "> projeto e os geradores dos desenhos — está em",
            f"> <{REPO}/tree/{tag}>."]
    return "\n".join(linhas[:i + 1] + nota + linhas[i + 1:])

# ----------------------------------------------------------------- Pico SDK
def ambiente_pico():
    if not os.path.exists(PICO_ENV_CMD):
        sys.exit(f"pico-env.cmd nao encontrado: {PICO_ENV_CMD} (defina PICO_ENV_CMD)")
    r = subprocess.run(f'cmd /s /c ""{PICO_ENV_CMD}" >nul 2>&1 && set"',
                       capture_output=True, text=True, errors="replace")
    env = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l and not l.startswith("="))
    if not any(k.upper() == "PICO_SDK_PATH" for k in env):
        sys.exit("o pico-env.cmd nao definiu PICO_SDK_PATH")
    return env

def compila_variantes_pico(versao, tmp):
    """Devolve (os quatro .uf2 para binarios/, o .uf2 + .elf padrao para build/)."""
    env = ambiente_pico()
    caminho = next(v for k, v in env.items() if k.upper() == "PATH")
    cmake, ninja = shutil.which("cmake", path=caminho), shutil.which("ninja", path=caminho)
    if not cmake or not ninja:
        sys.exit("cmake ou ninja nao estao no ambiente do Pico SDK")
    src = os.path.join(RAIZ, "cronometro-rasp-pico")
    binarios, simulador, vistos = [], [], set()
    for pd, s, sufixo in VARIANTES_PICO:
        build = os.path.join(src, "build", "release", f"pd{pd}-s{s}")
        for cmd in ([cmake, "-G", "Ninja", "-S", src, "-B", build,
                     f"-DPONTO_DECIMAL={pd}", f"-DSENSOR_NIVEL={s}"],
                    [ninja, "-C", build]):
            r = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace")
            saida = r.stdout + r.stderr
            if r.returncode != 0:
                sys.exit(f"falhou: {os.path.basename(cmd[0])}\n{saida[-4000:]}")
            proprios = [l for l in saida.splitlines()
                        if "warning" in l.lower() and "cronometro-rasp-pico" in l.replace("\\", "/")]
            if proprios:
                sys.exit("aviso de compilacao no firmware:\n" + "\n".join(proprios))
        uf2 = os.path.join(build, "cronometro-rasp-pico.uf2")
        h = hashlib.sha256(open(uf2, "rb").read()).hexdigest()
        if h in vistos:
            sys.exit("duas variantes deram o mesmo binario: a opcao nao chegou ao compilador")
        vistos.add(h)
        nome = f"cronometro-rasp-pico-v{versao}{sufixo}.uf2"
        destino = os.path.join(tmp, nome)
        shutil.copyfile(uf2, destino)
        binarios.append((f"binarios/{nome}", destino))
        print(f"  {nome}: {os.path.getsize(destino)} bytes")
        if not sufixo:
            elf = os.path.join(tmp, "pico-padrao.elf")
            shutil.copyfile(os.path.join(build, "cronometro-rasp-pico.elf"), elf)
            simulador = [("build/cronometro-rasp-pico.uf2", destino),
                         ("build/cronometro-rasp-pico.elf", elf)]
    return binarios, simulador

# ------------------------------------------------------------------ Arduino
def compila_arduino(tmp):
    """Compila o sketch como ele esta (padroes do topo do .ino) e devolve o .hex e o .elf."""
    if not os.path.exists(ARDUINO_CLI):
        sys.exit(f"arduino-cli nao encontrado: {ARDUINO_CLI} (defina ARDUINO_CLI)")
    # Conferir antes de compilar: sem o core, o compile sai baixando indices e
    # ferramentas para so entao falhar.
    r = subprocess.run([ARDUINO_CLI, "core", "list"], capture_output=True, text=True,
                       errors="replace")
    if "arduino:avr" not in r.stdout:
        dica = ""
        if "WindowsApps" in sys.executable:
            # Visto nesta maquina: o Python da Microsoft Store roda num pacote que
            # da a ele e aos processos filhos uma copia privada do AppData, e o
            # arduino-cli filho nao enxerga o core instalado em Arduino15.
            dica = ("\nEste e o Python da Microsoft Store, que da aos processos filhos uma "
                    "copia privada do AppData: o arduino-cli nao enxerga o core instalado. "
                    "Rode o script com outro Python (o do Pico SDK serve: "
                    "\"C:\\Program Files\\Raspberry Pi\\Pico SDK v1.5.1\\python\\python.exe\").")
        sys.exit("o arduino-cli nao tem o core arduino:avr "
                 "(arduino-cli core install arduino:avr)." + dica)
    saida_dir = os.path.join(tmp, "arduino")
    r = subprocess.run([ARDUINO_CLI, "compile", "-b", "arduino:avr:uno", "--warnings", "all",
                        "--output-dir", saida_dir, os.path.join(RAIZ, "cronometro-arduino")],
                       capture_output=True, text=True, errors="replace")
    texto = r.stdout + r.stderr
    if r.returncode != 0:
        sys.exit("arduino-cli falhou:\n" + texto[-4000:])
    avisos = [l for l in texto.splitlines()
              if "warning" in l.lower() and "cronometro-arduino.ino" in l]
    if avisos:
        sys.exit("aviso de compilacao no sketch:\n" + "\n".join(avisos))
    m = re.search(r"Sketch uses (\d+) bytes", texto)
    print(f"  sketch: {m.group(1) if m else '?'} bytes de programa")
    arquivos = []
    for ext in ("hex", "elf"):
        c = os.path.join(saida_dir, f"cronometro-arduino.ino.{ext}")
        if not os.path.exists(c):
            sys.exit(f"o arduino-cli nao gerou {os.path.basename(c)}")
        arquivos.append((f"build/cronometro-arduino.ino.{ext}", c))
    return arquivos

# --------------------------------------------------------------------- PNG
def renderiza_png(svg_repo, tmp):
    origem = os.path.join(RAIZ, *svg_repo.split("/"))
    texto = io.open(origem, encoding="utf-8").read()
    m = re.search(r'<svg[^>]*\swidth="(\d+)"\s+height="(\d+)"', texto)
    if not m:
        sys.exit(f"sem width/height em {svg_repo}")
    if not os.path.exists(EDGE):
        sys.exit(f"Edge nao encontrado: {EDGE} (defina EDGE)")
    copia = os.path.join(tmp, os.path.basename(origem))          # caminho so ASCII
    shutil.copyfile(origem, copia)
    png = copia[:-4] + ".png"
    perfil = tempfile.mkdtemp(prefix="edge-", dir=tmp)
    escala = 2                                                      # nitido impresso
    # O msedge.exe entrega o trabalho a um processo filho e volta na hora, antes
    # de o PNG existir: esperar o arquivo aparecer e parar de crescer. Saida
    # para DEVNULL, nao capturada, que o filho herdaria o pipe.
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--force-device-scale-factor={escala}",
                    f"--user-data-dir={perfil}", f"--screenshot={png}",
                    f"--window-size={m.group(1)},{m.group(2)}",
                    "file:///" + copia.replace("\\", "/")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    anterior, prazo = -1, time.time() + 120
    while time.time() < prazo:
        atual = os.path.getsize(png) if os.path.exists(png) else -1
        if atual > 0 and atual == anterior:
            break
        anterior = atual
        time.sleep(1)
    else:
        sys.exit(f"o Edge nao gerou o PNG de {svg_repo}")
    with open(png, "rb") as f:
        cab = f.read(24)
    largura, altura = struct.unpack(">II", cab[16:24])             # IHDR
    if cab[:8] != b"\x89PNG\r\n\x1a\n" or (largura, altura) != (
            int(m.group(1)) * escala, int(m.group(2)) * escala):
        sys.exit(f"PNG de {svg_repo} saiu com {largura}x{altura}, nao {escala}x o SVG")
    return png

# ------------------------------------------------------------------ LEIA-ME
LICENCA_TXT = """LICENÇA
  Software: GPL-3.0-or-later (LICENSE). Hardware — kicad/, diagramas, bom.md e
  pinout.md: CERN-OHL-S-2.0 (LICENSE-HARDWARE.txt). Detalhe em NOTICE.
  Copyright (C) 2026 Leonardo Roman da Rosa.
"""

def leia_me_pico(tag):
    return f"""CRONÔMETRO HOT WHEELS — 6 RAIAS
Versão Raspberry Pi Pico / RP2040 · release {tag}
{REPO}

O QUE TEM AQUI
  binarios/                 firmware pronto para gravar (4 variantes, passo 3)
  docs/fiacao-pico.png      diagrama de fiação: é o que se segue na montagem
  docs/fiacao-pico.svg      o mesmo diagrama, em vetor
  docs/bom.md               material e cuidados elétricos — leia antes de soldar
  docs/pinout.md            pinagem, com a posição do furo na Pico e na RP2040 roxa
  docs/esquema-kicad.pdf    esquema elétrico (o projeto KiCad 10 está em kicad/)
  docs/como-simular.md      como rodar tudo no simulador Wokwi antes de montar
  build/                    o firmware padrão onde o simulador do VS Code procura
  src/, CMakeLists.txt      código-fonte, para recompilar (Pico SDK 1.5.1)
  README.md                 documentação completa

MONTAGEM, EM ORDEM

1. Material (docs/bom.md). Três cuidados antes de comprar e soldar:
   - Tudo em 3,3 V, displays E sensores. O TM1637 e o TCRT5000 têm pull-up
     para o próprio VCC: alimentados em 5 V, põem 5 V num pino do RP2040, que
     não tolera.
   - Consumo: seis displays e seis sensores chegam perto do limite do 3V3 da
     Pico. O recomendado é um regulador 3,3 V separado (AMS1117-3.3), com o
     GND em comum com a placa.
   - O TCRT5000 é refletivo: monte por baixo da pista, olhando para cima, com
     o fundo do carro passando a 2 a 5 mm.

2. Fiação (docs/fiacao-pico.png). Os nomes no diagrama são GPIO. Na RP2040
   roxa a posição do furo é outra: confira em docs/pinout.md antes de soldar.

3. Gravar. Segure o BOOTSEL, ligue o USB e arraste UM .uf2 de binarios/ para
   o drive RPI-RP2. Comece pelo padrão; os passos 4 e 5 dizem se é preciso
   trocar.
     cronometro-rasp-pico-{tag}.uf2
         padrão: display com dois-pontos central, sensor ativo em 0
     cronometro-rasp-pico-{tag}-ponto-decimal.uf2
         display com um ponto embaixo de cada dígito (o tempo sai 3.721)
     cronometro-rasp-pico-{tag}-sensor-invertido.uf2
         lote de TCRT5000 que aciona ao contrário
     cronometro-rasp-pico-{tag}-ponto-decimal-sensor-invertido.uf2
         as duas coisas

4. Primeira vez ligado: cada display acende TUDO e depois mostra o número da
   própria raia.
   - Display apagado, ou com o número de outra raia: é o fio DIO dele.
   - Apareceu um ponto embaixo de cada dígito? Grave o "-ponto-decimal". Se só
     acenderam os dois pontinhos do meio, fique com o padrão.

5. Sensores. O LED de saída de cada TCRT5000 tem que acender com o carro em
   cima e apagar sem ele; se for o contrário, grave o "-sensor-invertido".
   Ajuste os seis trimpots com o MESMO carro. Com a prova armada, segurar um
   carrinho sobre o sensor da raia 1 por 2 s roda a corrida demo.

6. Uso. Fechar a porta arma; abrir larga. Cada display mostra a colocação
   quando o carro cruza e, no fim, alterna colocação e tempo. Botão TESTE
   (opcional): um toque rearma, segurar 1 s roda a demo. Os tempos também
   saem no USB, como porta serial.

{LICENCA_TXT}"""

def leia_me_arduino(tag):
    return f"""CRONÔMETRO HOT WHEELS — 6 RAIAS
Versão Arduino UNO / Nano · release {tag}
{REPO}

O QUE TEM AQUI
  cronometro-arduino.ino    o firmware, num arquivo só
  docs/fiacao-arduino.png   diagrama de fiação: é o que se segue na montagem
  docs/fiacao-arduino.svg   o mesmo diagrama, em vetor
  docs/bom.md               material e cuidados elétricos — leia antes de soldar
  docs/pinout.md            pinagem e as amarrações que não dá para mudar
  docs/esquema-kicad.pdf    esquema elétrico (o projeto KiCad 10 está em kicad/)
  docs/como-simular.md      como rodar no Wokwi antes de montar — no wokwi.com
                            não precisa instalar nada
  build/                    o .hex que o simulador do VS Code carrega
  README.md                 documentação completa

MONTAGEM, EM ORDEM

1. Material (docs/bom.md). Aqui tudo vai em 5 V: displays e sensores direto no
   5 V da placa. Alimente pelo USB — pelo conector DC de 12 V o regulador do UNO
   esquenta com seis displays e seis sensores. O TCRT5000 é refletivo: monte
   por baixo da pista, olhando para cima, com o fundo do carro a 2 a 5 mm.

2. Fiação (docs/fiacao-arduino.png). Duas amarrações que não dá para mudar:
   - os sensores vão em A0..A5, NESTA ORDEM (raia 1 em A0);
   - a porta de largada vai em D2.

3. Gravar. Abra cronometro-arduino.ino no Arduino IDE (ele precisa estar numa
   pasta chamada cronometro-arduino, como já está aqui), escolha a placa —
   Arduino Uno ou Arduino Nano — e a porta, e clique em Upload.

4. Primeira vez ligado: cada display acende TUDO e depois mostra o número da
   própria raia.
   - Display apagado, ou com o número de outra raia: é o fio DIO dele.
   - Apareceu um ponto embaixo de cada dígito? No topo do .ino, mude
     DISPLAY_PONTO_DECIMAL para 1 e grave de novo. Se só acenderam os dois
     pontinhos do meio, deixe 0.

5. Sensores. O LED de saída de cada TCRT5000 tem que acender com o carro em
   cima e apagar sem ele; se for o contrário, mude SENSOR_NIVEL_CARRO para 1
   no topo do .ino. Ajuste os seis trimpots com o MESMO carro. Com a prova
   armada, segurar um carrinho sobre o sensor da raia 1 por 2 s roda a corrida
   demo.

6. Uso. Fechar a porta arma; abrir larga. Cada display mostra a colocação
   quando o carro cruza e, no fim, alterna colocação e tempo. Botão TESTE
   (opcional): um toque rearma, segurar 1 s roda a demo. Os tempos também saem
   no Monitor Serial, a 115200.

{LICENCA_TXT}"""

# ------------------------------------------------------------------ pacote
def empacota(pasta, mapa, gerados, leia_me, nome_zip, tag, dist):
    existentes = set(mapa.values()) | {pkg for pkg, _ in gerados} | {"LEIA-ME.txt"}
    dirs = {}
    for repo, pkg in mapa.items():
        if not repo.startswith(pasta + "/"):
            continue                         # so a pasta da placa vira diretorio do pacote
        r, p = posixpath.dirname(repo), posixpath.dirname(pkg)
        while True:
            dirs[r] = p
            if not p:
                break
            r, p = posixpath.dirname(r), posixpath.dirname(p)
    existentes |= set(dirs.values())

    arq = os.path.join(dist, nome_zip)
    with zipfile.ZipFile(arq, "w", zipfile.ZIP_DEFLATED) as z:
        # BOM e CRLF: o LEIA-ME e o arquivo que se abre com dois cliques no Windows
        z.writestr(f"{pasta}/LEIA-ME.txt",
                   ("\ufeff" + leia_me.replace("\n", "\r\n")).encode("utf-8"))
        for repo, pkg in sorted(mapa.items(), key=lambda kv: kv[1]):
            origem = os.path.join(RAIZ, *repo.split("/"))
            if not os.path.isfile(origem):
                sys.exit(f"falta no repositorio: {repo}")
            if pkg.endswith(".md"):
                t = io.open(origem, encoding="utf-8").read()
                t = reescreve_links(t, repo, pkg, mapa, dirs, tag, existentes)
                if pkg == "README.md":
                    t = nota_no_readme(t, tag)
                z.writestr(f"{pasta}/{pkg}", t.encode("utf-8"))
            else:
                z.write(origem, f"{pasta}/{pkg}")
        for pkg, caminho in gerados:
            z.write(caminho, f"{pasta}/{pkg}")

    with zipfile.ZipFile(arq) as z:
        for i in z.infolist():
            print(f"    {i.file_size:>9}  {i.filename}")
    sha = hashlib.sha256(open(arq, "rb").read()).hexdigest()
    print(f"  => {nome_zip}  {os.path.getsize(arq)} bytes  sha256 {sha}\n")

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", args[0]):
        sys.exit("uso: python tools/empacotar_release.py X.Y.Z [--permitir-sujo]")
    versao = args[0]
    tag = "v" + versao
    sujo = subprocess.run(["git", "-C", RAIZ, "status", "--porcelain"],
                          capture_output=True, text=True).stdout.strip()
    if sujo and "--permitir-sujo" not in sys.argv:
        sys.exit("ha mudancas nao commitadas; o release tem que sair de um commit:\n" + sujo)

    dist = os.path.join(RAIZ, "dist")
    os.makedirs(dist, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="release-")
    try:
        print("Pico: compilando as variantes")
        uf2, simulador = compila_variantes_pico(versao, tmp)
        png = renderiza_png("cronometro-rasp-pico/docs/fiacao-pico.svg", tmp)
        pasta, mapa = arquivos_pico()
        empacota(pasta, mapa, uf2 + simulador + [("docs/fiacao-pico.png", png)],
                 leia_me_pico(tag), f"cronometro-hotwheels-rasp-pico-{tag}.zip", tag, dist)

        print("Arduino: compilando o sketch")
        simulador = compila_arduino(tmp)
        png = renderiza_png("cronometro-arduino/docs/fiacao-arduino.svg", tmp)
        pasta, mapa = arquivos_arduino()
        empacota(pasta, mapa, simulador + [("docs/fiacao-arduino.png", png)],
                 leia_me_arduino(tag), f"cronometro-hotwheels-arduino-{tag}.zip", tag, dist)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
