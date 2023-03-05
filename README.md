# Hazay Controller

### Setup

1. Assemble the controller (BLE, Pico, HX711)
2. Connecto Pico via USB to Thonny
3. Install micropython
4. Create `id_version` file with id and version
5. Copy `main.py` to Pico
6. Start Pico
7. Connect to Pico with BLE, the name can be like `BLE-Waveshare...` after connecting for the first time the name will be reset to `hazay_{id}_{version}`
8. Connect to scale unit, mount on bike
9. Use app to tare and scale the sensor

### Docs

- [4x50kg load cells with HX711 (setup overview)](https://circuitjournal.com/50kg-load-cells-with-HX711)

### Circuit

| Cable Color | Pico Pin | HX711 Pin |
| ----------- | -------- | --------- |
| Red         | VBUS     | VCC       |
| Black       | GND      | GND       |
| Yellow      | GP4      | SCK       |
| Orange      | GP5      | DT        |
| Blue        |          | E+        |
| White       |          | E-        |
| Green       |          | A-        |
| Purple      |          | A+        |
