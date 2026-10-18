<div align="center">

# Folder Galaxy

**Una costellazione 3D, in tempo reale, delle tue cartelle e dei tuoi file.**
Ogni progetto diventa una galassia, ogni cartella un ramo, ogni file una stella, e tutto si aggiorna mentre lavori.

[![tests](https://github.com/tobiagola-hue/folder-galaxy/actions/workflows/tests.yml/badge.svg)](https://github.com/tobiagola-hue/folder-galaxy/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-3776ab?logo=python&logoColor=white)
![Dipendenze](https://img.shields.io/badge/dipendenze-nessuna-brightgreen)
![Docker](https://img.shields.io/badge/docker-amd64%20%7C%20arm64%20%7C%20armv7-2496ed?logo=docker&logoColor=white)
[![Licenza: MIT](https://img.shields.io/badge/licenza-MIT-yellow)](LICENSE)

[Avvio rapido](#avvio-rapido) · [Installazione per dispositivo](#installazione-sul-tuo-dispositivo) · [Impostazioni](#impostazioni) · [Domande frequenti](#domande-frequenti) · [English](README.md)

<img src="docs/images/demo.gif" alt="Folder Galaxy: i file nuovi compaiono con un lampo bianco, quelli cancellati lampeggiano di rosso, il pannello attività si aggiorna dal vivo" width="900">

</div>

---

## Cos'è

Folder Galaxy è una piccola web app che trasforma una cartella (i tuoi progetti, la tua home, un singolo repository) in una mappa 3D interattiva da aprire nel browser.

È nata per un **server di casa senza schermo**: il server sorveglia la cartella e tu la guardi da portatile, tablet o telefono. Ogni modifica compare in tempo reale, senza ricaricare né rilanciare niente: i file nuovi appaiono, quelli cancellati spariscono, le cartelle più attive si illuminano.

È **un solo file Python, senza dipendenze**, quindi parte in pochi secondi anche su Mac, PC Windows o Raspberry Pi.

## Caratteristiche

**Dal vivo**
- **Aggiornamenti in tempo reale.** File creati, modificati o cancellati compaiono in pochi secondi, inviati alla pagina con Server-Sent Events. Viaggiano solo le differenze.
- **Pannello attività.** Le ultime creazioni, modifiche e cancellazioni sono in un elenco: clic per volarci sopra.
- **Mappa di calore.** I file modificati da poco sono più luminosi, quelli fermi da mesi si spengono.

**Visuale**
- **Layout a galassie.** Ogni cartella di primo livello è una galassia, e al suo interno l'albero cresce verso l'esterno come un ramo: i file della stessa cartella restano insieme.
- **Colori con un significato.** Le cartelle prendono il colore della loro galassia, i file quello del tipo (Python, JS/TS, web, altro codice, config, documenti, dati, log, media).
- **Dimensioni con un significato.** Per le cartelle conta quanti file contengono, per i file quanto pesano.
- **Disposizione stabile.** La stessa cartella produce sempre la stessa costellazione, così impari dove sta ogni cosa.

**Navigazione**
- **Scegli qualsiasi cartella** dalla pagina: barra del percorso con suggerimenti, ↑ per salire, percorso cliccabile, **Entra ›** per entrare in una cartella, e i tasti avanti/indietro del browser. Ogni vista ha il suo indirizzo, quindi la puoi salvare nei preferiti.
- **Ricerca** per nome (`/` per iniziare, `Invio` per volare sul primo risultato).
- **Clic per aprire o chiudere** una cartella. Quelle con più di 120 elementi partono chiuse.
- **Telecamera che vola** sugli elementi, rotazione automatica, etichette per tutte le cartelle e "inquadra tutto" con un clic.

**Sicura per costruzione**
- **Sola lettura.** Legge solo nomi, dimensioni e date, mai il contenuto dei file, e non scrive mai nulla.
- **Recinto.** La pagina non può uscire dalla cartella consentita (`BROWSE_ROOT`). I collegamenti simbolici vengono risolti prima del controllo e mai seguiti durante la scansione.
- **Privata di default.** Avviata a mano, ascolta solo su `127.0.0.1`. Decidi tu quando aprirla alla rete.

**Funziona ovunque**
- **Zero dipendenze.** Solo libreria standard di Python. Il motore 3D è incluso, quindi la pagina funziona anche senza internet.
- **Immagine Docker** per `amd64`, `arm64` e `armv7` (PC, Mac con Apple silicon, Raspberry Pi, NAS).
- Linux, macOS e Windows, nel browser da computer e da telefono, in italiano e inglese (scelti in automatico).
- **Leggera.** Una cartella viene sorvegliata solo mentre una pagina la mostra, e quelle enormi vengono controllate meno spesso.

## Immagini

| Panoramica | Una galassia da vicino, con etichette |
|---|---|
| <img src="docs/images/hero.png" alt="Panoramica di tutti i progetti"> | <img src="docs/images/galaxy.png" alt="Galassia di un progetto con etichette"> |
| **La ricerca evidenzia i risultati** | **Dentro un singolo progetto** |
| <img src="docs/images/search.png" alt="Risultati di ricerca evidenziati"> | <img src="docs/images/navigate.png" alt="Dentro un progetto, con il percorso"> |

<p align="center">
  <img src="docs/images/mobile.png" alt="Vista da telefono" width="230">
  &nbsp;&nbsp;
  <img src="docs/images/mobile-menu.png" alt="Vista da telefono con il menu aperto" width="230">
  <br><sub>Da telefono: trascina per ruotare, pizzica per lo zoom, menu richiudibile.</sub>
</p>

---

## Avvio rapido

Serve **Python 3.9+** (già presente su quasi tutti i Linux e Mac) oppure **Docker**.

**Opzione A: avvialo e basta**

```bash
git clone https://github.com/tobiagola-hue/folder-galaxy.git
cd folder-galaxy
python3 server.py ~/projects --open
```

Si apre il browser su <http://localhost:8765>. Al posto di `~/projects` puoi mettere qualsiasi cartella; senza, parte dalla tua home.

**Opzione B: Docker Compose** (ideale per un server sempre acceso)

```bash
git clone https://github.com/tobiagola-hue/folder-galaxy.git
cd folder-galaxy
cp .env.example .env        # poi imposta BROWSE_ROOT e DEFAULT_ROOT
docker compose up -d --build
```

Apri `http://<ip-del-server>:8765`. Ripartirà da solo a ogni riavvio.

**Opzione C: un solo `docker run`** con l'immagine già pronta

```bash
docker run -d --name folder-galaxy --restart unless-stopped -p 8765:8765 \
  -v "$HOME:$HOME:ro" -e BROWSE_ROOT="$HOME" -e DEFAULT_ROOT="$HOME/projects" -e HOME="$HOME" \
  ghcr.io/tobiagola-hue/folder-galaxy:latest
```

> Non usi git? Scarica lo ZIP dal pulsante verde **Code** su GitHub e scompattalo. Il resto è identico.

---

## Installazione sul tuo dispositivo

<details open>
<summary><b>Server Linux senza schermo / homelab (Docker)</b>, l'uso per cui è nata</summary>

1. Copia il progetto sul server, con `git clone` oppure copiando la cartella via SSH:
   ```bash
   scp -r folder-galaxy utente@server:~/
   ```
2. Sul server, crea il file delle impostazioni:
   ```bash
   cd ~/folder-galaxy
   cp .env.example .env
   nano .env
   ```
   ```ini
   BROWSE_ROOT=/home/utente            # la pagina non può mai uscire da qui
   DEFAULT_ROOT=/home/utente/projects  # cartella mostrata all'apertura
   ```
3. Avvialo:
   ```bash
   docker compose up -d --build
   docker compose logs -f              # cerca "Folder Galaxy ... start folder ..."
   ```
4. Da qualsiasi dispositivo della rete apri `http://<ip-del-server>:8765`. L'IP lo trovi con `hostname -I`.

La cartella è montata **in sola lettura** con lo stesso percorso, così nella pagina vedi i percorsi veri. Per aggiornare: `git pull && docker compose up -d --build`.
</details>

<details>
<summary><b>Server Linux senza Docker (systemd)</b></summary>

```bash
git clone https://github.com/tobiagola-hue/folder-galaxy.git ~/folder-galaxy
# prima modifica YOURUSER e i percorsi nel file del servizio
sudo cp ~/folder-galaxy/contrib/folder-galaxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now folder-galaxy
journalctl -u folder-galaxy -f
```

Il servizio avvia `server.py ... --host 0.0.0.0`, quindi si apre anche dagli altri dispositivi.
</details>

<details>
<summary><b>macOS</b></summary>

```bash
git clone https://github.com/tobiagola-hue/folder-galaxy.git
cd folder-galaxy
python3 server.py ~/Developer --open
```

- Se `python3` manca, macOS propone di installare gli Strumenti da riga di comando. In alternativa: `brew install python`.
- La prima volta che legge `Scrivania`, `Documenti` o `Download`, macOS può chiedere di autorizzare il Terminale. È normale.
- `~/Library` viene saltata di default perché è enorme e poco interessante da vedere.
</details>

<details>
<summary><b>Windows</b></summary>

Installa Python da [python.org](https://www.python.org/downloads/) (spunta *"Add python.exe to PATH"*) o dal Microsoft Store, poi in PowerShell:

```powershell
git clone https://github.com/tobiagola-hue/folder-galaxy.git
cd folder-galaxy
py server.py "$env:USERPROFILE\projects" --open
```

I percorsi si possono scrivere sia `C:\Users\io\projects` sia `C:/Users/io/projects`. `AppData` e il cestino vengono saltati di default.
</details>

<details>
<summary><b>Raspberry Pi</b></summary>

Raspberry Pi OS ha già Python 3:

```bash
git clone https://github.com/tobiagola-hue/folder-galaxy.git
cd folder-galaxy
python3 server.py ~/projects --host 0.0.0.0
```

Oppure usa Docker (l'immagine supporta `arm64` e `armv7`). Per farlo partire all'accensione senza Docker, usa il servizio systemd qui sopra.
</details>

<details>
<summary><b>NAS (Synology, Unraid, TrueNAS, …)</b></summary>

Usa **Container Manager / Docker Compose** con il `docker-compose.yml` incluso, oppure con questo minimo:

```yaml
services:
  folder-galaxy:
    image: ghcr.io/tobiagola-hue/folder-galaxy:latest
    restart: unless-stopped
    ports: ["8765:8765"]
    volumes: ["/volume1/projects:/volume1/projects:ro"]
    environment:
      BROWSE_ROOT: /volume1/projects
      DEFAULT_ROOT: /volume1/projects
```
</details>

<details>
<summary><b>Aprirla dal telefono o da fuori casa</b></summary>

- **Stessa Wi-Fi:** avvia con `--host 0.0.0.0` (Docker lo fa già) e apri `http://<ip-del-computer>:8765`.
- **Da ovunque:** usa una rete privata come [Tailscale](https://tailscale.com/) o WireGuard e apri `http://<ip-tailscale>:8765`. **Non** esporre la porta direttamente su internet: per scelta non c'è login.
- **Dietro un reverse proxy:** con nginx funziona così com'è (il flusso live invia `X-Accel-Buffering: no`). Con altri proxy, disattiva il buffering per `/api/events`.
</details>

---

## Uso della pagina

| Azione | Mouse / tastiera | Touch |
|---|---|---|
| Ruotare | trascina | trascina con un dito |
| Zoom | rotellina | pizzica |
| Spostare | trascina col tasto destro | trascina con due dita |
| Aprire / chiudere una cartella | clic | tocco |
| Dettagli, Vola qui, Entra › | clic su un nodo | tocco su un nodo |
| Cercare | `/`, poi scrivi; `Invio` vola sul primo risultato | casella di ricerca |
| Togliere selezione / ricerca | `Esc` | × |
| Cambiare cartella | barra del percorso, ↑, percorso cliccabile, indietro del browser | uguale |

**Come leggere la mappa**

| Vedi | Significa |
|---|---|
| Una galassia | una cartella di primo livello della vista attuale |
| Sfera di cartella più grande | più file dentro |
| Sfera di file più grande | file più pesante |
| Colore del file | tipo di file (vedi *Tipi di file* nel pannello) |
| Stella più luminosa | modificato negli ultimi 20 minuti |
| Stella più spenta | fermo da più di 60 giorni |
| Lampo bianco | file nuovo o modificato |
| Lampo rosso | file cancellato |
| `▸ nome (123)` | cartella chiusa: clic per aprirla |

**Come funziona il layout.** È una simulazione fisica. I collegamenti fanno da molle e tengono i figli vicini alla loro cartella. Una forza "ramo" fa crescere ogni cartella lontano dal suo genitore, così i fratelli stanno dallo stesso lato. Una forza "galassia" misura la nuvola di ogni cartella di primo livello e allontana quelle che si sovrappongono, mentre la radice resta ferma al centro. Le posizioni di partenza derivano da un hash di ogni percorso, quindi la stessa cartella dà sempre la stessa immagine.

---

## Impostazioni

Ogni impostazione si può passare come opzione da riga di comando o come variabile d'ambiente (Docker le legge da `.env`).

| Opzione | Variabile d'ambiente | Default | Cosa fa |
|---|---|---|---|
| `ROOT` (posizionale) | `DEFAULT_ROOT` | la tua home | Cartella mostrata all'apertura |
| `--browse-root` | `BROWSE_ROOT` | la tua home (o `ROOT`, se è fuori dalla home) | La pagina non può mai uscire da qui |
| `--host` | `HOST` | `127.0.0.1` (`0.0.0.0` in Docker) | Indirizzo di ascolto; `0.0.0.0` permette gli altri dispositivi |
| `--port` | `PORT` | `8765` | Porta |
| `--interval` | `SCAN_INTERVAL` | `3` | Secondi tra un controllo e l'altro; le cartelle grandi rallentano da sole |
| `--max-nodes` | `MAX_NODES` | `30000` | Limite di sicurezza sugli elementi per vista |
| `--exclude-extra` | `EXCLUDE_EXTRA` | – | Altri nomi da ignorare, separati da virgola, con caratteri jolly (`data,*.tmp`) |
| – | `EXCLUDE` | vedi sotto | Sostituisce del tutto l'elenco delle esclusioni |
| `--open` | – | no | Apre il browser all'avvio |

**Ignorati di default:** `.git`, `.hg`, `.svn`, `node_modules`, `venv`, `.venv`, `__pycache__`, `*.pyc`, cache degli strumenti (`.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.tox`, `.gradle`, `.m2`, `.next`, `.nuxt`, `site-packages`), cartelle degli editor (`.idea`, `.vscode`, `.vscode-server`, `.cursor-server`) e le cose pesanti della home (`.cache`, `.local`, `.npm`, `.nvm`, `.pyenv`, `.cargo`, `.rustup`, `.conda`, `miniconda3`, `anaconda3`, `snap`, `.docker`, `.Trash`, `Library`, `AppData`, `$RECYCLE.BIN`, `System Volume Information`, `.DS_Store`).

Puoi anche forzare la lingua aggiungendo `?lang=it` o `?lang=en` all'indirizzo.

---

## Sicurezza e privacy

- **Sola lettura, solo metadati.** Vengono letti solo nomi, dimensioni e date di modifica. Il contenuto dei file non viene mai aperto.
- **Recinto.** Ogni percorso richiesto viene risolto (`realpath`, quindi `..` e collegamenti simbolici sono gestiti) e rifiutato se è fuori da `BROWSE_ROOT`. Le cartelle collegate simbolicamente si vedono ma non si entra mai.
- **Docker.** La cartella è montata con `:ro` e il container ha un limite di memoria.
- **Niente login.** Chi raggiunge la porta può vedere i nomi dentro `BROWSE_ROOT`. Tienila su `127.0.0.1`, in rete locale o in una VPN come Tailscale, e non aprirla su internet.
- **Niente telemetria, nessuna richiesta esterna.** Il motore 3D è incluso.

## Prestazioni

- Una scansione di ~2.000 elementi richiede pochi millisecondi; ~30.000 elementi circa 0,2 s su una CPU moderna (comunque ben sotto il secondo su un piccolo mini PC).
- Se una scansione diventa lenta, l'intervallo si allunga da solo (a 5 volte il tempo di scansione), così le cartelle enormi non occupano la CPU.
- Una cartella viene sorvegliata solo finché almeno una pagina la mostra. Un minuto dopo la chiusura dell'ultima, il controllo si ferma.
- Nel browser, qualche migliaio di nodi visibili scorre fluido su portatili e telefoni recenti. Per alberi giganti usa **Comprimi**, `EXCLUDE_EXTRA` o `MAX_NODES`.

## API

Utile se vuoi costruirci sopra. Tutte le chiamate sono `GET`:

| Indirizzo | Restituisce |
|---|---|
| `/api/check?root=PERCORSO` | `{ok, path, error, base, default, version}`. Valida una cartella (`error`: `outside`, `missing`, `denied`) |
| `/api/dirs?path=PERCORSO` | Sottocartelle di una cartella (per i suggerimenti) |
| `/api/tree?root=PERCORSO` | Fotografia JSON completa della cartella |
| `/api/events?root=PERCORSO` | Flusso Server-Sent Events: uno `snapshot`, poi eventi `diff` con `added`, `removed`, `changed` |
| `/health` | `ok` |

Ogni nodo è `{id, p, n, t, s, m, f, e}`: percorso relativo, id del genitore, nome, tipo (`d`/`f`), byte, data di modifica, numero di file (per le cartelle) e flag di non leggibile.

## Sviluppo

```
folder-galaxy/
├── server.py                 # tutto il backend (solo libreria standard)
├── static/
│   ├── index.html            # tutto il frontend (HTML + CSS + JS)
│   └── 3d-force-graph.min.js # motore 3D incluso
├── tests/test_server.py      # test unitari e HTTP
├── Dockerfile, docker-compose.yml, .env.example
├── contrib/folder-galaxy.service
└── .github/workflows/        # test su Linux/macOS/Windows, immagine Docker multi-architettura
```

```bash
python3 -m unittest discover -s tests -v      # esegue i test
python3 server.py . --interval 1 --open       # ci lavori mentre guarda se stesso
```

Segnalazioni e pull request sono benvenute. Qualche idea: temi, un "time-lapse" dell'ultima ora, colori per lo stato git, filtri per dimensione/età, l'uso del disco come anelli.

---

## Domande frequenti

<details>
<summary><b>Perché due cartelle dello stesso progetto non sono vicine?</b></summary>
Lo sono. Ogni cartella cresce verso l'esterno dal suo genitore, quindi i fratelli stanno dallo stesso lato. In 3D due galassie possono sembrare sovrapposte solo perché una è dietro l'altra: ruota un po' la vista.
</details>

<details>
<summary><b>La pagina dice "Puoi scegliere solo cartelle dentro …".</b></summary>
È il recinto. Avvia il server con un <code>--browse-root</code> (o <code>BROWSE_ROOT</code>) più ampio, e con Docker ricordati di montare anche quella cartella (<code>docker-compose.yml</code> lo fa da solo leggendo <code>.env</code>).
</details>

<details>
<summary><b>Dal telefono non si apre.</b></summary>
Avvia con <code>--host 0.0.0.0</code> (Docker lo fa già), usa l'IP del computer e non <code>localhost</code>, e controlla il firewall (<code>sudo ufw allow 8765/tcp</code> su Ubuntu; su Windows consenti Python quando te lo chiede).
</details>

<details>
<summary><b>"cannot listen on …:8765"</b></summary>
La porta è già occupata. Avvia con <code>--port 8790</code>, oppure imposta <code>PORT=8790</code> in <code>.env</code>.
</details>

<details>
<summary><b>Il pallino è rosso e dice "riconnessione…".</b></summary>
Il server è fermo o la macchina non è raggiungibile. La pagina si ricollega da sola appena torna disponibile.
</details>

<details>
<summary><b>Una cartella dice "Ci sono più di 30.000 elementi".</b></summary>
Aumenta <code>MAX_NODES</code>, o meglio escludi la parte rumorosa (<code>EXCLUDE_EXTRA=data,backups</code>) oppure apri una sottocartella.
</details>

<details>
<summary><b>Funziona con i dischi di rete?</b></summary>
Sì, se la cartella è montata e leggibile. I dischi di rete sono più lenti da scansionare, e l'intervallo si adatta da solo.
</details>

---

## Riconoscimenti

- Rendering 3D con [3d-force-graph](https://github.com/vasturiano/3d-force-graph) (MIT) di Vasco Asturiano, basato su [three.js](https://threejs.org/) e [d3-force-3d](https://github.com/vasturiano/d3-force-3d). Vedi [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- Costruito con tanto aiuto da [Claude](https://claude.ai).

## Licenza

[MIT](LICENSE). Fanne quello che vuoi, una stella fa sempre piacere.
