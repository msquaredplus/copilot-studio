# Rechnungs-OCR-Automatisierung — Integrationsanleitung

**Für wen ist diese Anleitung?**  
Für Personen ohne Programmierkenntnisse, die den Workflow in Microsoft Copilot Studio einrichten möchten.

**Was macht der Workflow?**  
Sobald eine E-Mail mit dem Betreff „Rechnung" in Ihrem Postfach eingeht, liest der Workflow automatisch alle PDF-Anhänge aus, extrahiert Rechnungsnummer, Fälligkeitsdatum und die Fahrzeugidentifikationsnummern (VIN/FGSTNR17) und trägt diese Daten in eine Excel-Datei auf SharePoint ein.

---

## Voraussetzungen (vor Schritt 1)

Stellen Sie sicher, dass folgende Dinge vorhanden sind:

| Was | Warum |
|-----|-------|
| Microsoft 365-Konto (mit Copilot Studio-Lizenz) | Für den Import und Betrieb |
| Azure-Abonnement | Für den OCR-Dienst (Azure AI Document Intelligence) |
| SharePoint-Site mit einer Excel-Datei | Als Ziel für die extrahierten Daten |
| VS Code (kostenlos) + Power Platform Tools-Erweiterung | Zum Hochladen der Dateien |

---

## Schritt 1 — Excel-Datei vorbereiten

1. Öffnen Sie Ihre Excel-Datei auf SharePoint im Browser.
2. Navigieren Sie zum Sheet **„Rechnungen"**.
3. Tragen Sie in **Zeile 1** folgende Spaltenüberschriften ein (exakt so, mit Umlaut):

   | A | B | C | D |
   |---|---|---|---|
   | Rechnungsnummer | Fälligkeitsdatum | VIN | Fehler |

4. Markieren Sie die gesamte Zeile 1 und alle Datenspalten darunter.
5. Klicken Sie im Menü auf **Einfügen → Tabelle** und bestätigen Sie „Meine Tabelle hat Überschriften".
6. **Wichtig:** Notieren Sie den **Tabellennamen** (standardmäßig „Tabelle1" — sichtbar im Reiter „Tabellendesign" wenn die Tabelle ausgewählt ist).

> ⚠️ Der Workflow schreibt nur in eine **formatierte Excel-Tabelle**, nicht in ein normales Sheet!

---

## Schritt 2 — Azure AI Document Intelligence einrichten

1. Öffnen Sie das [Azure-Portal](https://portal.azure.com).
2. Klicken Sie auf **Ressource erstellen** → Suche nach **„Document Intelligence"**.
3. Erstellen Sie eine neue Instanz:
   - Preisstufe: **S0** (Standard — für produktiven Einsatz)
   - Region: z.B. **West Europe**
4. Nach der Erstellung öffnen Sie die Ressource und klicken auf **„Schlüssel und Endpunkt"**.
5. Notieren Sie:
   - **Endpunkt** (z.B. `https://meine-ressource.cognitiveservices.azure.com/`)
   - **Schlüssel 1**

---

## Schritt 3 — Benutzerdefinierten Connector erstellen

Der Workflow kommuniziert über einen „Connector" mit dem OCR-Dienst. Diesen müssen Sie einmalig anlegen.

1. Öffnen Sie [make.powerapps.com](https://make.powerapps.com) und melden Sie sich an.
2. Klicken Sie links auf **„Weitere..."** → **„Benutzerdefinierte Connectors"**.
3. Klicken Sie oben rechts auf **„+ Neuer benutzerdefinierter Connector" → „Aus leerer Vorlage"**.
4. Name: `AzureDocumentIntelligence`
5. Wechseln Sie zum Tab **„Sicherheit"**:
   - Authentifizierungstyp: **API-Schlüssel**
   - Parameterlabel: `Ocp-Apim-Subscription-Key`
   - Parameterstandort: **Header**
6. Wechseln Sie zum Tab **„Definition"** und fügen Sie zwei Aktionen ein:

   **Aktion 1: AnalyzeDocumentPage1**
   - Zusammenfassung: OCR Seite 1
   - Verb: POST
   - URL: `{Ihr Endpunkt}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version=2024-02-29-preview&pages=1&features=ocrHighResolution`
   - Anforderungstext (JSON):
     ```json
     { "base64Source": "" }
     ```
   - Antwortschema (JSON — definiert was zurückgegeben wird):
     ```json
     {
       "rechnungsnummer": "",
       "faelligkeitsdatum": "",
       "success": true,
       "error": ""
     }
     ```

   **Aktion 2: AnalyzeDocumentPage2**
   - Wie oben, aber URL mit `pages=2`
   - Antwortschema:
     ```json
     {
       "fgstnr17Values": [],
       "success": true,
       "error": ""
     }
     ```

   > 💡 **Hinweis zu den Antwortschemas:** Die Felder `rechnungsnummer`, `faelligkeitsdatum` und `fgstnr17Values` werden durch eine **Antwortumwandlung** (Response Transform / Policy) aus der Document Intelligence-Antwort extrahiert. Bitten Sie Ihren IT-Administrator, die Transformation einzurichten — die genaue Konfiguration hängt von Ihrer Connector-Version ab.

7. Klicken Sie auf **„Connector erstellen"**.
8. Notieren Sie den **logischen Namen** des Connectors (sichtbar in der URL nach dem Erstellen, z.B. `shared_azuredocumentintelligence`).
9. Ersetzen Sie in den Dateien `OcrSeite1Action.mcs.yml` und `OcrSeite2Action.mcs.yml` den Platzhalter `<azure_document_intelligence_custom_connector>` durch diesen Namen.

---

## Schritt 4 — VS Code einrichten und Dateien hochladen

### VS Code installieren und konfigurieren

1. Laden Sie [VS Code](https://code.visualstudio.com) herunter und installieren Sie es.
2. Öffnen Sie VS Code → klicken Sie links auf das **Erweiterungen-Symbol** (4 Quadrate).
3. Suchen Sie nach **„Power Platform Tools"** und klicken Sie auf **„Installieren"**.
4. Drücken Sie `Strg+Shift+P` (Windows) oder `Cmd+Shift+P` (Mac) und suchen Sie nach **„Power Platform: Anmelden"**. Folgen Sie den Anweisungen.

### Dateien importieren

1. Öffnen Sie in VS Code den Ordner `output/issue-1/` aus diesem Paket (**Datei → Ordner öffnen**).
2. Drücken Sie erneut `Strg+Shift+P` → **„Power Platform: Neue Umgebung wählen"** → wählen Sie Ihre Copilot Studio-Umgebung.
3. Drücken Sie `Strg+Shift+P` → **„Power Platform: syncPush"**.

   VS Code lädt jetzt alle `.mcs.yml`-Dateien in Copilot Studio hoch. Dies dauert ca. 1–2 Minuten.

---

## Schritt 5 — Verbindungen in Copilot Studio aktivieren

1. Öffnen Sie [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com).
2. Sie sehen den neuen Agenten **„Rechnungs-OCR-Automatisierung"**.
3. Klicken Sie auf den Agenten → **„Einstellungen" → „Verbindungen"**.
4. Aktivieren Sie folgende Verbindungen:
   - **Office 365 Outlook** — melden Sie sich mit Ihrem M365-Konto an
   - **Excel Online (Business)** — melden Sie sich mit Ihrem M365-Konto an
   - **AzureDocumentIntelligence** — tragen Sie Ihren API-Schlüssel ein (aus Schritt 2)

---

## Schritt 6 — Umgebungsvariablen setzen

Die Verbindungsdaten zur SharePoint-Datei werden als Variablen hinterlegt, damit Sie diese später einfach ändern können, ohne Dateien neu hochladen zu müssen.

1. Öffnen Sie [make.powerapps.com](https://make.powerapps.com).
2. Klicken Sie links auf **„Lösungen"** → öffnen Sie die Lösung mit dem Agenten.
3. Klicken Sie auf **„+ Neu" → „Umgebungsvariable"** und legen Sie folgende drei Variablen an:

   | Name | Wert (Beispiel) |
   |------|-----------------|
   | `sharepointSiteUrl` | `https://ihrafirma.sharepoint.com/sites/Buchhaltung` |
   | `excelFilePath` | `/Freigegebene Dokumente/Rechnungen.xlsx` |
   | `excelTableName` | `Tabelle1` (Name aus Schritt 1 Punkt 6) |

---

## Schritt 7 — Power Automate-Flow einrichten (E-Mail-Trigger)

Der Workflow in Copilot Studio verarbeitet ein einzelnes PDF/einen einzelnen Datensatz. Die äußere Schleife (für jede E-Mail, jedes PDF, jeden FGSTNR17-Wert) wird durch **Power Automate** gesteuert.

1. Öffnen Sie [make.powerautomate.com](https://make.powerautomate.com).
2. Klicken Sie auf **„+ Erstellen" → „Automatisierter Cloud-Flow"**.
3. Trigger: **„Wenn eine neue E-Mail eingeht (V3)"**
   - Ordner: Posteingang
   - Nur mit Anlagen: Ja
   - Betreff-Filter: `Rechnung`
4. Fügen Sie die Schleife hinzu:
   - **„Auf alle anwenden"** → Wert: `Anlagen` (aus dem E-Mail-Trigger)
   - Bedingung: `Name der Anlage endet mit .pdf`
   - Innerhalb der Schleife: **„Copilot Studio-Agent ausführen"** → Wählen Sie **„Rechnungs-OCR-Automatisierung"** → übergeben Sie die PDF-Bytes als `documentBase64`
5. Speichern und aktivieren Sie den Flow.

---

## Schritt 8 — Test durchführen

1. Senden Sie sich selbst eine Test-E-Mail mit Betreff **„Rechnung"** und einem PDF-Anhang.
2. Warten Sie ca. 1–3 Minuten.
3. Öffnen Sie Ihre SharePoint-Excel-Datei → Sheet **„Rechnungen"**.
4. Neue Zeilen sollten am Ende der Tabelle erscheinen.

**Wenn die Spalte „Fehler" befüllt ist:**  
→ Der OCR-Dienst hat das Feld nicht gefunden. Prüfen Sie, ob die Begriffe `RECHNUNG-Nummer.:` und `Fälligkeit:` exakt so im PDF stehen.

---

## Erweiterung: Neue FGSTNR17-Validierungsregel hinzufügen

Die Datei `actions/ValidiereFGSTNR17Action.mcs.yml` ist modular aufgebaut. Um eine neue Regel hinzuzufügen:

1. Öffnen Sie die Datei in einem Texteditor.
2. Suchen Sie den Kommentar `# ── RULE_05..N: Insert additional ConditionGroup blocks here`.
3. Fügen Sie darunter einen neuen Block ein (Beispiel — Regel: Wert darf nicht mit „0" beginnen):

```yaml
  - kind: ConditionGroup
    id: cond_rule05
    conditions:
      - id: cond_rule05_fail
        condition: =Left($inputs.rawValue, 1) = "0"
        actions:
          - kind: SetVariable
            id: set_fail_r05
            variable: Dialog.validationPassed
            value: =false
          - kind: SetVariable
            id: set_fehler_r05
            variable: Dialog.fehlerBeschreibung
            value: =If(Dialog.fehlerBeschreibung = "", "Wert darf nicht mit 0 beginnen", Dialog.fehlerBeschreibung & " | Wert darf nicht mit 0 beginnen")
```

4. Laden Sie die Datei erneut via `syncPush` hoch (Schritt 4).

---

## Dateien in diesem Paket

```
output/issue-1/
├── agent.mcs.yml                          Agent-Konfiguration
├── settings.mcs.yml                       Sprache, Authentifizierung
├── topics/
│   ├── Greeting.topic.mcs.yml             Startmeldung
│   ├── Fallback.topic.mcs.yml             Antwort bei manuellen Anfragen
│   ├── ErrorHandler.topic.mcs.yml         Fehlerbehandlung
│   └── RechnungsWorkflow.topic.mcs.yml    Haupt-Workflow-Logik
└── actions/
    ├── HoleEmailsAction.mcs.yml           E-Mails aus Postfach abrufen
    ├── OcrSeite1Action.mcs.yml            OCR: Rechnungsnummer + Fälligkeit
    ├── OcrSeite2Action.mcs.yml            OCR: FGSTNR17-Tabelle (Low-Contrast)
    ├── ValidiereFGSTNR17Action.mcs.yml    Validierung (erweiterbar)
    └── AppendExcelZeileAction.mcs.yml     Zeile in SharePoint-Excel schreiben
```

---

## Häufige Probleme

| Problem | Lösung |
|---------|--------|
| Keine Zeilen in Excel | Power Automate-Flow läuft nicht → prüfen Sie den Flow-Verlauf in make.powerautomate.com |
| Fehler: „Verbindung nicht gefunden" | Schritt 5 — Verbindungen in Copilot Studio aktivieren |
| Fehler: „Tabelle nicht gefunden" | Prüfen Sie `excelTableName` in den Umgebungsvariablen (Schritt 6) |
| FGSTNR17 leer / fehlt | Scanqualität zu schlecht → OCR-Dienst hat Tabelle nicht erkannt. Testen Sie mit einem besseren Scan. |
| Spalte „Fehler" zeigt „O gefunden" | OCR hat den Buchstaben O statt 0 erkannt — Validierung greift korrekt. Wert zur manuellen Prüfung markiert. |
