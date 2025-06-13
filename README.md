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
    *   Das Chat-Modell (Standard: `iobroker-assistant:latest`) muss in Ollama verfügbar sein: `ollama pull iobroker-assistant:latest` (oder ein anderes Modell deiner Wahl).
*   **Node.js & npm**: (Normalerweise mit ioBroker bereits vorhanden) für `axios` im JavaScript-Adapter.
*   Für die unten beschriebene ChromaDB-Installation unter Linux: Zugriff auf einen Linux-Server mit `sudo`-Rechten.

## Installation und Konfiguration

### 1. ChromaDB (Linux mit systemd)

Diese Anleitung beschreibt die Installation von ChromaDB als Dienst auf einem Linux-System (z.B. Debian) unter Verwendung von `systemd`. Dies ist eine empfohlene Methode für den Betrieb auf einem Server (z.B. dem Ollama-Server).

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
       # Installieren Sie python3-venv, falls es nicht vorhanden ist (z.B. auf Debian/Ubuntu)
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
    Öffnen Sie eine Eingabeaufforderung oder PowerShell **als Administrator**.
    Führen Sie den folgenden Befehl aus, um die NSSM-Service-Installations-GUI zu öffnen:
    ````shell
    nssm install ChromaDBService
    ````
    Im NSSM-GUI-Fenster konfigurieren Sie die folgenden Reiter:

    *   **Application Tab:**
        *   **Path:** Geben Sie den Pfad zur `chroma.exe` ein. Normalerweise befindet sich diese im `Scripts`-Verzeichnis Ihrer Python-Installation (z.B. `C:\Python311\Scripts\chroma.exe` oder der Pfad, den `where chroma` in der Kommandozeile anzeigt).
        *   **Startup directory:** Geben Sie den Pfad zum `Scripts`-Verzeichnis Ihrer Python-Installation ein (z.B. `C:\Python311\Scripts`).
        *   **Arguments:** Geben Sie `run --path /path/to/your/chroma_data --port 8087` ein. Ersetzen Sie `/path/to/your/chroma_data` durch den tatsächlichen Pfad, in dem ChromaDB seine Daten speichern soll (z.B. `C:\ChromaData`). Sie können den Port bei Bedarf anpassen.

    *   **Details Tab (Optional):**
        *   **Display name:** `ChromaDB Service`
        *   **Description:** `ChromaDB Persistent Vector Store Service`

    *   **I/O Tab (Optional aber empfohlen):**
        *   Konfigurieren Sie hier die Ausgabe- (stdout) und Fehlerprotokolldateien (stderr), um das Logging des Dienstes zu ermöglichen. Zum Beispiel:
            *   **Output (stdout):** `C:\ChromaData\chroma_service.log`
            *   **Error (stderr):** `C:\ChromaData\chroma_service_error.log`
        Stellen Sie sicher, dass das Verzeichnis `C:\ChromaData` existiert oder erstellen Sie es.

    *   **Environment Tab (Wichtig, falls Python nicht im System-PATH ist oder virtuelle Umgebungen genutzt werden):**
        Wenn Sie ChromaDB in einer virtuellen Umgebung installiert haben oder Ihr Python-Verzeichnis nicht im System-PATH ist, müssen Sie hier die `PATH`-Variable anpassen.
        Fügen Sie eine Variable hinzu: `PATH=%PATH%;C:\Pfad\zu\Ihrem\Python\Scripts;C:\Pfad\zu\Ihrem\Python`
        (Passen Sie die Pfade entsprechend Ihrer Python-Installation an).

    Klicken Sie auf **Install service**.

**e. Dienst starten:**
    Sie können den Dienst über die Windows-Diensteverwaltung (`services.msc`) starten oder über die Kommandozeile:
    ````shell
    nssm start ChromaDBService
    ````
    Oder:
    ````shell
    net start ChromaDBService
    ````

**Hinweise:**

*   Stellen Sie sicher, dass der angegebene `--path` für die ChromaDB-Daten existiert und der Dienst Schreibrechte darauf hat.
*   Überprüfen Sie die Logdateien (falls konfiguriert), um Fehler beim Starten oder während des Betriebs zu diagnostizieren.
*   Um den Dienst zu stoppen: `nssm stop ChromaDBService` oder `net stop ChromaDBService`.
*   Um den Dienst zu entfernen: `nssm remove ChromaDBService` (bestätigen Sie die Aktion).

**f. Konfiguration in Python-Skripten:**
   Der Host und Port für ChromaDB werden in `iobroker_receiver.py` und `rag_tool_server.py` über Umgebungsvariablen oder Standardwerte konfiguriert (siehe unten). Der Standardport im Skript ist `8087`.

### 2. Python-Skripte (`iobroker_receiver.py` & `rag_tool_server.py`)

Beide Python-Skripte benötigen ähnliche Abhängigkeiten. Es wird empfohlen, eine virtuelle Umgebung zu verwenden.

**a. Virtuelle Umgebung erstellen (optional, aber empfohlen):**
   ```bash
   python -m venv venv
   venv\Scripts\activate    # Windows
   ```

**b. Abhängigkeiten installieren:**
   Erstelle eine Datei `requirements.txt` mit folgendem Inhalt:
   ```txt
   flask
   flask-cors
   ollama
   chromadb-client 
   python-dotenv 
   ```
   Installiere die Abhängigkeiten:
   ```bash
   pip install -r requirements.txt
   ```
   *Hinweis: `chromadb-client` wird benötigt, wenn ChromaDB als Server läuft. Wenn du ChromaDB als Library nutzen würdest, wäre es nur `chromadb`.*

**c. `iobroker_receiver.py` Konfiguration:**
   Dieses Skript empfängt Daten von ioBroker.
   *   **`CHROMADB_HOST`**: IP-Adresse des ChromaDB-Servers (Standard: "0.0.0.0", was bedeutet, dass es auf Anfragen von jeder IP auf dem Host lauscht, auf dem das Skript läuft. Für den Client-Teil, der sich mit ChromaDB verbindet, sollte dies die IP sein, unter der ChromaDB erreichbar ist, z.B. "192.168.0.206" oder "localhost", wenn ChromaDB auf derselben Maschine läuft).
   *   **`CHROMADB_PORT`**: Port des ChromaDB-Servers (Standard: `8087`).
   *   **`CHROMADB_COLLECTION_NAME`**: Name der ChromaDB-Collection (Standard: `"iobroker_events"`).
   *   **`OLLAMA_HOST`**: URL des Ollama-Servers (Standard: `"http://192.168.0.204:11434"`).
   *   **`OLLAMA_EMBEDDING_MODEL`**: Name des Embedding-Modells in Ollama (Standard: `"nomic-embed-text"`).
   *   **`FLASK_HOST`**: Host, auf dem dieser Receiver-Server lauschen soll (Standard: `"0.0.0.0"`).
   *   **`FLASK_PORT`**: Port für den Receiver-Server (Standard: `5000`).
   *   **`FLASK_DEBUG_MODE`**: Flask Debug-Modus (Standard: `"False"`).

   Diese können als Umgebungsvariablen gesetzt oder direkt im Skript angepasst werden (Umgebungsvariablen sind bevorzugt).

**d. `rag_tool_server.py` Konfiguration:**
   Dieses Skript stellt das RAG-Tool für Open Web UI bereit.
   *   **`OLLAMA_ACTUAL_SERVER_URL`**: URL des Ollama-Servers (Standard: `"http://192.168.0.204:11434"`).
   *   **`CHROMADB_HOST`**: IP-Adresse des ChromaDB-Servers (Standard: `"192.168.0.206"`).
   *   **`CHROMADB_PORT`**: Port des ChromaDB-Servers (Standard: `8087`).
   *   **`CHROMADB_COLLECTION_NAME`**: Name der ChromaDB-Collection (Standard: `"iobroker_events"`). **Achte darauf, dass dieser Name mit dem in `iobroker_receiver.py` übereinstimmt!** Der Default-Wert im bereitgestellten Skript `rag_tool_server.py` enthält einen Tippfehler (`...data_answer_events`) und sollte zu `"iobroker_events"` korrigiert werden, um mit dem Receiver übereinzustimmen.
   *   **`OLLAMA_EMBEDDING_MODEL`**: Name des Embedding-Modells (Standard: `"nomic-embed-text"`).
   *   **`TOOL_SERVER_LLM_MODEL`**: Name des Chat-Modells in Ollama, das vom Tool verwendet wird (Standard: `"iobroker-assistant:latest"`).
   *   **`RELAY_SERVER_PORT`**: Port, auf dem dieser Tool-Server lauschen soll (Standard: `5001`).
   *   **`RAG_N_RESULTS`**: Anzahl der relevantesten Dokumente, die aus ChromaDB abgerufen werden (Standard: `3`).

**e. Python-Skripte starten:**
   Öffne zwei separate Terminals (oder verwende `screen`/`tmux` unter Linux).

   Im ersten Terminal, starte den `iobroker_receiver.py`:
   ```bash
   python iobroker_receiver.py
   ```

   Im zweiten Terminal, starte den `rag_tool_server.py`:
   ```bash
   python rag_tool_server.py
   ```

### 3. `ollama export.js` (ioBroker JavaScript)

**a. Installation:**
   1.  Öffne deine ioBroker-Admin-Oberfläche.
   2.  Gehe zum "Skripte"-Adapter.
   3.  Erstelle ein neues JavaScript (nicht Blockly oder TypeScript).
   4.  Kopiere den gesamten Inhalt von `ollama export.js` in dieses neue Skript.

**b. Konfiguration im Skript:**
   Passe die folgenden Konstanten am Anfang des Skripts an:
   *   **`PYTHON_SERVER_URL_BASE`**: Die URL, unter der dein `iobroker_receiver.py` erreichbar ist (Standard: `"http://192.168.0.206:5000"`). Stelle sicher, dass IP und Port korrekt sind.
   *   **`TARGET_DATAPOINTS`**: Dies ist die wichtigste Konfiguration. Definiere hier alle ioBroker-Datenpunkte, die du überwachen und an Ollama senden möchtest. Jeder Eintrag ist ein Objekt mit:
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

### 4. Open Web UI Tool Integration

1.  Starte deinen `rag_tool_server.py`. Er stellt eine OpenAPI-Spezifikation unter `http://<IP_RAG_TOOL_SERVER>:<RELAY_SERVER_PORT>/openapi.json` bereit (z.B. `http://192.168.0.204:5001/openapi.json`).
2.  Gehe in Open Web UI zu den Einstellungen des Modells, das du verwenden möchtest.
3.  Aktiviere "Tools" und füge die URL zur `openapi.json` deines `rag_tool_server.py` hinzu.
4.  Open Web UI sollte das Tool `getIoBrokerDataAnswer` erkennen.
5.  Wähle das Tool für die Verwendung im Chat aus.

## Workflow

1.  Eine Änderung an einem der in `ollama export.js` konfigurierten ioBroker-Datenpunkte tritt ein.
2.  Das ioBroker-Skript sendet die Datenpunktinformationen (Wert, Beschreibung, Typ, Zeitstempel etc.) an den `iobroker_receiver.py`.
3.  Der `iobroker_receiver.py` erstellt einen beschreibenden Text aus diesen Informationen.
4.  Er generiert mit Ollama (`nomic-embed-text`) ein Embedding für diesen Text.
5.  Der Text, das Embedding und Metadaten werden in der ChromaDB-Collection (`iobroker_events`) gespeichert.
6.  Ein Benutzer stellt eine Frage in Open Web UI (z.B. "Wie warm ist es im Wohnzimmer?").
7.  Open Web UI erkennt, dass die Frage für das `getIoBrokerDataAnswer`-Tool relevant sein könnte und ruft den `rag_tool_server.py` auf.
8.  Der `rag_tool_server.py`:
    a.  Generiert ein Embedding für die Benutzerfrage.
    b.  Sucht mit diesem Embedding in ChromaDB nach den ähnlichsten (relevantesten) gespeicherten Ereignissen.
    c.  Erstellt einen Kontext aus den gefundenen Ereignissen.
    d.  Sendet die ursprüngliche Frage und den Kontext an das Ollama Chat-Modell (`iobroker-assistant:latest`).
9.  Das LLM generiert eine Antwort basierend auf dem bereitgestellten Kontext.
10. Die Antwort wird an Open Web UI zurückgesendet und dem Benutzer angezeigt.

## Fehlerbehebung / Hinweise

*   **Logs überprüfen**: Die Logs aller Komponenten sind entscheidend für die Fehlersuche:
    *   ioBroker JavaScript-Adapter Logs.
    *   Terminal-Ausgaben von `iobroker_receiver.py`.
    *   Terminal-Ausgaben von `rag_tool_server.py`.
    *   Ollama Server Logs.
    *   Browser-Entwicklerkonsole in Open Web UI.
*   **IP-Adressen und Ports**: Stelle sicher, dass alle IP-Adressen und Ports in den Konfigurationen korrekt sind und die Komponenten sich im Netzwerk erreichen können. Firewalls könnten die Kommunikation blockieren.
*   **Modellnamen**: Überprüfe die genauen Namen der Ollama-Modelle.
*   **ChromaDB Collection Name**: Muss in `iobroker_receiver.py` und `rag_tool_server.py` identisch sein.
*   **Python Virtuelle Umgebung**: Es wird dringend empfohlen, virtuelle Umgebungen zu verwenden, um Konflikte zwischen Paketversionen zu vermeiden.
*   **Axios im ioBroker**: Wenn `axios` nicht gefunden wird, stelle sicher, dass es korrekt in den JavaScript-Adapter-Einstellungen hinzugefügt wurde und der Adapter neu gestartet wurde.