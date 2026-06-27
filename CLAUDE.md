# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An Arduino sketch that drives a prayer-call (Azan) clock. It reads the date/time from a
DS3231 RTC, looks up the five daily prayer times from a hard-coded yearly table, and drives an
N-channel MOSFET HIGH for a configurable duration when a prayer time is reached (powering an
amplifier). A 16x2 parallel LCD shows the clock and status; four buttons let the user set the
time/date and Azan duration, which persists in EEPROM. A physical switch forces the output on
(manual mode). A hardware reset button connects directly to the RST pin — no firmware needed.

## Build / flash / debug

There is no build system — built and uploaded with the Arduino IDE (or `arduino-cli`). No tests.

- Open `Azan.ino` in the Arduino IDE; `prayer_times.h` is included automatically (same folder).
- Required libraries: `RTClib` (Adafruit), plus the bundled `Wire`, `LiquidCrystal`, `EEPROM`.
- Serial monitor runs at **9600 baud** — logs button states, prayer detection, and Azan
  start/stop every loop. This is the primary debugging channel.
- `arduino-cli` example: `arduino-cli compile --fqbn <board> .` then
  `arduino-cli upload -p <port> --fqbn <board> .`

On boot, `setup()` runs an I2C bus scan (`scanI2C()`) and retries `rtc.begin()` up to 3 times.
If the RTC is not found, the sketch halts forever displaying "RTC Failed! / Check Wiring!" —
it will never reach `loop()`.

## Regenerating the prayer table

`prayer_times.h` is generated data — `manual_prayer_times.py` (Python 3, stdlib only, no deps)
produces it. Run `python manual_prayer_times.py` for an interactive prompt that walks all 365
days and writes a `.h` file with the exact `PrayerTime` struct and `prayer_times[365]` layout
the sketch expects.

- Always emits **365 days** (non-leap, fixed `DAYS_IN_MONTH`) — keep the struct/array shape in
  sync between `prayer_times.h` and the generator if either changes.
- For bulk/scripted generation, edit the data path directly: the writer is `write_header()` and
  per-day data comes from the `entries` list in `main()`. Ctrl-C aborts cleanly.
- `manual_prayer_times.h` is a previously-generated output kept as a reference. Both files use
  `#ifndef PRAYER_TIMES_H` — **they share the same header guard and cannot both be included**.
  Only `prayer_times.h` is `#include`d in `Azan.ino`.

## Target board caveat (important)

The code is internally inconsistent about the target — confirm the board before changing pins:

- Defines ESP32-style I2C pins (`I2C_SDA 21`, `I2C_SCL 22`) but calls `Wire.begin()` **without**
  those args, so they are unused. On Uno/Nano the actual I2C pins are **A4 (SDA) / A5 (SCL)**.
- `EEPROM.read/write` (no `EEPROM.commit`) assumes **AVR**. On ESP32, add `EEPROM.begin(size)`
  and `EEPROM.commit()` after every write, and pass SDA/SCL to `Wire.begin()`.
- Button pins 10–13 and LCD pins 4–9 are AVR/Uno-style. Treat the pin map as Uno-oriented
  unless told otherwise.

## Architecture

Key files:

- **`Azan.ino`** — all firmware logic. Standard Arduino `setup()`/`loop()`.
- **`prayer_times.h`** — `const PrayerTime prayer_times[365]` lookup table, one row per
  calendar day keyed by `{day, month}`, with hour/min for each of the five prayers. Editing
  prayer schedules means editing this array. Generated — see above.
- **`manual_prayer_times.py`** — host-side generator for `prayer_times.h`. Runs on a PC, not
  compiled into firmware.
- **`wiring.md`** — complete hardware pin map for all modules. **Note:** `wiring.md` was written
  when the output device was a relay; the output is now a MOSFET (see Output logic below).

Key flow in `loop()`:

1. Read RTC into global `now` and read manual switch — both happen at the very top, before the
   if/else, so they are current in all modes.
2. Process MODE and SECTION button edges (shared across both modes).
3. **Setting mode** (`settingMode != 0`): SECTION cycles `settingMode` 1→6
   (1=hour, 2=minute, 3=day, 4=month, 5=Azan minutes, 6=Azan seconds); UP increases,
   DOWN decreases. Modes 1–4 write to the RTC via `rtc.adjust()`; modes 5–6 persist via
   `saveAzanLenToEEPROM()`.
4. **Normal display mode** (`settingMode == 0`): `getPrayerTimesForDate(day, month)` does a
   linear scan of the 365-row table. If the current hour:minute exactly matches a prayer, sets
   `azanActive` and drives the MOSFET HIGH. Clears after `getAzanDurationMs()` elapses
   (tracked with `millis()`, not the RTC).
5. After the if/else: MOSFET is reasserted — **manual switch wins** over Azan state.

### Output logic — MOSFET active-HIGH

The sketch drives pin 3 (`RELAY_PIN`, kept as the name in code) to an N-channel MOSFET gate:

- `HIGH` = MOSFET ON = amplifier powered
- `LOW`  = MOSFET OFF = amplifier off

**If the MOSFET module has a built-in inverter/optocoupler** (some boards are active-low like
relay modules), all five `digitalWrite(RELAY_PIN, ...)` calls must be flipped.

### Manual switch

`MANUAL_SWITCH_PIN` (pin 14 = A0) is `INPUT_PULLUP`. Wire the switch between **pin 14 and GND**
— pressing/closing pulls the pin LOW → `manualMode = true` → MOSFET driven HIGH regardless of
prayer schedule. No external resistor needed. The switch state is read at the top of every
`loop()` iteration so it works in both normal and setting modes.

### State & persistence

- Globals: `settingMode`, `azanActive`, `azanStartTime`, `currentAzanName`, `manualMode`.
- Azan duration lives in EEPROM at addresses 0/1/2 (0 = init flag, 1 = minutes, 2 = seconds).
  `loadAzanLenFromEEPROM()` seeds defaults of 5:00 on first boot.
- All five buttons (MODE, SECTION, UP, DOWN, and any future additions) use `INPUT_PULLUP` with
  edge-detected debouncing: HIGH→LOW edge, 120 ms guard on shared `lastButtonEventMs`.
  `lastUpState`/`lastDownState` are updated inside each branch (setting/normal) separately.

### Notable gotchas

- The table covers 365 rows only — **Feb 29 has no entry**, so `getPrayerTimesForDate` returns
  `NULL` on a leap day and no Azan fires.
- Prayer matching is exact-minute. If the device is mid-boot or in setting mode when a prayer
  minute passes, that Azan is missed (no catch-up logic).
- If `azanLenMinutes` and `azanLenSeconds` are both 0 (e.g. EEPROM corrupted to 0:0), the
  duration check `millis() - azanStartTime >= 0` is immediately true on the same loop tick that
  sets `azanActive`, so the Azan fires and ends within one iteration.
- `RELAY_PIN` is the pin name in the code even though the device is now a MOSFET — do not
  confuse the name with the (old) active-low relay logic documented in `wiring.md`.
- LCD strings mix Arabic and English; keep new user-facing strings ≤16 chars and space-pad to
  16 to clear leftover characters (the code clears lines by printing 16 spaces before writing).
