# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An Arduino sketch that drives a prayer-call (Azan) clock. It reads the date/time from a
DS3231 RTC, looks up the five daily prayer times from a hard-coded yearly table, and pulls a
relay LOW (active-low) for a configurable duration when a prayer time is reached. A 16x2
parallel LCD shows the clock and status; four buttons let the user set the time/date and the
Azan duration, which persists in EEPROM. A physical switch forces the relay on (manual mode).

## Build / flash / debug

There is no build system in the repo — this is built and uploaded with the Arduino IDE (or
`arduino-cli`). There are no tests.

- Open `Azan.ino` in the Arduino IDE; `prayer_times.h` is included automatically (same folder).
- Required libraries: `RTClib` (Adafruit), plus the bundled `Wire`, `LiquidCrystal`, `EEPROM`.
- Serial monitor runs at **9600 baud** — the sketch logs button states, prayer detection, and
  Azan start/stop here every loop, which is the primary debugging channel.
- `arduino-cli` example: `arduino-cli compile --fqbn <board> .` then `arduino-cli upload -p <port> --fqbn <board> .`

## Regenerating the prayer table

`prayer_times.h` is generated data — `manual_prayer_times.py` (Python 3, stdlib only, no deps)
produces it. Run with `python manual_prayer_times.py` for an interactive prompt that walks all
365 days, asking for each of the five prayers' hour/minute, and writes a `.h` file
(default `prayer_times.h`) with the exact same `PrayerTime` struct and `prayer_times[365]` layout
the sketch expects.

- It always emits **365 days** (non-leap, fixed `DAYS_IN_MONTH`) to match the firmware's table
  size — keep the struct/array shape in `prayer_times.h` and the generator in sync if either
  changes (the `.ino` reads these field names directly).
- The interactive flow is tedious by design (a `Press Enter` between every day). For bulk/scripted
  generation, prefer editing the data path: the writer is `write_header()` and the per-day data
  comes from the `entries` list built in `main()`. Ctrl-C aborts cleanly.

## Target board caveat (important)

The code is internally inconsistent about the target and this matters before changing pins:
- It defines ESP32-style I2C pins (`I2C_SDA 21`, `I2C_SCL 22`) and calls `Wire.setClock` /
  `Wire.setTimeout`, but `Wire.begin()` in `setup()` is called **without** the SDA/SCL args, so
  those `#define`s are currently unused.
- Comments and `EEPROM.read/write` (no `EEPROM.commit`) assume an **AVR** board (e.g. Uno/Mega),
  where EEPROM is real and exceptions are disabled.
- Button pins 10–13 and LCD pins 4–9 are AVR/Uno-style assignments.

Before retargeting or relying on a pin, confirm the actual board: if it is an ESP32, EEPROM
writes need `EEPROM.begin(size)` + `EEPROM.commit()`, and pins 10–14 may not exist/behave the
same. Treat the current pin map as Uno-oriented unless the user says otherwise.

## Architecture

Three files:

- **`Azan.ino`** — all firmware logic. Standard Arduino `setup()`/`loop()`.
- **`prayer_times.h`** — a `const PrayerTime prayer_times[365]` lookup table, one row per
  calendar day, keyed by `{day, month}` with hour/min fields for each of the five prayers.
  This is the data source; editing prayer schedules means editing this array. **Generated** —
  see "Regenerating the prayer table".
- **`manual_prayer_times.py`** — host-side Python generator for `prayer_times.h`. Not compiled
  into the firmware; runs on a PC.

Key flow in `loop()`:
1. Read RTC and all four button states once per iteration.
2. **Setting mode** (`settingMode != 0`): MODE button toggles in/out; SECTION button cycles
   `settingMode` 1→6 (1=hour, 2=minute, 3=day, 4=month, 5=Azan minutes, 6=Azan seconds);
   UP/DOWN adjust. Modes 1–4 write back to the RTC via `rtc.adjust(...)`; modes 5–6 persist via
   `saveAzanLenToEEPROM()`.
3. **Normal display mode** (`settingMode == 0`): look up today's row with
   `getPrayerTimesForDate(day, month)` (linear scan of the table). If current hour:minute exactly
   matches a prayer, set `azanActive` and pull the relay LOW; clear it after
   `getAzanDurationMs()` elapses (uses `millis()`, not the RTC, for duration).
4. After the branch, the relay is reasserted: **manual switch (HIGH) wins** over Azan state.

Relay logic is **active-low**: `LOW` = on, `HIGH` = off.

### State & persistence
- Global flags drive everything: `settingMode`, `azanActive`, `azanStartTime`,
  `currentAzanName`, `manualMode`.
- Azan duration (`azanLenMinutes`, `azanLenSeconds`) lives in EEPROM at addresses 0/1/2
  (0 = init flag, 1 = minutes, 2 = seconds). `loadAzanLenFromEEPROM()` seeds defaults of 5:00
  on first boot.
- Buttons use edge-detected debouncing: compare against `lastXxxState` with a `debounceMs` (120ms)
  guard on `lastButtonEventMs`. MODE is wired active-high-idle in code (`INPUT_PULLUP`, edge
  HIGH→LOW); preserve this pattern when adding buttons.

### Notable conventions / gotchas
- Comments and LCD/Serial strings mix Arabic and English; keep new user-facing strings short
  (LCD is 16 chars wide — lines are space-padded to clear) and follow the existing bilingual style.
- The table only covers 365 rows — **Feb 29 has no entry**, so `getPrayerTimesForDate` returns
  `NULL` on a leap day and no Azan fires.
- Prayer matching is exact-minute; if the device misses that minute (e.g. mid-setting), the Azan
  for that prayer won't trigger.
