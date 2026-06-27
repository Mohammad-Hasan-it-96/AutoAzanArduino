#include <Wire.h>
#include <RTClib.h>
#include <LiquidCrystal.h>
#include <EEPROM.h>
#include <SPI.h>
#include <SD.h>
#include "prayer_times.h"

// I2C (ESP32-style defines kept; Wire.begin() uses board defaults — A4/A5 on Uno)
#define I2C_SDA  21
#define I2C_SCL  22
#define I2C_FREQ 100000

// Buttons moved to A1-A3 and D2 to free SPI bus (pins 10-13) for SD card
#define BTN_MODE     2
#define BTN_SECTION  A1
#define BTN_UP       A2
#define BTN_DOWN     A3

// Output and switches
#define RELAY_PIN         3   // N-channel MOSFET gate — active-high: HIGH = amplifier on
#define MANUAL_SWITCH_PIN 14  // INPUT_PULLUP; switch to GND → LOW = manual on
#define SD_CS_PIN         53  // SD card chip select

int settingMode = 0;
DateTime now;
LiquidCrystal lcd(8, 9, 4, 5, 6, 7);
RTC_DS3231 rtc;

// Button state tracking
int lastModeState    = LOW;
int lastSectionState = HIGH;
int lastUpState      = HIGH;
int lastDownState    = HIGH;
unsigned long lastButtonEventMs = 0;
const unsigned long debounceMs  = 120;
bool manualMode = false;

const char* PRAYER_NAMES[5] = { "Fajr", "Dhuhr", "Asr", "Maghrib", "Isha" };

// ── SD card prayer-times ──────────────────────────────────────────────────────
bool sdCardAvailable = false;
PrayerTime todayFromSD;          // holds the single loaded entry
bool       todaySDLoaded  = false;
int        lastLoadedDay   = -1;
int        lastLoadedMonth = -1;

// Read PTIMES.CSV from SD and store the entry for (day, month).
// File format — no header, one line per day:
//   day,month,fajr_h,fajr_m,dhuhr_h,dhuhr_m,asr_h,asr_m,maghrib_h,maghrib_m,isha_h,isha_m
bool loadTodayFromSD(uint8_t day, uint8_t month) {
  if (!sdCardAvailable) return false;

  Serial.print(F("SD: Looking for day=")); Serial.print(day);
  Serial.print(F(" month=")); Serial.println(month);

  File file = SD.open("PTIMES.CSV");
  if (!file) {
    Serial.println(F("SD: Cannot open PTIMES.CSV"));
    todaySDLoaded = false;
    return false;
  }

  Serial.print(F("SD: File size: ")); Serial.println(file.size());

  char buf[48];
  bool found = false;
  bool eof   = false;
  int  linesScanned = 0;

  // Use file.read() returning -1 for EOF — more reliable than file.available()
  while (!found && !eof) {
    uint8_t len = 0;
    while (len < sizeof(buf) - 1) {
      int c = file.read();
      if (c == -1) { eof = true; break; }
      if (c == '\n') break;
      if (c != '\r') buf[len++] = (char)c;
    }
    buf[len] = '\0';
    if (len == 0) continue;
    linesScanned++;

    // Print first 3 lines so we can verify file content
    if (linesScanned <= 3) {
      Serial.print(F("SD line ")); Serial.print(linesScanned);
      Serial.print(F(": [")); Serial.print(buf); Serial.println(']');
    }

    // Parse 12 comma-separated integers
    int   values[12];
    int   idx = 0;
    char* ptr = buf;
    while (idx < 12) {
      values[idx++] = atoi(ptr);
      ptr = strchr(ptr, ',');
      if (!ptr) break;
      ptr++;
    }

    if (idx == 12 && (uint8_t)values[0] == day && (uint8_t)values[1] == month) {
      todayFromSD.day          = values[0];
      todayFromSD.month        = values[1];
      todayFromSD.fajr_hour    = values[2];
      todayFromSD.fajr_min     = values[3];
      todayFromSD.dhuhr_hour   = values[4];
      todayFromSD.dhuhr_min    = values[5];
      todayFromSD.asr_hour     = values[6];
      todayFromSD.asr_min      = values[7];
      todayFromSD.maghrib_hour = values[8];
      todayFromSD.maghrib_min  = values[9];
      todayFromSD.isha_hour    = values[10];
      todayFromSD.isha_min     = values[11];
      found = true;
    }
  }

  file.close();

  Serial.print(F("SD: Scanned ")); Serial.print(linesScanned); Serial.println(F(" lines"));

  todaySDLoaded   = found;
  lastLoadedDay   = found ? day   : -1;
  lastLoadedMonth = found ? month : -1;

  if (found) {
    Serial.print(F("SD: Loaded times for "));
    Serial.print(day); Serial.print('/'); Serial.println(month);
  } else {
    Serial.println(F("SD: Date not found — using built-in fallback"));
  }
  return found;
}

// Returns SD entry if available for today, otherwise falls back to prayer_times.h
const PrayerTime* getPrayerTimesForDate(uint8_t day, uint8_t month) {
  if (todaySDLoaded && todayFromSD.day == day && todayFromSD.month == month) {
    return &todayFromSD;
  }
  for (int i = 0; i < 365; i++) {
    if (prayer_times[i].day == day && prayer_times[i].month == month) {
      return &prayer_times[i];
    }
  }
  return NULL;
}
// ─────────────────────────────────────────────────────────────────────────────

extern int azanLenMinutes;
extern int azanLenSeconds;

const int EEPROM_FLAG_ADDR = 0;
const int EEPROM_MIN_ADDR  = 1;
const int EEPROM_SEC_ADDR  = 2;

void loadAzanLenFromEEPROM() {
  uint8_t flag = EEPROM.read(EEPROM_FLAG_ADDR);
  if (flag != 1) {
    EEPROM.write(EEPROM_FLAG_ADDR, 1);
    EEPROM.write(EEPROM_MIN_ADDR, 5);
    EEPROM.write(EEPROM_SEC_ADDR, 0);
    azanLenMinutes = 5;
    azanLenSeconds = 0;
    Serial.println("EEPROM initialized with defaults (5:00)");
  } else {
    azanLenMinutes = EEPROM.read(EEPROM_MIN_ADDR) % 60;
    azanLenSeconds = EEPROM.read(EEPROM_SEC_ADDR) % 60;
    Serial.print("EEPROM loaded Azan length: ");
    Serial.print(azanLenMinutes); Serial.print(":"); Serial.println(azanLenSeconds);
  }
}

void saveAzanLenToEEPROM() {
  if (EEPROM.read(EEPROM_MIN_ADDR) != (uint8_t)azanLenMinutes)
    EEPROM.write(EEPROM_MIN_ADDR, (uint8_t)azanLenMinutes);
  if (EEPROM.read(EEPROM_SEC_ADDR) != (uint8_t)azanLenSeconds)
    EEPROM.write(EEPROM_SEC_ADDR, (uint8_t)azanLenSeconds);
  if (EEPROM.read(EEPROM_FLAG_ADDR) != 1)
    EEPROM.write(EEPROM_FLAG_ADDR, 1);
  Serial.print("EEPROM saved: ");
  Serial.print(azanLenMinutes); Serial.print(":"); Serial.println(azanLenSeconds);
}

bool azanActive = false;
unsigned long azanStartTime = 0;
int azanLenMinutes = 5;
int azanLenSeconds = 0;

unsigned long getAzanDurationMs() {
  return (unsigned long)azanLenMinutes * 60000UL + (unsigned long)azanLenSeconds * 1000UL;
}
String currentAzanName = "";

void scanI2C() {
  Serial.println("Scanning I2C devices...");
  lcd.clear();
  lcd.print("Scanning I2C...");
  int nDevices = 0;
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      Serial.print("I2C found: 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
      nDevices++;
    }
  }
  lcd.clear();
  if (nDevices == 0) {
    lcd.print("No I2C devices!");
    lcd.setCursor(0, 1); lcd.print("Check wiring!");
    delay(3000);
  } else {
    lcd.print("Found "); lcd.print(nDevices); lcd.print(" device(s)");
    delay(2000);
  }
}

void setup() {
  Serial.begin(9600);

  pinMode(BTN_MODE,    INPUT_PULLUP);
  pinMode(BTN_SECTION, INPUT_PULLUP);
  pinMode(BTN_UP,      INPUT_PULLUP);
  pinMode(BTN_DOWN,    INPUT_PULLUP);
  pinMode(RELAY_PIN,   OUTPUT);
  pinMode(MANUAL_SWITCH_PIN, INPUT_PULLUP);
  digitalWrite(RELAY_PIN, LOW);  // MOSFET off at startup

  Wire.begin();
  Wire.setClock(I2C_FREQ);
  Wire.setTimeout(1000);

  lcd.begin(16, 2);
  Serial.println("Starting Azan System...");
  loadAzanLenFromEEPROM();
  lcd.print("Starting...");
  delay(1000);

  scanI2C();

  // ── RTC init ──
  int  rtcAttempts = 0;
  bool rtcFound    = false;
  while (rtcAttempts < 3 && !rtcFound) {
    Serial.print("RTC attempt "); Serial.print(rtcAttempts + 1); Serial.println("/3");
    lcd.clear(); lcd.print("Connecting RTC...");
    lcd.setCursor(0, 1); lcd.print("Try "); lcd.print(rtcAttempts + 1); lcd.print("/3");

    if (rtc.begin()) {
      rtcFound = true;
      lcd.clear(); lcd.print("RTC Connected!");
      if (rtc.lostPower()) {
        rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
        lcd.setCursor(0, 1); lcd.print("Time reset!");
      }
      delay(2000); lcd.clear();
    } else {
      lcd.clear(); lcd.print("RTC Error!");
      lcd.setCursor(0, 1); lcd.print("Retry "); lcd.print(rtcAttempts + 1); lcd.print("/3");
      delay(2000);
      rtcAttempts++;
    }
  }

  if (!rtcFound) {
    lcd.clear(); lcd.print("RTC Failed!");
    lcd.setCursor(0, 1); lcd.print("Check Wiring!");
    while (1) delay(1000);
  }

  // ── SD card init ──
  pinMode(SD_CS_PIN, OUTPUT);
  digitalWrite(SD_CS_PIN, HIGH);  // deselect SD before begin
  delay(200);                     // let module power stabilise
  lcd.clear(); lcd.print("SD Card...");
  if (SD.begin(SD_CS_PIN)) {
    sdCardAvailable = true;
    Serial.println(F("SD card OK"));
    lcd.setCursor(0, 1); lcd.print("SD: OK          ");
    delay(1000);

    now = rtc.now();
    lcd.setCursor(0, 1); lcd.print("SD: Reading...  ");
    if (loadTodayFromSD(now.day(), now.month())) {
      lcd.setCursor(0, 1); lcd.print("Times: SD       ");
    } else {
      lcd.setCursor(0, 1); lcd.print("Times: Built-in ");
    }
    delay(1500);
  } else {
    // Diagnose why SD.begin() failed
    Sd2Card  diagCard;
    SdVolume diagVol;
    if (!diagCard.init(SPI_HALF_SPEED, SD_CS_PIN)) {
      Serial.println(F("SD: No card or wiring error (check MOSI/MISO/CS/power)"));
      lcd.setCursor(0, 1); lcd.print("SD:NoCard/Wiring");
    } else if (!diagVol.init(diagCard)) {
      Serial.println(F("SD: Card found but no FAT — reformat as FAT32"));
      lcd.setCursor(0, 1); lcd.print("SD:Format FAT32!");
    } else {
      Serial.print(F("SD: FAT")); Serial.print(diagVol.fatType());
      Serial.println(F(" OK but SD.begin() failed — check library version"));
      lcd.setCursor(0, 1); lcd.print("SD: Init failed ");
    }
    Serial.println(F("Using built-in prayer times"));
    delay(3000);
  }

  Serial.println("System Ready!");
  settingMode = 0;
  lcd.clear(); lcd.print("Ready...");
  delay(1000);
  lcd.clear();
}

void loop() {
  now = rtc.now();

  manualMode = (digitalRead(MANUAL_SWITCH_PIN) == LOW);

  int modeState    = digitalRead(BTN_MODE);
  int sectionState = digitalRead(BTN_SECTION);
  int upState      = digitalRead(BTN_UP);
  int downState    = digitalRead(BTN_DOWN);
  unsigned long nowMs = millis();

  static unsigned long lastDebugTime = 0;
  if (nowMs - lastDebugTime > 2000) {
    Serial.print("MODE:"); Serial.print(modeState);
    Serial.print(" SEC:"); Serial.print(sectionState);
    Serial.print(" UP:"); Serial.print(upState);
    Serial.print(" DOWN:"); Serial.print(downState);
    Serial.print(" Setting:"); Serial.print(settingMode);
    Serial.print(" Manual:"); Serial.println(manualMode ? "ON" : "OFF");
    lastDebugTime = nowMs;
  }

  // MODE button
  if (lastModeState == HIGH && modeState == LOW && (nowMs - lastButtonEventMs) > debounceMs) {
    settingMode = (settingMode > 0) ? 0 : 1;
    Serial.println(settingMode ? "MODE - Enter setting" : "MODE - Normal display");
    lastButtonEventMs = nowMs;
  }
  lastModeState = modeState;

  // SECTION button
  if (lastSectionState == HIGH && sectionState == LOW && (nowMs - lastButtonEventMs) > debounceMs) {
    if (settingMode > 0) {
      settingMode = (settingMode >= 6) ? 1 : settingMode + 1;
      Serial.println("SECTION - SettingMode: " + String(settingMode));
    }
    lastButtonEventMs = nowMs;
  }
  lastSectionState = sectionState;

  if (settingMode > 0) {
    int y = now.year(), m = now.month(), d = now.day();
    int h = now.hour(), mn = now.minute(), s = now.second();

    if (lastUpState == HIGH && upState == LOW && (nowMs - lastButtonEventMs) > debounceMs) {
      if (settingMode == 1) h  = (h + 1) % 24;
      if (settingMode == 2) mn = (mn + 1) % 60;
      if (settingMode == 3) d  = (d % 31) + 1;
      if (settingMode == 4) m  = (m % 12) + 1;
      if (settingMode == 5) azanLenMinutes = (azanLenMinutes + 1) % 60;
      if (settingMode == 6) azanLenSeconds = (azanLenSeconds + 1) % 60;
      if (settingMode >= 1 && settingMode <= 4) rtc.adjust(DateTime(y, m, d, h, mn, s));
      if (settingMode == 5 || settingMode == 6) saveAzanLenToEEPROM();
      lastButtonEventMs = nowMs;
      Serial.println("UP pressed");
    }

    if (lastDownState == HIGH && downState == LOW && (nowMs - lastButtonEventMs) > debounceMs) {
      if (settingMode == 1) h  = (h - 1 + 24) % 24;
      if (settingMode == 2) mn = (mn - 1 + 60) % 60;
      if (settingMode == 3) d  = (d - 2 + 31) % 31 + 1;
      if (settingMode == 4) m  = (m - 2 + 12) % 12 + 1;
      if (settingMode == 5) azanLenMinutes = (azanLenMinutes - 1 + 60) % 60;
      if (settingMode == 6) azanLenSeconds = (azanLenSeconds - 1 + 60) % 60;
      if (settingMode >= 1 && settingMode <= 4) rtc.adjust(DateTime(y, m, d, h, mn, s));
      if (settingMode == 5 || settingMode == 6) saveAzanLenToEEPROM();
      lastButtonEventMs = nowMs;
      Serial.println("DOWN pressed");
    }

    lastUpState   = upState;
    lastDownState = downState;

    lcd.setCursor(0, 0);
    char timeLine[17];
    snprintf(timeLine, sizeof(timeLine), "%02d/%02d %02d:%02d:%02d", d, m, h, mn, s);
    lcd.print(timeLine);

    lcd.setCursor(0, 1);
    if (settingMode == 1) lcd.print("Set Hour       ");
    if (settingMode == 2) lcd.print("Set Minute     ");
    if (settingMode == 3) lcd.print("Set Day        ");
    if (settingMode == 4) lcd.print("Set Month      ");
    if (settingMode == 5) { char az[17]; snprintf(az, 17, "Azan Min: %02d  ", azanLenMinutes); lcd.print(az); }
    if (settingMode == 6) { char az[17]; snprintf(az, 17, "Azan Sec: %02d  ", azanLenSeconds); lcd.print(az); }

  } else {
    lastDownState = downState;
    lastUpState   = upState;

    // Reload SD prayer times when the date changes (handles midnight rollover)
    if (sdCardAvailable && (now.day() != lastLoadedDay || now.month() != lastLoadedMonth)) {
      loadTodayFromSD(now.day(), now.month());
    }

    char line1[17];
    snprintf(line1, sizeof(line1), "%02d/%02d %02d:%02d:%02d",
             now.day(), now.month(), now.hour(), now.minute(), now.second());
    lcd.setCursor(0, 0);
    lcd.print("                ");
    lcd.setCursor(0, 0);
    lcd.print(line1);

    Serial.print("Time: "); Serial.println(line1);

    const char* currentPrayer = "";
    bool prayerTimeNow = false;

    const PrayerTime* today = getPrayerTimesForDate(now.day(), now.month());
    if (today != NULL) {
      int hours[5]   = { today->fajr_hour, today->dhuhr_hour, today->asr_hour, today->maghrib_hour, today->isha_hour };
      int minutes[5] = { today->fajr_min,  today->dhuhr_min,  today->asr_min,  today->maghrib_min,  today->isha_min  };
      for (int i = 0; i < 5; i++) {
        if (now.hour() == hours[i] && now.minute() == minutes[i]) {
          currentPrayer = PRAYER_NAMES[i];
          prayerTimeNow = true;
          break;
        }
      }
    } else {
      Serial.println("No prayer times found for today!");
    }

    if (prayerTimeNow && !azanActive) {
      azanActive = true;
      azanStartTime = millis();
      currentAzanName = String(currentPrayer);
      digitalWrite(RELAY_PIN, HIGH);
      Serial.println("AZAN TIME: " + currentAzanName);
    }

    if (azanActive && (millis() - azanStartTime >= getAzanDurationMs())) {
      azanActive = false;
      currentAzanName = "";
      digitalWrite(RELAY_PIN, LOW);
      Serial.println("AZAN FINISHED");
    }

    lcd.setCursor(0, 1);
    lcd.print("                ");
    lcd.setCursor(0, 1);
    if (manualMode) {
      lcd.print("MANUAL ON       ");
    } else if (azanActive) {
      lcd.print("AZAN: "); lcd.print(currentAzanName);
    } else {
      lcd.print(currentPrayer);
    }

    Serial.print("Prayer: "); Serial.print(currentPrayer);
    Serial.print("  Azan: "); Serial.print(azanActive ? "YES" : "NO");
    Serial.print("  Src: "); Serial.println(todaySDLoaded ? "SD" : "Built-in");

    delay(1000);
  }

  // MOSFET reassertion — manual switch wins (active-high: HIGH = on)
  if (manualMode) {
    digitalWrite(RELAY_PIN, HIGH);
  } else {
    digitalWrite(RELAY_PIN, azanActive ? HIGH : LOW);
  }
}
