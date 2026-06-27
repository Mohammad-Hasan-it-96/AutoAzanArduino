# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An Arduino sketch that drives a prayer-call (Azan) clock. It reads the date/time from a
DS3231 RTC, looks up the five daily prayer times from either an SD card file (`PTIMES.CSV`)
or a hard-coded yearly table (`prayer_times.h`), and drives an N-channel MOSFET HIGH for a
configurable duration when a prayer time is reached (powering an amplifier). A 16×2 parallel
LCD shows the clock and status; four buttons let the user set the time/date and Azan duration,
which persists in EEPROM. A physical switch forces the output on (manual mode). A hardware
reset button connects directly to the RST pin — no firmware needed.

## Build / flash / debug

There is no build system — built and uploaded with the Arduino IDE (or `arduino-cli`). No tests.

- Open `Azan.ino` in the Arduino IDE; `prayer_times.h` is included automatically (same folder).
- **Target board: Arduino Mega 2560.**
- Required libraries: `RTClib` (Adafruit), plus the bundled `Wire`, `LiquidCrystal`, `EEPROM`, `SPI`, `SD`.
- Serial monitor runs at **9600 baud** — logs button states, SD card status, prayer detection,
  and Azan start/stop every loop. This is the primary debugging channel.
- `arduino-cli` example: `arduino-cli compile --fqbn arduino:avr:mega .` then
  `arduino-cli upload -p <port> --fqbn arduino:avr:mega .`

On boot, `setup()` runs an I2C bus scan (`scanI2C()`) and retries `rtc.begin()` up to 3 times.
If the RTC is not found, the sketch halts forever displaying "RTC Failed! / Check Wiring!" —
it will never reach `loop()`.

## Pin assignments (Arduino Mega 2560)

```
BTN_MODE          = 2       INPUT_PULLUP, active-LOW
BTN_SECTION       = A1      INPUT_PULLUP, active-LOW
BTN_UP            = A2      INPUT_PULLUP, active-LOW
BTN_DOWN          = A3      INPUT_PULLUP, active-LOW
RELAY_PIN         = 3       OUTPUT, N-channel MOSFET gate (active-HIGH)
MANUAL_SWITCH_PIN = 14      INPUT_PULLUP, active-LOW (Mega digital pin 14 = TX3)
SD_CS_PIN         = 53      OUTPUT, SD card chip select (Mega hardware SS pin)
LCD               = RS:8, E:9, D4:4, D5:5, D6:6, D7:7
RTC I2C           = SDA:20, SCL:21  (Wire.begin() without args uses these on Mega)
SD SPI            = MOSI:51, MISO:50, SCK:52, CS:53
```

Buttons were moved from pins 10–13 to D2/A1/A2/A3 to free the hardware SPI bus for the SD
card module. `I2C_SDA 21` / `I2C_SCL 22` are defined in the code but unused — `Wire.begin()`
without arguments automatically uses pins 20/21 on Mega.

## SD card prayer times

At boot, `setup()` calls `SD.begin(SD_CS_PIN)`. On success, `loadTodayFromSD()` reads only
the single matching line from `PTIMES.CSV` (not all 365 rows) to stay within SRAM limits.
On SD failure, a low-level `Sd2Card` + `SdVolume` check distinguishes wiring errors from
format errors and prints a specific message to serial and LCD.

### PTIMES.CSV format

No header row — one line per day, 365 lines total:

```
day,month,fajr_h,fajr_m,dhuhr_h,dhuhr_m,asr_h,asr_m,maghrib_h,maghrib_m,isha_h,isha_m
```

- File must be in the **root directory** of a **FAT32**-formatted card (not exFAT).
- After copying to the SD card, **safely eject** before removing — file size 0 after copying
  is the most common cause of "Date not found" and means the OS did not flush the write.
- `loadTodayFromSD()` uses `file.read() == -1` for EOF detection, not `file.available()`.
  Do not revert to `file.available()` — it returned 0 on this SD module even for non-empty files.

### Fallback chain

1. SD card entry for today → use it
2. SD unavailable / file missing / date not in file → fall back to `prayer_times.h`
3. Date not in `prayer_times.h` (e.g. Feb 29 leap day) → `NULL` → no Azan fires

### SD serial diagnostics

- `SD: File size: 0` — file on card is empty; re-copy and safely eject
- `SD: No card or wiring error` — MOSI/MISO/CS/power wrong
- `SD: Card found but no FAT` — reformat card as FAT32
- First 3 parsed lines are printed on each `loadTodayFromSD()` call for content verification

## Regenerating the prayer table

`prayer_times.h` and `PTIMES.CSV` are generated data. `manual_prayer_times.py` (Python 3,
stdlib only, no deps) produces both. Run:

```
python manual_prayer_times.py
```

Interactive prompt walks all 365 days. Outputs `prayer_times.h` (firmware fallback) and
`PTIMES.CSV` (copy to SD card root).

- Always emits **365 days** (non-leap, fixed `DAYS_IN_MONTH`) — keep struct/array shape in
  sync between `prayer_times.h` and the generator if either changes.
- `manual_prayer_times.h` is a previously-generated reference. Both files use
  `#ifndef PRAYER_TIMES_H` — **they share the same header guard and cannot both be included**.
  Only `prayer_times.h` is `#include`d in `Azan.ino`.

## Architecture

Key files:

- **`Azan.ino`** — all firmware logic. Standard Arduino `setup()`/`loop()`.
- **`prayer_times.h`** — `const PrayerTime prayer_times[365]` lookup table, one row per
  calendar day keyed by `{day, month}`. SD card data takes priority; this is the fallback.
- **`PTIMES.CSV`** — SD card prayer times; updated annually by replacing the file on the card.
- **`manual_prayer_times.py`** — host-side generator for `prayer_times.h` and `PTIMES.CSV`.
- **`wiring.md`** — complete hardware pin map for the Mega.

Key flow in `loop()`:

1. Read RTC into global `now` and read manual switch — both at the very top, before the
   if/else, so they are current in all modes.
2. Process MODE and SECTION button edges (shared across both modes).
3. **Setting mode** (`settingMode != 0`): SECTION cycles `settingMode` 1→6
   (1=hour, 2=minute, 3=day, 4=month, 5=Azan minutes, 6=Azan seconds); UP increases,
   DOWN decreases. Modes 1–4 write to the RTC via `rtc.adjust()`; modes 5–6 persist via
   `saveAzanLenToEEPROM()`.
4. **Normal display mode** (`settingMode == 0`): if SD is available and the date has changed
   since last load, `loadTodayFromSD()` reloads (handles midnight rollover).
   `getPrayerTimesForDate()` checks SD entry first, then scans `prayer_times[365]`. If the
   current hour:minute exactly matches a prayer, sets `azanActive` and drives MOSFET HIGH.
   Clears after `getAzanDurationMs()` elapses (tracked with `millis()`, not the RTC).
5. After the if/else: MOSFET is reasserted — **manual switch wins** over Azan state.

### Output logic — MOSFET active-HIGH

The sketch drives pin 3 (`RELAY_PIN`, legacy name) to an N-channel MOSFET gate:

- `HIGH` = MOSFET ON = amplifier powered
- `LOW`  = MOSFET OFF = amplifier off

If the MOSFET module has a built-in inverter/optocoupler (active-low), all five
`digitalWrite(RELAY_PIN, ...)` calls must be flipped.

### Manual switch

`MANUAL_SWITCH_PIN` (pin 14) is `INPUT_PULLUP`. Wire the switch between **pin 14 and GND**.
Closing the switch pulls LOW → `manualMode = true` → MOSFET driven HIGH regardless of prayer
schedule. No external resistor needed. Read at the top of every `loop()` — works in both
normal and setting modes.

Note: on Mega, digital pin 14 is TX3 (USART3 TX). If USART3 serial is ever needed, move the
manual switch to a different pin and update `MANUAL_SWITCH_PIN`.

### State & persistence

- Globals: `settingMode`, `azanActive`, `azanStartTime`, `currentAzanName`, `manualMode`.
- SD state: `sdCardAvailable`, `todayFromSD`, `todaySDLoaded`, `lastLoadedDay`, `lastLoadedMonth`.
- Azan duration lives in EEPROM at addresses 0/1/2 (0 = init flag, 1 = minutes, 2 = seconds).
  `loadAzanLenFromEEPROM()` seeds defaults of 5:00 on first boot.
- All buttons use `INPUT_PULLUP` with edge-detected debouncing: HIGH→LOW edge, 120 ms guard
  on shared `lastButtonEventMs`. `lastUpState`/`lastDownState` are updated inside each branch
  (setting/normal) separately.

### Notable gotchas

- The table covers 365 rows only — **Feb 29 has no entry**, so `getPrayerTimesForDate` returns
  `NULL` on a leap day and no Azan fires.
- Prayer matching is exact-minute. If the device is mid-boot or in setting mode when a prayer
  minute passes, that Azan is missed (no catch-up logic).
- If `azanLenMinutes` and `azanLenSeconds` are both 0 (EEPROM corrupted to 0:0), the Azan
  fires and ends within one loop iteration.
- `RELAY_PIN` is the legacy pin name — the device is a MOSFET, not a relay. Active-HIGH,
  not active-LOW.
- LCD strings: keep ≤16 chars and space-pad to 16 to clear leftover characters.
