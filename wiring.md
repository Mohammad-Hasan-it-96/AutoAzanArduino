# Wiring Guide — Azan Prayer Clock

This document lists every module/button in the firmware and exactly which Arduino pin it
connects to. The pin assignments are taken directly from `Azan.ino`.

> **Board assumption: Arduino Uno / Nano / Pro Mini (AVR, 5 V).**
> The sketch contains ESP32-style `#define I2C_SDA 21` / `I2C_SCL 22`, but `Wire.begin()` is
> called **without** arguments, so those defines are unused — the RTC uses the board's default
> hardware-I2C pins (A4/A5 on a Uno). The button (10–13), LCD (4–9) and manual-switch (14 = A0)
> pins are all standard Uno digital/analog pins. If you are on a different board, re-map
> accordingly (see notes at the bottom).

---

## Pin map at a glance

| Module / Control        | Signal      | Arduino Pin | Pin mode in code      |
|-------------------------|-------------|-------------|-----------------------|
| **DS3231 RTC**          | SDA         | A4          | Hardware I2C          |
|                         | SCL         | A5          | Hardware I2C          |
|                         | VCC         | 5 V         | —                     |
|                         | GND         | GND         | —                     |
| **16x2 LCD (parallel)** | RS          | 8           | OUTPUT                |
|                         | E (Enable)  | 9           | OUTPUT                |
|                         | D4          | 4           | OUTPUT                |
|                         | D5          | 5           | OUTPUT                |
|                         | D6          | 6           | OUTPUT                |
|                         | D7          | 7           | OUTPUT                |
| **Relay module**        | IN          | 3           | OUTPUT (active-LOW)   |
| **Button: MODE**        | signal      | 10          | INPUT_PULLUP          |
| **Button: SECTION**     | signal      | 11          | INPUT_PULLUP          |
| **Button: UP**          | signal      | 12          | INPUT_PULLUP          |
| **Button: DOWN**        | signal      | 13          | INPUT_PULLUP          |
| **Manual switch**       | signal      | 14 (A0)     | INPUT (active-HIGH)   |

---

## 1. DS3231 RTC (clock module) — I2C

Provides the date/time. Uses the I2C bus.

| RTC pin | Arduino Uno pin |
|---------|-----------------|
| VCC     | 5 V             |
| GND     | GND             |
| SDA     | A4              |
| SCL     | A5              |

Notes:
- On a Uno/Nano, A4 = SDA and A5 = SCL — these are the only hardware-I2C pins; you cannot move them.
- The DS3231 board has its own pull-up resistors and coin-cell backup, so no extra components are needed.
- SQW/32K pins are not used by the firmware — leave them unconnected.
- On boot the sketch scans the I2C bus and retries the RTC 3× (watch the 9600-baud serial
  monitor); "RTC Failed! / Check Wiring!" on the LCD means SDA/SCL/power are wrong.

## 2. 16x2 LCD — 4-bit parallel (HD44780, **not** I2C)

Driven directly with `LiquidCrystal lcd(8, 9, 4, 5, 6, 7)` → order is `(RS, E, D4, D5, D6, D7)`.

| LCD pin | Name        | Connect to                                    |
|---------|-------------|-----------------------------------------------|
| 1       | VSS         | GND                                           |
| 2       | VDD         | 5 V                                           |
| 3       | V0 (contrast)| Wiper of a 10 kΩ potentiometer (ends to 5 V / GND) |
| 4       | RS          | Arduino pin **8**                             |
| 5       | RW          | GND (write-only)                              |
| 6       | E           | Arduino pin **9**                             |
| 7–10    | D0–D3       | Not connected (4-bit mode)                    |
| 11      | D4          | Arduino pin **4**                             |
| 12      | D5          | Arduino pin **5**                             |
| 13      | D6          | Arduino pin **6**                             |
| 14      | D7          | Arduino pin **7**                             |
| 15      | A (LED+)    | 5 V (through ~220 Ω resistor for backlight)   |
| 16      | K (LED-)    | GND                                           |

Notes:
- **RW (pin 5) must go to GND** — the library only writes to the display.
- Use a 10 kΩ pot on V0 (pin 3) for contrast; if the screen is blank but backlit, adjust this first.

## 3. Relay module (the Azan output)

Pulled **LOW to turn ON** (active-low). Drives whatever plays the Azan (amplifier, buzzer, mains
contactor, etc.).

| Relay pin | Connect to        |
|-----------|-------------------|
| VCC       | 5 V               |
| GND       | GND               |
| IN        | Arduino pin **3** |

Logic in firmware:
- `LOW` on pin 3 = relay **ON** (Azan playing).
- `HIGH` on pin 3 = relay **OFF**.
- The relay is set HIGH (off) at startup, turned on when a prayer minute matches, and turned off
  after the configured Azan duration. The **manual switch overrides** and forces it ON.
- The relay's switched side (COM/NO/NC) wires to your load — keep mains wiring isolated and safe.

## 4. Buttons (4×) — setting the clock & Azan duration

All four use `INPUT_PULLUP`, so each button connects between its Arduino pin and **GND**. No
external resistors needed. Idle = HIGH; pressing pulls the pin LOW (edge-detected, 120 ms debounce).

| Button   | Arduino pin | Function                                                        |
|----------|-------------|-----------------------------------------------------------------|
| MODE     | 10          | Enter / exit setting mode                                       |
| SECTION  | 11          | Cycle field: hour → minute → day → month → Azan-min → Azan-sec  |
| UP       | 12          | Increase the selected value                                     |
| DOWN     | 13          | Decrease the selected value                                     |

Wiring each button:

```
Arduino pin (10/11/12/13) ──┤ push-button ├── GND
```

## 5. Manual override switch

A physical switch (e.g. toggle) that forces the relay ON regardless of prayer schedule. Configured
as plain `INPUT` (no internal pull-up), and read as **active-HIGH**.

| Switch terminal | Connect to                       |
|-----------------|----------------------------------|
| One side        | 5 V                              |
| Other side      | Arduino pin **14 (A0)**          |

> Because the pin is `INPUT` with **no pull-up**, add an external **10 kΩ pull-down resistor**
> from pin 14 (A0) to **GND**. This keeps the pin at a defined LOW (manual OFF) when the switch is
> open; closing the switch drives it HIGH (manual ON). Without the pull-down the input floats and
> may trigger manual mode randomly.

```
5V ──┤ switch ├──┬── Arduino pin 14 (A0)
                 │
                10kΩ
                 │
                GND
```

---

## Power & ground

- Power the Arduino from USB or a regulated 5 V supply.
- **All modules share a common GND** with the Arduino — RTC, LCD, relay, buttons and the switch
  pull-down all return to the same ground.
- The relay module can draw a noticeable coil current; if you switch a heavy/mains load, power the
  relay board from a supply that can handle it and keep mains wiring isolated.

## If you are NOT on a Uno/Nano

- **ESP32:** `I2C_SDA 21` / `I2C_SCL 22` would then apply, but you must also add
  `Wire.begin(I2C_SDA, I2C_SCL)` in `setup()`. EEPROM needs `EEPROM.begin(size)` + `EEPROM.commit()`.
  Digital pins 10–14 and 4–9 differ on the ESP32 — re-check every assignment before wiring.
- **Mega:** the digital pins 3–13 exist and behave the same; I2C is on pins 20 (SDA) / 21 (SCL),
  and pin 14 is a real digital pin (not A0). Adjust the RTC and manual-switch wiring accordingly.

Always confirm the target board before relying on any pin number above.
