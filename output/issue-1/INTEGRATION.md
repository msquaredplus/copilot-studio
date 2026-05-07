# Rechnungs-OCR-Automatisierung — Integrationsanleitung

**Zielgruppe:** Personen ohne Programmierkenntnisse  
**Zugang:** Ausschließlich über den Browser — kein VS Code, kein lokales Tool nötig

**Was macht der Workflow?**  
Sobald eine E-Mail mit dem Betreff „Rechnung" eingeht, liest der Workflow automatisch alle PDF-Anhänge aus, extrahiert Rechnungsnummer, Fälligkeitsdatum und Fahrzeugidentifikationsnummern (VIN/FGSTNR17) und trägt diese Daten in eine Excel-Datei auf SharePoint ein.

---

## Überblick: Zwei Wege zur Installation

| Weg | Wann nutzen | Aufwand |
|-----|-------------|---------|
| **A — KI-Prompt-Erstellung** | Schnellstart, Grundstruktur automatisch | Niedrig — KI baut die Nodes, Sie füllen Parameter |
| **B — Code-Editor (YAML einfügen)** | Exakte Logik aus dieser Vorlage übernehmen | Mittel — YAML kopieren, Parameter setzen |

**Empfehlung:** Beginnen Sie mit **Weg A** für die Grundstruktur. Nutzen Sie **Weg B** für die komplexen Teile (Validierung, Fehlerbehandlung).

---

## Voraussetzungen

| Was | Warum |
|-----|-------|
| Microsoft 365-Konto mit Copilot Studio-Lizenz | Zugang zu copilotstudio.microsoft.com |
| Azure-Abonnement | Für den OCR-Dienst (Azure AI Document Intelligence) |
| SharePoint-Seite mit Excel-Datei | Ziel für die extrahierten Daten |

---

## Schritt 1 — Excel-Datei vorbereiten

1. Öffnen Sie Ihre Excel-Datei auf SharePoint im Browser.
2. Navigieren Sie zum Sheet **„Rechnungen"**.
3. Tragen Sie in **Zeile 1** folgende Spaltenüberschriften ein — exakt so, mit Umlaut:

   | A | B | C | D |
   |---|---|---|---|
   | Rechnungsnummer | Fälligkeitsdatum | VIN | Fehler |

4. Markieren Sie Zeile 1 und alle Spalten.
5. Klicken Sie im Menü auf **Einfügen → Tabelle** → „Meine Tabelle hat Überschriften" bestätigen.
6. Notieren Sie den **Tabellennamen** (sichtbar im Reiter „Tabellendesign", z.B. `Tabelle1`).

> ⚠️ Der Workflow schreibt nur in eine **formatierte Excel-Tabelle**, nicht in ein normales Sheet!

---

## Schritt 2 — Azure AI Document Intelligence einrichten

1. Öffnen Sie [portal.azure.com](https://portal.azure.com).
2. **Ressource erstellen** → suchen Sie nach **„Document Intelligence"**.
3. Neue Instanz erstellen:
   - Preisstufe: **S0** (Standard)
   - Region: **West Europe**
4. Nach der Erstellung: Ressource öffnen → **„Schlüssel und Endpunkt"**.
5. Notieren Sie:
   - **Endpunkt** (z.B. `https://meine-ressource.cognitiveservices.azure.com/`)
   - **Schlüssel 1**

---

## Schritt 3 — Neuen Agenten erstellen

1. Öffnen Sie [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com).
2. Klicken Sie auf **„+ Erstellen"** → **„Neuer Agent"**.
3. Benennen Sie den Agenten: **`Rechnungs-OCR-Automatisierung`**
4. Sprache: **Deutsch**
5. Klicken Sie auf **„Erstellen"**.

---

## Schritt 4 — Workflow per KI-Prompt anlegen (Weg A)

Copilot Studio hat einen eingebauten KI-Assistenten, der Topics und Aktionsknoten automatisch als bearbeitbare Elemente auf der Zeichenfläche erzeugt. Sie beschreiben, was passieren soll — die KI baut die Struktur.

### 4.1 — Haupt-Workflow-Topic per KI erstellen

1. Klicken Sie im linken Menü auf **„Topics"** → **„+ Neues Topic hinzufügen"** → **„Mit Copilot erstellen"**.
2. Geben Sie folgenden Prompt ein:

```
Erstelle ein Topic namens "RechnungsWorkflow" ohne Benutzerinteraktion.
Der Ablauf:
1. Empfange ein PDF-Dokument als Base64-String als Eingabe.
2. Rufe eine Aktion "OcrSeite1" auf und übergib das PDF. Speichere die Ergebnisse Rechnungsnummer und Faelligkeitsdatum.
3. Falls OcrSeite1 fehlschlägt, setze eine Variable "fehlerBeschreibung" mit dem Fehlertext.
4. Rufe eine Aktion "OcrSeite2" auf und übergib das PDF. Speichere das Ergebnis als Liste "fgstnr17Werte".
5. Falls OcrSeite2 fehlschlägt, hänge den Fehler an "fehlerBeschreibung" an und setze fgstnr17Werte auf ["__OCR_FEHLER__"].
6. Für jeden Wert in fgstnr17Werte: Rufe "ValidiereFGSTNR17" auf. Falls ungültig, hänge den Fehlertext an "fehlerBeschreibung" an.
7. Rufe "AppendExcelZeile" auf mit Rechnungsnummer, Faelligkeitsdatum, aktuellem fgstnr17Wert und fehlerBeschreibung.
8. Beende den Dialog.
```

3. Klicken Sie auf **„Erstellen"** — die KI baut die Knoten automatisch auf der Zeichenfläche.

### 4.2 — Validierungs-Topic per KI erstellen

1. Neues Topic → **„Mit Copilot erstellen"**:

```
Erstelle ein Topic namens "ValidiereFGSTNR17" mit einer Texteingabe "rawValue".
Prüfe den Wert auf folgende Regeln und setze bei Fehler validationPassed=false und hänge die Fehlermeldung an fehlerBeschreibung an:
Regel 1: Länge muss genau 17 Zeichen sein. Fehlermeldung: "Länge ungültig"
Regel 2: Nur Großbuchstaben (A-Z) und Ziffern (0-9) erlaubt. Fehlermeldung: "Ungültige Zeichen"
Regel 3: Der Buchstabe O (Großbuchstabe) ist nicht erlaubt, nur die Ziffer 0. Fehlermeldung: "Buchstabe O gefunden"
Alle Regeln müssen einzeln geprüft werden, auch wenn eine vorherige fehlschlägt.
Gib validationPassed (boolean) und fehlerBeschreibung (Text) zurück.
```

> 💡 Weitere Validierungsregeln lassen sich später hier ergänzen — einfach die KI erneut mit „Füge eine Regel hinzu: ..." aufrufen.

### 4.3 — Parameter nach KI-Erstellung manuell setzen

Die KI erstellt die Struktur, aber **Connector-Details** müssen Sie anschließend in jedem Knoten selbst eintragen:

| Knoten | Was eintragen |
|--------|--------------|
| OcrSeite1 / OcrSeite2 | Connector: Azure Document Intelligence → Endpunkt + Schlüssel aus Schritt 2 |
| AppendExcelZeile | Connector: Excel Online (Business) → SharePoint-URL, Dateipfad, Tabellenname |
| E-Mail-Trigger (Power Automate) | Posteingang-Ordner, Betreff-Filter „Rechnung" |

---

## Schritt 5 — Komplexe Actions per Code-Editor einfügen (Weg B)

Für Teile, die die KI unvollständig erstellt (z.B. die Validierungslogik oder die Excel-Action), können Sie das fertige YAML direkt einfügen.

### So öffnen Sie den Code-Editor:

1. Öffnen Sie ein Topic oder eine Action in Copilot Studio.
2. Klicken Sie oben rechts auf die **drei Punkte `...`** → **„Code-Editor öffnen"**.
3. Löschen Sie den vorhandenen Inhalt und fügen Sie das YAML aus der jeweiligen Datei dieses Pakets ein.
4. Drücken Sie `Strg+S` — die Zeichenfläche aktualisiert sich automatisch.

### Welche Dateien per Code-Editor einfügen:

| Datei aus diesem Paket | In Copilot Studio einfügen als |
|------------------------|-------------------------------|
| `actions/ValidiereFGSTNR17Action.mcs.yml` | Action „ValidiereFGSTNR17" → Code-Editor |
| `actions/OcrSeite1Action.mcs.yml` | Action „OcrSeite1" → Code-Editor |
| `actions/OcrSeite2Action.mcs.yml` | Action „OcrSeite2" → Code-Editor |
| `actions/AppendExcelZeileAction.mcs.yml` | Action „AppendExcelZeile" → Code-Editor |
| `topics/RechnungsWorkflow.topic.mcs.yml` | Topic „RechnungsWorkflow" → Code-Editor |

> **Hinweis:** Beim Einfügen via Code-Editor ersetzen Sie den Platzhalter `<azure_document_intelligence_custom_connector>` durch den tatsächlichen Connector-Namen (sichtbar in Copilot Studio unter Einstellungen → Verbindungen).

### Platzhalter ersetzen — Übersicht:

| Platzhalter in den YAML-Dateien | Ersetzen durch |
|----------------------------------|----------------|
| `<azure_document_intelligence_custom_connector>` | Logischer Name Ihres Azure DI Connectors |
| `Global.sharepointSiteUrl` | URL Ihrer SharePoint-Site |
| `Global.excelFilePath` | Pfad zur Excel-Datei (z.B. `/Freigegebene Dokumente/Rechnungen.xlsx`) |
| `Global.excelTableName` | Tabellenname aus Schritt 1 (z.B. `Tabelle1`) |

---

## Schritt 6 — Verbindungen aktivieren

1. Im Agenten: **Einstellungen → Verbindungen**.
2. Aktivieren Sie:
   - **Office 365 Outlook** — mit M365-Konto anmelden
   - **Excel Online (Business)** — mit M365-Konto anmelden
   - **Azure AI Document Intelligence** (custom connector) — API-Schlüssel aus Schritt 2 eintragen

---

## Schritt 7 — Power Automate: E-Mail-Trigger einrichten

Copilot Studio verarbeitet **ein PDF / einen Datensatz** pro Aufruf. Die äußere Schleife (für jede E-Mail, jedes PDF, jeden FGSTNR17-Wert) steuert **Power Automate**. Beides geschieht im Browser.

1. Öffnen Sie [make.powerautomate.com](https://make.powerautomate.com).
2. **+ Erstellen → Automatisierter Cloud-Flow**.
3. Trigger: **„Wenn eine neue E-Mail eingeht (V3)"**
   - Ordner: Posteingang
   - Nur mit Anlagen: **Ja**
   - Betreff enthält: **Rechnung**
4. Aktion: **„Auf alle anwenden"** (Quelle: Anlagen des E-Mail-Triggers)
   - Bedingung: Name der Anlage endet mit `.pdf`
   - Aktion innerhalb der Schleife: **„Copilot Studio-Agent ausführen"**
     - Agent: **Rechnungs-OCR-Automatisierung**
     - Eingabe `documentBase64`: `Anlageninhalt` (aus dem Trigger, Base64-Format)
5. Speichern und **Flow aktivieren**.

> 💡 **Tipp:** Power Automate hat ebenfalls eine KI-Unterstützung. Sie können den Flow per Beschreibung erstellen lassen: „Erstelle einen Flow der bei eingehenden E-Mails mit Betreff Rechnung alle PDF-Anhänge an einen Copilot Studio Agenten sendet."

---

## Schritt 8 — Test

1. Senden Sie sich eine Test-E-Mail mit Betreff **„Rechnung"** und einem PDF-Anhang.
2. Warten Sie 1–3 Minuten.
3. Öffnen Sie die SharePoint-Excel-Datei → Sheet **„Rechnungen"**.
4. Neue Zeilen erscheinen am Ende der Tabelle.

**Spalte „Fehler" ist befüllt?**  
→ OCR hat die Felder nicht erkannt. Prüfen Sie, ob `RECHNUNG-Nummer.:` und `Fälligkeit:` exakt so im PDF stehen.

---

## Validierungsregeln erweitern

Im Topic „ValidiereFGSTNR17" können Sie jederzeit neue Regeln hinzufügen:

**Per KI-Prompt** (im Topic → Copilot-Schaltfläche):
```
Füge eine neue Regel hinzu: Der Wert darf nicht mit der Ziffer 0 beginnen.
Fehlermeldung: "Wert darf nicht mit 0 beginnen"
```

**Per Code-Editor** (in `ValidiereFGSTNR17Action.mcs.yml`):  
Suchen Sie den Kommentar `# ── RULE_05..N` und fügen Sie darunter ein:

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

---

## Dateien in diesem Paket (Referenz)

Die `.mcs.yml`-Dateien dienen als fertige Vorlagen zum Einfügen per Code-Editor:

```
output/issue-1/
├── agent.mcs.yml                          Agent-Grundkonfiguration
├── settings.mcs.yml                       Sprache (DE), Azure AD Auth
├── topics/
│   ├── Greeting.topic.mcs.yml             Startmeldung
│   ├── Fallback.topic.mcs.yml             Antwort bei manuellen Anfragen
│   ├── ErrorHandler.topic.mcs.yml         Systemfehler-Antwort
│   └── RechnungsWorkflow.topic.mcs.yml    Haupt-Workflow (ein PDF pro Aufruf)
└── actions/
    ├── HoleEmailsAction.mcs.yml           E-Mails aus Postfach abrufen
    ├── OcrSeite1Action.mcs.yml            OCR: Rechnungsnummer + Fälligkeit (Seite 1)
    ├── OcrSeite2Action.mcs.yml            OCR: FGSTNR17-Tabelle, Low-Contrast (Seite 2)
    ├── ValidiereFGSTNR17Action.mcs.yml    Validierung, modular erweiterbar
    └── AppendExcelZeileAction.mcs.yml     Zeile in SharePoint-Excel schreiben
```

---

## Häufige Probleme

| Problem | Lösung |
|---------|--------|
| Keine neuen Zeilen in Excel | Power Automate-Flow nicht aktiv → Flow-Verlauf unter make.powerautomate.com prüfen |
| „Verbindung nicht gefunden" | Schritt 6 — alle drei Verbindungen aktivieren |
| „Tabelle nicht gefunden" | Tabellenname in Schritt 1 prüfen und in Schritt 5 korrekt eintragen |
| FGSTNR17-Werte fehlen | Scanqualität zu niedrig — mit besserem Scan testen |
| Spalte „Fehler": „Buchstabe O gefunden" | OCR erkannte O statt 0 — Validierung greift korrekt, Wert zur manuellen Prüfung markiert |
| Code-Editor zeigt Fehler beim Einfügen | Platzhalter `<azure_document_intelligence_custom_connector>` noch nicht ersetzt |
