# Wiring Guide — Azan Prayer Clock

This document lists every module/button in the firmware and exactly which Arduino pin it
connects to. The pin assignments are taken directly from `Azan.ino`.

> **Board: Arduino Mega 2560.**
> On a Mega, hardware I2C is on pins 20 (SDA) / 21 (SCL) and hardware SPI is on pins
> 50 (MISO) / 51 (MOSI) / 52 (SCK) / 53 (SS). These are **different from Uno/Nano**
> (which use A4/A5 for I2C and 11/12/13 for SPI). Wiring the SD card to the Uno SPI pins
> (11/12/13) is the most common cause of "SD card not found" on a Mega.

---

## Pin map at a glance

| Module / Control          | Signal      | Arduino Mega Pin | Pin mode in code       |
|---------------------------|-------------|------------------|------------------------|
| **DS3231 RTC**            | SDA         | 20               | Hardware I2C           |
|                           | SCL         | 21               | Hardware I2C           |
|                           | VCC         | 5 V              | —                      |
|                           | GND         | GND              | —                      |
| **16×2 LCD (parallel)**   | RS          | 8                | OUTPUT                 |
|                           | E (Enable)  | 9                | OUTPUT                 |
|                           | D4          | 4                | OUTPUT                 |
|                           | D5          | 5                | OUTPUT                 |
|                           | D6          | 6                | OUTPUT                 |
|                           | D7          | 7                | OUTPUT                 |
| **MOSFET (Azan output)**  | Gate (IN)   | 3                | OUTPUT (active-HIGH)   |
| **SD card module**        | CS          | 10               | OUTPUT                 |
|                           | MOSI        | **51**           | Hardware SPI           |
|                           | MISO        | **50**           | Hardware SPI           |
|                           | SCK         | **52**           | Hardware SPI           |
|                           | VCC         | 5 V (or 3.3 V)   | —                      |
|                           | GND         | GND              | —                      |
| **Button: MODE**          | signal      | 2                | INPUT_PULLUP           |
| **Button: SECTION**       | signal      | A1 (pin 55)      | INPUT_PULLUP           |
| **Button: UP**            | signal      | A2 (pin 56)      | INPUT_PULLUP           |
| **Button: DOWN**          | signal      | A3 (pin 57)      | INPUT_PULLUP           |
| **Manual switch**         | signal      | A0 (pin 54)      | INPUT_PULLUP, active-LOW |
| **Reset button**          | —           | RST pin → GND    | Hardware reset, no firmware needed |

---

## 1. DS3231 RTC (clock module) — I2C

Provides the date/time. Uses the hardware I2C bus.

| RTC pin | Arduino Mega pin |
|---------|------------------|
| VCC     | 5 V              |
| GND     | GND              |
| SDA     | **20**           |
| SCL     | **21**           |

Notes:
- On a Mega, SDA = pin 20 and SCL = pin 21 — these are the only hardware-I2C pins.
- `Wire.begin()` is called without arguments; on Mega it automatically uses pins 20/21.
- The DS3231 board has its own pull-up resistors and coin-cell backup — no extra components needed.
- SQW/32K pins are not used — leave them unconnected.
- On boot the sketch scans the I2C bus and retries the RTC 3×; "RTC Failed! / Check Wiring!"
  on the LCD means SDA/SCL/power are wrong.

---

## 2. 16×2 LCD — 4-bit parallel (HD44780, not I2C)

Driven directly with `LiquidCrystal lcd(8, 9, 4, 5, 6, 7)` → order is `(RS, E, D4, D5, D6, D7)`.

| LCD pin | Name          | Connect to                                               |
|---------|---------------|----------------------------------------------------------|
| 1       | VSS           | GND                                                      |
| 2       | VDD           | 5 V                                                      |
| 3       | V0 (contrast) | Wiper of a 10 kΩ potentiometer (ends to 5 V / GND)      |
| 4       | RS            | Arduino pin **8**                                        |
| 5       | RW            | GND (write-only)                                         |
| 6       | E             | Arduino pin **9**                                        |
| 7–10    | D0–D3         | Not connected (4-bit mode)                               |
| 11      | D4            | Arduino pin **4**                                        |
| 12      | D5            | Arduino pin **5**                                        |
| 13      | D6            | Arduino pin **6**                                        |
| 14      | D7            | Arduino pin **7**                                        |
| 15      | A (LED+)      | 5 V through ~220 Ω resistor for backlight                |
| 16      | K (LED−)      | GND                                                      |

Notes:
- **RW (pin 5) must go to GND** — the library only writes to the display.
- Use a 10 kΩ pot on V0 (pin 3) for contrast; blank but backlit screen → adjust this first.

---

## 3. SD card module — SPI

**Critical for Mega:** the hardware SPI bus is on pins 50/51/52, not 11/12/13 (Uno).
Wiring to the wrong pins is the most common cause of `SD: No card or wiring error`.

| SD module pin | Arduino Mega pin | Notes                                    |
|---------------|------------------|------------------------------------------|
| CS (SS)       | **10**           | Set as OUTPUT by firmware                |
| MOSI          | **51**           | Hardware SPI — must use this pin         |
| MISO          | **50**           | Hardware SPI — must use this pin         |
| SCK (CLK)     | **52**           | Hardware SPI — must use this pin         |
| VCC           | 5 V or 3.3 V     | Match to your module's voltage rating    |
| GND           | GND              |                                          |

Notes:
- SD module CS is on pin **10** (a regular digital output). Pin 53 (Mega's hardware SS) is
  internally managed by the SPI library and does not need to be connected to the module.
- Most SD modules have an onboard 3.3 V regulator and level shifter — connect VCC to 5 V.
  If your module has no regulator (bare breakout), use the 3.3 V pin instead.
- The SD card must be formatted as **FAT32** (not exFAT). Use SD Card Formatter or Windows
  right-click → Format → FAT32. The firmware will print `SD: Card found but no FAT —
  reformat as FAT32` on the serial monitor if the format is wrong.
- Place `PTIMES.CSV` in the root directory of the card (not inside any folder).

---

## 4. MOSFET (Azan output) — active-HIGH

The firmware drives pin 3 HIGH to turn the amplifier on and LOW to turn it off.

| MOSFET module pin | Connect to         |
|-------------------|--------------------|
| VCC               | 5 V                |
| GND               | GND                |
| IN (Gate)         | Arduino pin **3**  |

Logic:
- `HIGH` on pin 3 = MOSFET ON = amplifier powered (Azan playing or manual mode).
- `LOW` on pin 3 = MOSFET OFF = amplifier off.

> If your MOSFET module has a built-in optocoupler/inverter (active-LOW), flip all five
> `digitalWrite(RELAY_PIN, …)` calls in `Azan.ino`.

---

## 5. Buttons (4×) — setting the clock & Azan duration

All four use `INPUT_PULLUP`. Wire each button between its Arduino pin and **GND**.
No external resistors needed. Idle = HIGH; pressing pulls LOW (edge-detected, 120 ms debounce).

| Button   | Arduino Mega pin | Function                                                         |
|----------|------------------|------------------------------------------------------------------|
| MODE     | **2**            | Enter / exit setting mode                                        |
| SECTION  | **A1** (pin 55)  | Cycle field: hour → minute → day → month → Azan-min → Azan-sec  |
| UP       | **A2** (pin 56)  | Increase the selected value                                      |
| DOWN     | **A3** (pin 57)  | Decrease the selected value                                      |

```
Arduino pin ──┤ push-button ├── GND
```

---

## 6. Manual override switch

Forces the amplifier ON regardless of prayer schedule. Uses `INPUT_PULLUP` — connect the
switch between **A0 and GND**. No external resistor needed.

| Switch terminal | Connect to              |
|-----------------|-------------------------|
| One side        | Arduino pin **A0** (54) |
| Other side      | GND                     |

- Switch open (idle) → pin reads HIGH → manual mode OFF.
- Switch closed → pin pulled LOW → manual mode ON → MOSFET driven HIGH.

```
Arduino A0 ──┤ switch ├── GND
```

---

## 7. Hardware reset button

A physical button between the **RST** pin and **GND**. No firmware changes needed —
pressing it performs a full hardware reset.

```
RST ──┤ push-button ├── GND
```

---

## Power & ground

- Power the Mega from USB or a regulated 5 V supply (Vin pin accepts 7–12 V).
- **All modules share a common GND** with the Mega — RTC, LCD, MOSFET, SD module,
  buttons, and manual switch all return to the same ground.
- If you power the SD module from the Mega's 5 V pin and add the LCD, make sure your
  supply can handle the combined current (typically 200–300 mA total).
