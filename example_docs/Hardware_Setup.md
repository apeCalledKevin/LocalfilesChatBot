# Hardware-Aufbau

> Beispieldokument für den Local RAG Chatbot. Das Projekt ist fiktiv und dient nur zum Testen.

## Komponentenliste

| Komponente | Modell | Bemerkung |
|---|---|---|
| Einplatinencomputer | Raspberry Pi 5, 8 GB RAM | |
| KI-Beschleuniger | Raspberry Pi AI HAT+ (Hailo-8L, 13 TOPS) | über PCIe angebunden |
| Kamera | Raspberry Pi Camera Module 3 (Wide) | 12 MP, Autofokus, 120° Sichtfeld |
| Speicher | microSD-Karte 64 GB, A2 | Raspberry Pi OS Bookworm 64-Bit |
| Netzteil | Offizielles 27-W-USB-C-Netzteil (5 V / 5 A) | |
| Kühlung | Active Cooler | unter dem HAT montiert |
| Gehäuse | 3D-gedruckt (PETG) | |

## Anschluss der Kamera

Die Kamera wird über ein **CSI-Flachbandkabel** an den Kameraanschluss **CAM/DISP 0** des Raspberry Pi 5
angeschlossen. Da der Pi 5 schmalere 22-Pin-Anschlüsse hat, wird ein **22-auf-15-Pin-Adapterkabel**
(ca. 200 mm) benötigt.

Wichtig beim Einstecken:

- Pi vorher ausschalten und vom Strom trennen.
- Die Kontakte des Kabels zeigen am Pi 5 **zur USB-/Ethernet-Seite hin**.
- Die Verriegelung des Steckers vorsichtig hochziehen, Kabel einschieben, Verriegelung wieder schließen.

Die Kamera wird beim Booten automatisch erkannt. Test mit:

```bash
rpicam-hello --timeout 5000
```

## Montage des AI HAT+

1. Active Cooler auf den Pi 5 montieren.
2. Den 16-poligen PCIe-Flachbandkabel-Anschluss des HAT mit dem PCIe-Port des Pi verbinden.
3. Abstandshalter (im Lieferumfang) einschrauben und das HAT auf den GPIO-Header stecken.
4. In `/boot/firmware/config.txt` PCIe Gen 3 aktivieren:

```ini
dtparam=pciex1_gen=3
```

5. Treiber installieren und neu starten:

```bash
sudo apt install hailo-all
sudo reboot
```

Erfolgreiche Erkennung prüfen mit `hailortcli fw-control identify`.

## Stromversorgung

Unter Volllast (Inferenz + Kamera + WLAN) zieht das System ca. 12 W.
Mit schwächeren Netzteilen (z. B. 15 W) kam es zu Unterspannungswarnungen und Throttling,
deshalb ist das offizielle 27-W-Netzteil Pflicht.
