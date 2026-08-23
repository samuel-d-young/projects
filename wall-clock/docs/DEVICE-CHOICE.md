# Which board for what

Verified against ESPHome 2026.8.0 source, not docs summaries.

## Short answer

| Build | Board | Verdict |
|---|---|---|
| 24-LED test clock, ring only | **D1 mini (ESP8266)** | Works. Use `test-clock-d1mini.yaml`. |
| Ring + 360×360 round display | **ESP32-S3-N16R8** | Works. Use `test-clock-s3-round.yaml`. |
| Ring + display on a D1 mini | — | **Impossible.** Not a tuning problem. |
| Ring + display on a plain ESP32 | — | **Refused at compile time.** |

## Why the display cannot run on the D1 mini

A 360×360 RGB565 framebuffer is 360 × 360 × 2 = **259,200 bytes = 253 KB**.

| Board | Available | Result |
|---|---|---|
| D1 mini / NodeMCU (ESP8266) | ~30 KB heap | short by 223 KB |
| ESP32, no PSRAM | ~160 KB heap | short by 93 KB |
| **ESP32-S3-N16R8, 8 MB PSRAM** | 8192 KB | fits easily |

And it is enforced, not merely tight. ESPHome's ST77916 model at
`esphome/components/mipi_spi/models/st77916.py` (tag 2026.8.0) declares:

```python
DriverChip(
    "ESP-VOCAT",
    width=360, height=360,
    bus_mode=TYPE_QUAD,
    data_rate="80MHz",
    invert_colors=True,
    requires={"psram"},        # <-- config validation fails without it
    initsequence=_ESP_VOCAT_INIT,
)
```

`requires={"psram"}` means a config without PSRAM **will not compile**. The
N16R8's 8 MB of octal PSRAM is exactly the part that satisfies it.

> The ESPHome docs page for `mipi_spi` does **not** list ST77916 among its
> models. That listing is stale — the model file is there in the source at
> 2026.8.0. Checking the source rather than the docs is the only reason this
> project isn't now telling you to buy a different panel.

## Pins are the risk, not the chip

`model: ESP-VOCAT` ships the init sequence **and default pins for the ESP-VoCat
v1.2 board** — that is where Espressif's init data came from. A generic
Waveshare or Guition 1.85" module is wired differently. The GPIOs in
`test-clock-s3-round.yaml` are the ESP-VoCat reference values, exposed as
substitutions at the top of the file. **Get your module's pinout and correct
them before flashing.**

If your panel needs a different init sequence entirely, `mipi_spi` also accepts
`model: CUSTOM` with your own `init_sequence:`.

## ESP8266 is not deprecated

2026.1 moved ESP8266 to ESP-IDF: roughly 40% smaller binaries and free heap up
from under 10 K to over 30 K. That improvement is what makes the D1 mini config
viable at all.

Two ESP8266 specifics that bite:

- **`neopixelbus`, not `esp32_rmt_led_strip`.** The latter is ESP32-only. The
  2026.6 `neopixelbus` deprecation was **ESP32-only** — ESP8266 is unaffected.
- **The LED method is a real trade-off.** `esp8266_dma` is rock solid but is
  locked to GPIO3, which is UART0 RX, so you lose serial logging and must set
  `logger: baud_rate: 0`. The config ships `bit_bang` on GPIO4/D2 so serial
  logging works during first flash — at 24 LEDs the ~720 µs of disabled
  interrupts is not a problem. Switch to DMA if you see flicker.
