# Objekterkennung auf dem Raspberry Pi 5

> Beispieldokument für den Local RAG Chatbot. Das Projekt ist fiktiv und dient nur zum Testen.

## Ziel des Projekts

Ein Raspberry Pi 5 soll in Echtzeit Personen, Fahrräder und Autos in einem Kamerabild erkennen.
Die Ergebnisse (Klasse, Konfidenz, Bounding Box) werden per MQTT an einen zentralen Server gesendet.
Zielwert sind mindestens 25 FPS bei einer Auflösung von 640×640 Pixeln.

## Wahl des KI-Beschleunigers

Zur Auswahl standen der **Google Coral USB Accelerator** und das **Raspberry Pi AI HAT+ mit Hailo-8L**.

Entschieden wurde sich für das **Hailo AI HAT+**, aus folgenden Gründen:

- **Rechenleistung:** Der Hailo-8L liefert 13 TOPS, der Coral Edge TPU nur 4 TOPS.
- **Anbindung:** Das AI HAT+ wird direkt über PCIe Gen 3 angebunden. Der Coral hängt am USB-Bus,
  der sich die Bandbreite mit der Kamera-Pipeline und dem Netzwerk teilt.
- **Software-Support:** Hailo wird offiziell von Raspberry Pi unterstützt und ist in `rpicam-apps`
  integriert. Die Coral-Bibliotheken (`pycoral`) werden kaum noch gepflegt und unterstützen
  aktuelle Python-Versionen nicht offiziell.
- **Modelle:** YOLOv8 lässt sich für Hailo kompilieren, ohne das Modell auf die
  eingeschränkten Operationen der Edge TPU anpassen zu müssen.

Nachteil des Hailo-Moduls: Es ist etwas teurer (ca. 70 € statt ca. 60 €) und belegt den GPIO-Header,
weshalb für weitere Sensoren ein Stacking-Header nötig ist.

## Verwendetes Modell

- Modell: **YOLOv8s**, vortrainiert auf COCO
- Eingabegröße: 640×640
- Format: `.hef` (Hailo Executable Format), erstellt mit dem Hailo Dataflow Compiler
- Erreichte Leistung: ca. 30 FPS bei rund 35 ms Latenz pro Bild
- Konfidenz-Schwellwert: 0,5; NMS-IoU-Schwellwert: 0,45

## Software-Pipeline

1. Kamera liefert Frames über `picamera2`
2. Vorverarbeitung (Skalierung auf 640×640, Letterboxing)
3. Inferenz auf dem Hailo-8L
4. Nachverarbeitung (NMS, Filterung auf die Klassen `person`, `bicycle`, `car`)
5. Versand der Ergebnisse als JSON über MQTT an das Topic `detections/cam01`
