const axios = require('axios');

// Konfiguration
const anfrageDatenpunkt = '0_userdata.0.Anfrage';
const antwortDatenpunkt = '0_userdata.0.Antwort';
const apiEndpoint = 'http://192.168.0.204:5001/tools/get_iobroker_data_answer';

// Sicherstellen, dass die Datenpunkte existieren (optional, aber gute Praxis)
if (!existsState(anfrageDatenpunkt)) {
    createState(anfrageDatenpunkt, '', {
        name: 'Anfrage an Ollama Service',
        type: 'string',
        role: 'text',
        read: true,
        write: true,
    });
}

if (!existsState(antwortDatenpunkt)) {
    createState(antwortDatenpunkt, '', {
        name: 'Antwort von Ollama Service',
        type: 'string',
        role: 'text',
        read: true,
        write: false, // Nur durch Skript beschreibbar
    });
}

// Auf Änderungen des Anfrage-Datenpunkts reagieren
on({ id: anfrageDatenpunkt, change: 'ne', ack: false }, async function (obj) {
    const userQuery = obj.state.val;
    log('Neue Anfrage empfangen: ' + userQuery, 'info');

    if (!userQuery || typeof userQuery !== 'string' || userQuery.trim() === '') {
        log('Ungültige oder leere Anfrage.', 'warn');
        setState(antwortDatenpunkt, 'Fehler: Ungültige oder leere Anfrage.', true);
        return;
    }

    const requestPayload = { user_query: userQuery };

    try {
        const response = await axios.post(apiEndpoint, requestPayload, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 10000 // 10 Sekunden Timeout
        });

        if (response.status === 200 && response.data) {
            if (response.data.answer) {
                const answer = response.data.answer;
                log('Antwort vom Service erhalten: ' + answer, 'info');
                setState(antwortDatenpunkt, answer, true);
            } else {
                log('Ungültige Antwortstruktur vom Service. Body: ' + JSON.stringify(response.data), 'warn');
                setState(antwortDatenpunkt, 'Fehler: Ungültige Antwortstruktur.', true);
            }
        } else {
            // Dieser Fall sollte durch den catch-Block für HTTP-Fehler abgedeckt werden,
            // aber zur Sicherheit hier belassen.
            log('Service antwortete mit Statuscode: ' + response.status + ' Body: ' + JSON.stringify(response.data), 'warn');
            setState(antwortDatenpunkt, 'Fehler: Service antwortete mit Status ' + response.status, true);
        }
    } catch (error) {
        if (error.response) {
            // Die Anfrage wurde gestellt und der Server antwortete mit einem Statuscode
            // außerhalb des Bereichs von 2xx
            log('Fehler vom Service (Status ' + error.response.status + '): ' + JSON.stringify(error.response.data), 'error');
            setState(antwortDatenpunkt, 'Fehler vom Service: Status ' + error.response.status, true);
        } else if (error.request) {
            // Die Anfrage wurde gestellt, aber keine Antwort erhalten
            log('Keine Antwort vom Service erhalten: ' + error.message, 'error');
            setState(antwortDatenpunkt, 'Fehler: Keine Antwort vom Service.', true);
        } else {
            // Ein Fehler ist beim Erstellen der Anfrage aufgetreten
            log('Fehler beim Senden der Anfrage: ' + error.message, 'error');
            setState(antwortDatenpunkt, 'Fehler: Anfrage konnte nicht gesendet werden.', true);
        }
        log('Fehlerdetails (axios): ' + JSON.stringify(error.config), 'debug');
    }
});