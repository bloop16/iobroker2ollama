# iobroker2ollama
gives Ollama the possibility to check for decided iobroker datapoints
# ioBroker Ollama RAG Integration

Dieses Projekt ermöglicht die Integration von ioBroker-Daten mit einem lokalen Ollama Large Language Model (LLM) unter Verwendung eines Retrieval Augmented Generation (RAG) Ansatzes. Änderungen an ausgewählten ioBroker-Datenpunkten werden erfasst, in einer Vektordatenbank (ChromaDB) gespeichert und können dann über ein Tool von einem LLM (z.B. über Open Web UI) abgefragt werden, um kontextbezogene Antworten zu Smart-Home-Ereignissen zu erhalten.

## Komponentenübersicht

1.  **`ollama export.js`**: Ein ioBroker JavaScript, das auf Änderungen ausgewählter Datenpunkte lauscht und diese an das `ollama_rag.py`-Skript sendet.
2.  **`ollama_rag.py`**: Ein Python Flask-Server, der Daten vom ioBroker-Skript empfängt, Text-Embeddings mit Ollama generiert, die Daten in ChromaDB speichert UND eine OpenAPI-Schnittstelle für ein LLM-Tool bereitstellt. Dieses Tool nimmt eine Benutzeranfrage entgegen, sucht relevante Informationen in ChromaDB und lässt das LLM eine Antwort basierend auf diesen Informationen generieren.
3.  **ChromaDB**: Eine Vektordatenbank zur Speicherung der Embeddings und Metadaten.
4.  **Ollama**: Die Plattform zum Ausführen der lokalen LLMs für Embedding-Generierung und Antwortgenerierung.

## Voraussetzungen

*   **ioBroker**: Eine laufende ioBroker-Instanz mit installiertem JavaScript-Adapter.
*   **Python**: Python 3.8 oder höher.
*   **Ollama**: Eine laufende Ollama-Instanz.
    *   Das Embedding-Modell (Standard: `nomic-embed-text`) muss in Ollama verfügbar sein: `ollama pull nomic-embed-text`
    *   Das Chat-Modell muss in Ollama verfügbar sein.


## Installation und Konfiguration

### 1. ChromaDB (Linux mit systemd)

Diese Anleitung beschreibt die Installation von ChromaDB als Dienst auf einem Linux-System (z.B. Debian) unter Verwendung von `systemd`. Dies ist eine empfohlene Methode für den Betrieb auf einem Server.

**Voraussetzungen für diesen Abschnitt:**
*   Zugriff auf einen Linux-Server mit `sudo`-Rechten.
*   Python 3.x (insbesondere `python3-venv`) und `pip` müssen installiert sein.

**a. Arbeitsverzeichnis erstellen und Python Virtuelle Umgebung vorbereiten**

   1.  **Verzeichnis erstellen und dorthin navigieren:**
       Stellen Sie eine SSH-Verbindung zu Ihrem Server her. Erstellen Sie das Arbeitsverzeichnis (falls nicht vorhanden) und wechseln Sie hinein.
       ````bash
       sudo mkdir -p /opt/ollama_rag
       # Optional: Besitz an Ihren Benutzer übergeben, falls Sie das Verzeichnis als root erstellt haben und als anderer Benutzer weiterarbeiten möchten.
       # sudo chown -R $(whoami):$(whoami) /opt/ollama_rag
       cd /opt/ollama_rag
       ````

   2.  **Python Virtuelle Umgebung erstellen:**
       Es ist sehr empfehlenswert, eine virtuelle Python-Umgebung zu verwenden, um Projekt-Abhängigkeiten zu isolieren.
       ````bash
       # Installieren Sie python3-venv, falls es nicht vorhanden ist 
       sudo apt update
       sudo apt install python3-venv -y

       # Erstellen der virtuellen Umgebung (z.B. venv_ollama_rag)
       python3 -m venv venv_ollama_rag

       # Aktivieren der virtuellen Umgebung
       source venv_ollama_rag/bin/activate
       ````
       Ihre Kommandozeilen-Eingabeaufforderung sollte nun das Präfix `(venv_ollama_rag)` anzeigen.

**b. ChromaDB installieren**

   Mit der aktivierten virtuellen Umgebung installieren Sie ChromaDB:
   ````bash
   pip install chromadb
   ````
   
**d. ChromaDB als Dienst konfigurieren:**
    Ich habe die Anleitung für die Installation von ChromaDB als Dienst unter Debian mit `systemd` vorbereitet. Hier ist der Abschnitt, der in Ihrer README.md-Datei aktualisiert werden soll:

````markdown
// ...existing code...
**b. ChromaDB installieren**

   Mit der aktivierten virtuellen Umgebung installieren Sie ChromaDB:
   ````bash
   pip install chromadb
   ````
   
**d. ChromaDB als systemd-Dienst konfigurieren (Linux)**

   Diese Anleitung beschreibt, wie ChromaDB als `systemd`-Dienst auf einem Debian-basierten Linux-System eingerichtet wird.

   1.  **systemd Service-Datei erstellen:**
       Erstellen Sie eine Datei namens `chromadb.service` im Verzeichnis `/etc/systemd/system/` mit `sudo` und einem Texteditor (z.B. `nano`):
       ````bash
       sudo nano /etc/systemd/system/chromadb.service
       ````

   2.  **Inhalt der Service-Datei:**
       Fügen Sie folgenden Inhalt in die Datei ein. Passen Sie `User`, `Group`, `WorkingDirectory`, den Pfad zur `chroma`-Executable in `ExecStart` und den `--path` für die Datenbankdateien bei Bedarf an.

       ```ini
       [Unit]
       Description=ChromaDB Persistent Vector Store
       After=network.target

       [Service]
       Type=simple
       User=your_linux_user # Ersetzen: Benutzer, unter dem ChromaDB laufen soll (z.B. der Besitzer von /opt/ollama_rag)
       Group=your_linux_group # Ersetzen: Gruppe des Benutzers
       WorkingDirectory=/opt/ollama_rag
       # Pfad zur Chroma-Executable in Ihrer virtuellen Umgebung
       ExecStart=/opt/ollama_rag/venv_ollama_rag/bin/chroma run --path /var/lib/chromadb_data --port 8087
       Restart=always
       RestartSec=5
       StandardOutput=journal
       StandardError=journal

       [Install]
       WantedBy=multi-user.target
       ```
       *   **Wichtige Anpassungen und Vorbereitungen:**
           *   Ersetzen Sie `your_linux_user` und `your_linux_group` mit dem tatsächlichen Benutzernamen und der Gruppe, unter der der Dienst laufen soll. Wenn Sie den Benutzer verwenden, der `/opt/ollama_rag` erstellt hat, stellen Sie sicher, dass dieser Benutzer Schreibrechte auf `/var/lib/chromadb_data` (oder den von Ihnen gewählten Pfad) und `/var/log/` hat. Es ist oft eine gute Praxis, einen dedizierten Benutzer für Dienste zu erstellen.

   3.  **systemd Daemon neu laden:**
       Nachdem Sie die Datei gespeichert haben, laden Sie die systemd-Konfiguration neu, damit die Änderungen wirksam werden:
       ````bash
       sudo systemctl daemon-reload
       ````

   4.  **Dienst starten:**
       Starten Sie den ChromaDB-Dienst:
       ````bash
       sudo systemctl start chromadb.service
       ````

   5.  **Dienststatus überprüfen:**
       Überprüfen Sie, ob der Dienst korrekt gestartet wurde und läuft:
       ````bash
       sudo systemctl status chromadb.service
       ````
       Sie sollten sehen, dass der Dienst `active (running)` ist. Überprüfen Sie auch die Logdateien (`/var/log/chromadb_service.log` und `/var/log/chromadb_service_error.log`) auf Meldungen oder Fehler.

   6.  **Dienst beim Systemstart aktivieren (optional):**
       Wenn der ChromaDB-Dienst bei jedem Systemstart automatisch gestartet werden soll, aktivieren Sie ihn:
       ````bash
       sudo systemctl enable chromadb.service
       ````

   **Hinweise zum systemd-Dienst:**
    *   Um den Dienst zu stoppen: `sudo systemctl stop chromadb.service`
    *   Um den Dienst neu zu starten: `sudo systemctl restart chromadb.service`
    *   Um den automatischen Start zu deaktivieren: `sudo systemctl disable chromadb.service`
    *   Um die Logs des Dienstes live anzuzeigen: `sudo journalctl -f -u chromadb.service`

**e. Konfiguration in Python-Skripten:**
   Der Host und Port für ChromaDB weird in `ollama_rag.py` über Umgebungsvariablen oder Standardwerte konfiguriert (siehe unten). Der Standardport im Skript ist `8087`.

Okay, ich habe die README.md-Datei überarbeitet, sodass Abschnitt 2 sich ausschließlich auf das konsolidierte Skript ollama_rag.py konzentriert und entsprechende Anpassungen in anderen Abschnitten vorgenommen.

Hier sind die vorgeschlagenen Änderungen für Ihre README.md-Datei:

````markdown
// ...existing code...
# Installation und Konfiguration

### 1. ChromaDB (Linux mit systemd)

Diese Anleitung beschreibt die Installation von ChromaDB als Dienst auf einem Linux-System (z.B. Debian) unter Verwendung von `systemd`. Dies ist eine empfohlene Methode für den Betrieb auf einem Server.

**Voraussetzungen für diesen Abschnitt:**
*   Zugriff auf einen Linux-Server mit `sudo`-Rechten.
*   Python 3.x (insbesondere `python3-venv`) und `pip` müssen installiert sein.

**a. Arbeitsverzeichnis erstellen und Python Virtuelle Umgebung vorbereiten**

   1.  **Verzeichnis erstellen und dorthin navigieren:**
       Stellen Sie eine SSH-Verbindung zu Ihrem Server her. Erstellen Sie das Arbeitsverzeichnis (falls nicht vorhanden) und wechseln Sie hinein.
       ````bash
       sudo mkdir -p /opt/ollama_rag
       # Optional: Besitz an Ihren Benutzer übergeben, falls Sie das Verzeichnis als root erstellt haben und als anderer Benutzer weiterarbeiten möchten.
       # sudo chown -R $(whoami):$(whoami) /opt/ollama_rag
       cd /opt/ollama_rag
       ````

   2.  **Python Virtuelle Umgebung erstellen:**
       Es ist sehr empfehlenswert, eine virtuelle Python-Umgebung zu verwenden, um Projekt-Abhängigkeiten zu isolieren.
       ````bash
       # Installieren Sie python3-venv, falls es nicht vorhanden ist 
       sudo apt update
       sudo apt install python3-venv -y

       # Erstellen der virtuellen Umgebung (z.B. venv_ollama_rag)
       python3 -m venv venv_ollama_rag

       # Aktivieren der virtuellen Umgebung
       source venv_ollama_rag/bin/activate
       ````
       Ihre Kommandozeilen-Eingabeaufforderung sollte nun das Präfix `(venv_ollama_rag)` anzeigen.

**b. ChromaDB installieren**

   Mit der aktivierten virtuellen Umgebung installieren Sie ChromaDB:
   ````bash
   pip install chromadb
   ````
   
**d. ChromaDB als systemd-Dienst konfigurieren (Linux)**

   Diese Anleitung beschreibt, wie ChromaDB als `systemd`-Dienst auf einem Debian-basierten Linux-System eingerichtet wird.

   1.  **systemd Service-Datei erstellen:**
       Erstellen Sie eine Datei namens `chromadb.service` im Verzeichnis `/etc/systemd/system/` mit `sudo` und einem Texteditor (z.B. `nano`):
       ````bash
       sudo nano /etc/systemd/system/chromadb.service
       ````

   2.  **Inhalt der Service-Datei:**
       Fügen Sie folgenden Inhalt in die Datei ein. Passen Sie `User`, `Group`, `WorkingDirectory`, den Pfad zur `chroma`-Executable in `ExecStart` und den `--path` für die Datenbankdateien bei Bedarf an.

       ```ini
       [Unit]
       Description=ChromaDB Persistent Vector Store
       After=network.target

       [Service]
       Type=simple
       User=your_linux_user # Ersetzen: Benutzer, unter dem ChromaDB laufen soll (z.B. der Besitzer von /opt/ollama_rag)
       Group=your_linux_group # Ersetzen: Gruppe des Benutzers
       WorkingDirectory=/opt/ollama_rag
       # Pfad zur Chroma-Executable in Ihrer virtuellen Umgebung
       ExecStart=/opt/ollama_rag/venv_ollama_rag/bin/chroma run --path /var/lib/chromadb_data --port 8087
       Restart=always
       RestartSec=5
       StandardOutput=journal
       StandardError=journal

       [Install]
       WantedBy=multi-user.target
       ```
       *   **Wichtige Anpassungen und Vorbereitungen:**
           *   Ersetzen Sie `your_linux_user` und `your_linux_group` mit dem tatsächlichen Benutzernamen und der Gruppe, unter der der Dienst laufen soll. Wenn Sie den Benutzer verwenden, der `/opt/ollama_rag` erstellt hat, stellen Sie sicher, dass dieser Benutzer Schreibrechte auf `/var/lib/chromadb_data` (oder den von Ihnen gewählten Pfad) hat.
           *   Erstellen Sie das Datenverzeichnis, falls es nicht existiert, und weisen Sie die korrekten Berechtigungen zu:
             ````bash
             sudo mkdir -p /var/lib/chromadb_data
             sudo chown your_linux_user:your_linux_group /var/lib/chromadb_data
             ````
             (Ersetzen Sie `your_linux_user:your_linux_group` entsprechend.)

   3.  **systemd Daemon neu laden:**
       Nachdem Sie die Datei gespeichert haben, laden Sie die systemd-Konfiguration neu, damit die Änderungen wirksam werden:
       ````bash
       sudo systemctl daemon-reload
       ````

   4.  **Dienst starten:**
       Starten Sie den ChromaDB-Dienst:
       ````bash
       sudo systemctl start chromadb.service
       ````

   5.  **Dienststatus überprüfen:**
       Überprüfen Sie, ob der Dienst korrekt gestartet wurde und läuft:
       ````bash
       sudo systemctl status chromadb.service
       ````
       Sie sollten sehen, dass der Dienst `active (running)` ist. Die Logs können mit `sudo journalctl -u chromadb.service` eingesehen werden.

   6.  **Dienst beim Systemstart aktivieren (optional):**
       Wenn der ChromaDB-Dienst bei jedem Systemstart automatisch gestartet werden soll, aktivieren Sie ihn:
       ````bash
       sudo systemctl enable chromadb.service
       ````

   **Hinweise zum systemd-Dienst:**
    *   Um den Dienst zu stoppen: `sudo systemctl stop chromadb.service`
    *   Um den Dienst neu zu starten: `sudo systemctl restart chromadb.service`
    *   Um den automatischen Start zu deaktivieren: `sudo systemctl disable chromadb.service`
    *   Um die Logs des Dienstes live anzuzeigen: `sudo journalctl -f -u chromadb.service`

### 2. Python-Skript (`ollama_rag.py`)

Das Python-Skript `ollama_rag.py` ist das Herzstück der Logik. Es empfängt Daten von ioBroker, verarbeitet sie, generiert Embeddings, speichert sie in ChromaDB und stellt einen RAG-Tool-Endpunkt für LLMs bereit.

**a. Virtuelle Umgebung vorbereiten/aktivieren:**
   Wenn Sie das Skript auf derselben Maschine wie den ChromaDB-Dienst (aus Abschnitt 1) ausführen, können Sie dieselbe virtuelle Umgebung (`/opt/ollama_rag/venv_ollama_rag`) verwenden. Stellen Sie sicher, dass sie aktiviert ist:
   ```bash
   source /opt/ollama_rag/venv_ollama_rag/bin/activate
   ```
   Wenn Sie eine separate Umgebung oder eine andere Maschine verwenden:
   ```bash
   # Navigieren Sie zu Ihrem Projektverzeichnis
   # cd /pfad/zu/ihrem/projekt
   python3 -m venv venv_py_script # Oder ein anderer Name
   source venv_py_script/bin/activate
   ```

**b. Abhängigkeiten installieren:**
   Legen Sie das Skript `ollama_rag.py` in Ihrem Arbeitsverzeichnis ab. Erstellen Sie eine Datei `requirements.txt` (oder ergänzen Sie eine bestehende im selben Verzeichnis) mit folgendem Inhalt:
   ```txt
   flask
   flask-cors
   ollama
   chromadb
   python-dotenv
   waitress
   ```
   Installieren Sie die Abhängigkeiten innerhalb der aktivierten virtuellen Umgebung:
   ```bash
   pip install -r requirements.txt
   ```

**c. `ollama_rag.py` Konfiguration:**
   Das Skript wird primär über Umgebungsvariablen konfiguriert. Die Standardwerte sind im Skript definiert, können aber durch Umgebungsvariablen überschrieben werden.

   *   **`CHROMADB_HOST`**: Hostname oder IP-Adresse des ChromaDB-Servers (Standard: `"localhost"`).
   *   **`CHROMADB_PORT`**: Port des ChromaDB-Servers (Standard: `8087`).
   *   **`CHROMADB_COLLECTION_NAME`**: Name der ChromaDB-Collection (Standard: `"iobroker_events"`).
   *   **`OLLAMA_HOST`**: Vollständige URL des Ollama-Servers (Standard: `"http://localhost:11434"`).
   *   **`OLLAMA_EMBEDDING_MODEL`**: Name des Embedding-Modells in Ollama (Standard: `"nomic-embed-text"`).
   *   **`TOOL_LLM_MODEL`**: Name des Chat-Modells in Ollama, das vom RAG-Tool verwendet wird (Standard: `"gemma3:4b"`).
   *   **`FLASK_HOST`**: Host, auf dem der Flask-Server für `ollama_rag.py` lauschen soll (Standard: `"0.0.0.0"`, d.h. auf allen Netzwerkschnittstellen).
   *   **`FLASK_PORT`**: Port für den Flask-Server (Standard: `5000`). Dieser Port wird für den Datenempfang und den Tool-Endpunkt verwendet.
   *   **`FLASK_DEBUG_MODE`**: Flask Debug-Modus aktivieren (`"true"`) oder deaktivieren (`"false"`) (Standard: `"False"`).
   *   **`RAG_N_RESULTS`**: Anzahl der relevantesten Dokumente, die aus ChromaDB für den RAG-Kontext abgerufen werden (Standard: `10`).

   Sie können diese Variablen vor dem Start des Skripts in Ihrer Shell setzen (z.B. `export FLASK_PORT=5005`) oder eine `.env`-Datei im selben Verzeichnis wie `ollama_rag.py` verwenden (dafür sorgt `python-dotenv`, falls es im Skript explizit geladen würde – aktuell nutzt das Skript `os.getenv`, was systemgesetzte Variablen direkt liest).

**d. Python-Skript starten:**
   Stellen Sie sicher, dass Ihre virtuelle Umgebung aktiviert ist und alle Abhängigkeiten installiert sind. Starten Sie das Skript:
   ```bash
   python ollama_rag.py
   ```
   Das Skript verwendet `waitress` als WSGI-Server für den produktiven Einsatz, wenn es direkt ausgeführt wird. Die Startmeldungen im Terminal zeigen an, unter welcher Adresse und Port der Server läuft.

### 3. `ollama export.js` (ioBroker JavaScript)

**a. Installation:**
   1.  Öffne deine ioBroker-Admin-Oberfläche.
   2.  Gehe zum "Skripte"-Adapter.
   3.  Erstelle ein neues JavaScript (nicht Blockly oder TypeScript).
   4.  Kopiere den gesamten Inhalt von `ollama export.js` in dieses neue Skript.

**b. Konfiguration im Skript:**
   Passe die folgenden Konstanten am Anfang des Skripts an:
   *   **`PYTHON_SERVER_URL_BASE`**: Die URL, unter der dein `ollama_rag.py`-Server erreichbar ist. Stelle sicher, dass IP und Port korrekt sind und mit den `FLASK_HOST`- und `FLASK_PORT`-Einstellungen von `ollama_rag.py` übereinstimmen (der Endpunkt ist `/iobroker-event`).
   *   **`TARGET_DATAPOINTS`**: Dies ist die wichtigste Konfiguration. Definiere hier alle ioBroker-Datenpunkte, die du überwachen und an das Python-Skript senden möchtest. Jeder Eintrag ist ein Objekt mit:
        *   `id`: Die vollständige ID des ioBroker-Datenpunkts.
        *   `description`: Eine menschenlesbare Beschreibung, was dieser Datenpunkt repräsentiert.
        *   `type`: Der Datentyp ("boolean", "number", "string", "mixed").
        *   `location` (optional): Der Ort, auf den sich der Datenpunkt bezieht.
        *   `booleanTrueValue` (optional, nur für `type: "boolean"`): Text für den `true`-Zustand (z.B. "anwesend", "offen").
        *   `booleanFalseValue` (optional, nur für `type: "boolean"`): Text für den `false`-Zustand (z.B. "abwesend", "geschlossen").
        *   `unit` (optional, nur für `type: "number"`): Die Einheit des Zahlenwerts (z.B. "°C", "W", "%").

**c. Axios-Modul im JavaScript-Adapter:**
   Das Skript verwendet `axios` für HTTP-Anfragen.
   1.  Gehe in ioBroker zu "Instanzen".
   2.  Finde deine JavaScript-Adapter-Instanz (z.B. `javascript.0`).
   3.  Klicke auf den Schraubenschlüssel (Konfiguration).
   4.  Im Tab "Zusätzliche NPM-Module" (oder ähnlich benannt), füge `axios` hinzu.
   5.  Speichere die Konfiguration. Der Adapter sollte neu starten und das Modul installieren.

**d. Skript starten:**
   Aktiviere und starte das JavaScript in ioBroker. Überprüfe die ioBroker-Logs auf Meldungen vom Skript.

### 4. `iobroker_request.js` (ioBroker JavaScript für direkte Anfragen)

Dieses Skript ermöglicht es, direkt aus ioBroker (z.B. über die Visualisierung oder andere Skripte) eine Anfrage an den RAG-Tool-Endpunkt des `ollama_rag.py`-Servers zu senden und die Antwort in einem ioBroker-Datenpunkt zu empfangen.

**a. Installation:**
   1.  Öffne deine ioBroker-Admin-Oberfläche.
   2.  Gehe zum "Skripte"-Adapter.
   3.  Erstelle ein neues JavaScript.
   4.  Kopiere den gesamten Inhalt von `iobroker_request.js` in dieses neue Skript.

**b. Konfiguration im Skript:**
   Passe die folgenden Konstanten am Anfang des Skripts an:
   *   **`anfrageDatenpunkt`**: Die ID des ioBroker-Datenpunkts, in den die Benutzeranfrage geschrieben wird (Standard: `'0_userdata.0.ollama.Anfrage'`). Das Skript lauscht auf Änderungen dieses Datenpunkts.
   *   **`antwortDatenpunkt`**: Die ID des ioBroker-Datenpunkts, in den die Antwort vom `ollama_rag.py`-Server geschrieben wird (Standard: `'0_userdata.0.ollama.Antwort'`).
   *   **`apiEndpoint`**: Die vollständige URL des RAG-Tool-Endpunkts auf deinem `ollama_rag.py`-Server (Standard: `'http://192.168.0.204:5001/tools/get_iobroker_data_answer'`). Stelle sicher, dass IP, Port und Pfad korrekt sind und mit den `FLASK_HOST`-, `FLASK_PORT`-Einstellungen und dem Routenpfad in `ollama_rag.py` übereinstimmen.

**c. Axios-Modul im JavaScript-Adapter:**
   Dieses Skript verwendet ebenfalls `axios`. Wenn du es bereits für `ollama_export.js` konfiguriert hast, ist kein weiterer Schritt nötig. Andernfalls:
   1.  Gehe in ioBroker zu "Instanzen".
   2.  Finde deine JavaScript-Adapter-Instanz (z.B. `javascript.0`).
   3.  Klicke auf den Schraubenschlüssel (Konfiguration).
   4.  Im Tab "Zusätzliche NPM-Module", füge `axios` hinzu.
   5.  Speichere die Konfiguration. Der Adapter sollte neu starten.

**d. Datenpunkte erstellen (optional, aber empfohlen):**
   Das Skript versucht, die `anfrageDatenpunkt` und `antwortDatenpunkt` zu erstellen, falls sie nicht existieren. Du kannst sie auch manuell unter `0_userdata.0` (oder einem Pfad deiner Wahl, dann musst du die Konstanten im Skript anpassen) mit folgenden Eigenschaften anlegen:
    *   `0_userdata.0.ollama.Anfrage`: Typ `string`, Rolle `text`, Lesen `true`, Schreiben `true`.
    *   `0_userdata.0.ollama.Antwort`: Typ `string`, Rolle `text`, Lesen `true`, Schreiben `false` (wird vom Skript geschrieben).

**e. Skript starten und verwenden:**
   1.  Aktiviere und starte das JavaScript in ioBroker.
   2.  Um eine Anfrage zu senden, schreibe deine Frage in den `anfrageDatenpunkt` (z.B. über ein VIS-Eingabefeld oder ein anderes Skript). Stelle sicher, dass der `ack`-Flag beim Schreiben auf `false` gesetzt ist, damit das Skript die Änderung erkennt.
   3.  Die Antwort vom LLM wird kurz darauf in den `antwortDatenpunkt` geschrieben.
   4.  Überprüfe die ioBroker-Logs auf Meldungen vom Skript, insbesondere bei Fehlern.

### 5. Open Web UI Tool Integration

1.  Starte dein `ollama_rag.py`-Skript. Es stellt eine OpenAPI-Spezifikation unter `http://<FLASK_HOST_VON_OLLAMA_RAG>:<FLASK_PORT_VON_OLLAMA_RAG>/openapi.json` bereit (z.B. `http://localhost:5000/openapi.json`, abhängig von deiner Konfiguration).
2.  Gehe in Open Web UI zu den Einstellungen des Modells, das du verwenden möchtest.
3.  Aktiviere "Tools" und füge die URL zur `openapi.json` deines `ollama_rag.py`-Servers hinzu.
4.  Open Web UI sollte das Tool `getIoBrokerDataAnswer` erkennen.
5.  Wähle das Tool für die Verwendung im Chat aus.

## Workflow

1.  Eine Änderung an einem der in `ollama export.js` konfigurierten ioBroker-Datenpunkte tritt ein.
2.  Das ioBroker-Skript sendet die Datenpunktinformationen (Wert, Beschreibung, Typ, Zeitstempel etc.) an den `/iobroker-event`-Endpunkt des `ollama_rag.py`-Servers.
3.  Das `ollama_rag.py`-Skript erstellt einen beschreibenden Text aus diesen Informationen.
4.  Es generiert mit Ollama (`nomic-embed-text`) ein Embedding für diesen Text.
5.  Der Text, das Embedding und Metadaten werden in der ChromaDB-Collection (`iobroker_events`) gespeichert.
6.  Ein Benutzer stellt eine Frage in Open Web UI (z.B. "Wie warm ist es im Wohnzimmer?").
7.  Open Web UI erkennt, dass die Frage für das `getIoBrokerDataAnswer`-Tool relevant sein könnte und ruft den `/tools/get_iobroker_data_answer`-Endpunkt des `ollama_rag.py`-Servers auf.
8.  Das `ollama_rag.py`-Skript:
    a.  Generiert ein Embedding für die Benutzerfrage.
    b.  Sucht mit diesem Embedding in ChromaDB nach den ähnlichsten (relevantesten) gespeicherten Ereignissen.
    c.  Erstellt einen Kontext aus den gefundenen Ereignissen.
    d.  Sendet die ursprüngliche Frage und den Kontext an das Ollama Chat-Modell (konfiguriert durch `TOOL_LLM_MODEL`).
9.  Das LLM generiert eine Antwort basierend auf dem bereitgestellten Kontext.
10. Die Antwort wird an Open Web UI zurückgesendet und dem Benutzer angezeigt.

## Fehlerbehebung / Hinweise

*   **Logs überprüfen**: Die Logs aller Komponenten sind entscheidend für die Fehlersuche:
    *   ioBroker JavaScript-Adapter Logs.
    *   Terminal-Ausgaben von `ollama_rag.py`.
    *   Ollama Server Logs.
    *   ChromaDB Logs (wenn als Dienst via `journalctl -u chromadb.service` oder direkt, falls anders gestartet).
    *   Browser-Entwicklerkonsole in Open Web UI.
*   **IP-Adressen und Ports**: Stelle sicher, dass alle IP-Adressen und Ports in den Konfigurationen korrekt sind und die Komponenten sich im Netzwerk erreichen können. Firewalls könnten die Kommunikation blockieren.
*   **Modellnamen**: Überprüfe die genauen Namen der Ollama-Modelle (`OLLAMA_EMBEDDING_MODEL`, `TOOL_LLM_MODEL`). Stelle sicher, dass sie in Ollama verfügbar sind (`ollama list`).
*   **ChromaDB Collection Name**: Wird in `ollama_rag.py` über `CHROMADB_COLLECTION_NAME` konfiguriert.
*   **Python Virtuelle Umgebung**: Es wird dringend empfohlen, virtuelle Umgebungen zu verwenden, um Konflikte zwischen Paketversionen zu vermeiden. Stelle sicher, dass die richtige Umgebung aktiv ist, wenn du das Skript startest oder Pakete installierst.
*   **Axios im ioBroker**: Wenn `axios` nicht gefunden wird, stelle sicher, dass es korrekt in den JavaScript-Adapter-Einstellungen hinzugefügt wurde und der Adapter neu gestartet wurde.