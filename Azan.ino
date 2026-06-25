#include <Wire.h>
#include <RTClib.h>
#include <LiquidCrystal.h>
#include <EEPROM.h>
#include "prayer_times.h"

// I2C configuration for ESP32
#define I2C_SDA 21
#define I2C_SCL 22
#define I2C_FREQ 100000  // 100kHz for better compatibility
#define BTN_MODE 10
#define BTN_SECTION 11  // اختيار ما نعدّل
#define BTN_UP 12       // زيادة
#define BTN_DOWN 13     // نقصان
#define RELAY_PIN 3
#define MANUAL_SWITCH_PIN 14  // مفتاح تشغيل يدوي — INPUT_PULLUP، LOW = تشغيل

int settingMode = 0;  // 0 = عرض عادي، 1-6 = وضع الضبط
DateTime now;
LiquidCrystal lcd(8, 9, 4, 5, 6, 7);
RTC_DS3231 rtc;

// Button state tracking for edge-detected debouncing
int lastModeState = LOW;
int lastSectionState = HIGH;
int lastUpState = HIGH;
int lastDownState = HIGH;
unsigned long lastButtonEventMs = 0;
const unsigned long debounceMs = 120;
bool manualMode = false;

const char* PRAYER_NAMES[5] = { "Fajr", "Dhuhr", "Asr", "Maghrib", "Isha" };

const PrayerTime* getPrayerTimesForDate(uint8_t day, uint8_t month) {
  for (int i = 0; i < 365; i++) {
    if (prayer_times[i].day == day && prayer_times[i].month == month) {
      return &prayer_times[i];
    }
  }
  return NULL;
}

extern int azanLenMinutes;
extern int azanLenSeconds;

const int EEPROM_FLAG_ADDR = 0;
const int EEPROM_MIN_ADDR = 1;
const int EEPROM_SEC_ADDR = 2;

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
    Serial.print(azanLenMinutes);
    Serial.print(":");
    Serial.println(azanLenSeconds);
  }
}

void saveAzanLenToEEPROM() {
  uint8_t storedMin = EEPROM.read(EEPROM_MIN_ADDR);
  uint8_t storedSec = EEPROM.read(EEPROM_SEC_ADDR);
  if (storedMin != (uint8_t)azanLenMinutes) {
    EEPROM.write(EEPROM_MIN_ADDR, (uint8_t)azanLenMinutes);
  }
  if (storedSec != (uint8_t)azanLenSeconds) {
    EEPROM.write(EEPROM_SEC_ADDR, (uint8_t)azanLenSeconds);
  }
  if (EEPROM.read(EEPROM_FLAG_ADDR) != 1) {
    EEPROM.write(EEPROM_FLAG_ADDR, 1);
  }
  Serial.print("EEPROM saved Azan length: ");
  Serial.print(azanLenMinutes);
  Serial.print(":");
  Serial.println(azanLenSeconds);
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
    byte error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("I2C device found at address 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
      nDevices++;
    }
  }

  if (nDevices == 0) {
    Serial.println("No I2C devices found!");
    lcd.clear();
    lcd.print("No I2C devices!");
    lcd.setCursor(0, 1);
    lcd.print("Check wiring!");
    delay(3000);
  } else {
    Serial.print(nDevices);
    Serial.println(" device(s) found");
    lcd.clear();
    lcd.print("Found ");
    lcd.print(nDevices);
    lcd.print(" devices");
    delay(2000);
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(BTN_MODE, INPUT_PULLUP);
  pinMode(BTN_SECTION, INPUT_PULLUP);
  pinMode(BTN_UP, INPUT_PULLUP);
  pinMode(BTN_DOWN, INPUT_PULLUP);
  pinMode(RELAY_PIN, OUTPUT);
  // Manual switch: INPUT_PULLUP — connect switch between pin 14 and GND; LOW = manual ON
  pinMode(MANUAL_SWITCH_PIN, INPUT_PULLUP);
  digitalWrite(RELAY_PIN, HIGH);  // relay off at startup

  Wire.begin();
  Wire.setClock(I2C_FREQ);
  Wire.setTimeout(1000);

  lcd.begin(16, 2);

  Serial.println("Starting Azan System...");
  loadAzanLenFromEEPROM();
  lcd.print("Starting...");
  delay(1000);

  scanI2C();

  int rtcAttempts = 0;
  bool rtcFound = false;

  while (rtcAttempts < 3 && !rtcFound) {
    Serial.print("Attempting to connect to RTC... (");
    Serial.print(rtcAttempts + 1);
    Serial.println("/3)");

    lcd.clear();
    lcd.print("Connecting RTC...");
    lcd.setCursor(0, 1);
    lcd.print("Try ");
    lcd.print(rtcAttempts + 1);
    lcd.print("/3");

    if (rtc.begin()) {
      rtcFound = true;
      Serial.println("RTC Found!");
      lcd.clear();
      lcd.print("RTC Connected!");

      if (rtc.lostPower()) {
        Serial.println("RTC lost power, setting time...");
        rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
        lcd.setCursor(0, 1);
        lcd.print("Time Set!");
      }

      delay(2000);
      lcd.clear();
    } else {
      Serial.println("RTC Not Found! Retrying...");
      lcd.clear();
      lcd.print("RTC Error!");
      lcd.setCursor(0, 1);
      lcd.print("Retry ");
      lcd.print(rtcAttempts + 1);
      lcd.print("/3");
      delay(2000);
      rtcAttempts++;
    }
  }

  if (!rtcFound) {
    Serial.println("Failed to connect to RTC after 3 attempts!");
    lcd.clear();
    lcd.print("RTC Failed!");
    lcd.setCursor(0, 1);
    lcd.print("Check Wiring!");
    while (1) delay(1000);
  }

  Serial.println("System Ready!");
  settingMode = 0;
  lcd.clear();
  lcd.print("Ready...");
  delay(1000);
  lcd.clear();
}

void loop() {
  now = rtc.now();

  // Manual switch read at top of every loop — works in all modes
  // INPUT_PULLUP: switch connects pin 14 to GND → LOW = manual ON
  manualMode = (digitalRead(MANUAL_SWITCH_PIN) == LOW);

  int modeState    = digitalRead(BTN_MODE);
  int sectionState = digitalRead(BTN_SECTION);
  int upState      = digitalRead(BTN_UP);
  int downState    = digitalRead(BTN_DOWN);
  unsigned long nowMs = millis();

  static unsigned long lastDebugTime = 0;
  if (nowMs - lastDebugTime > 2000) {
    Serial.print("Button States - MODE:");
    Serial.print(modeState);
    Serial.print(" SECTION:");
    Serial.print(sectionState);
    Serial.print(" UP:");
    Serial.print(upState);
    Serial.print(" DOWN:");
    Serial.print(downState);
    Serial.print(" SettingMode:");
    Serial.print(settingMode);
    Serial.print(" Manual:");
    Serial.println(manualMode ? "ON" : "OFF");
    lastDebugTime = nowMs;
  }

  // MODE button: enter / exit setting mode (HIGH → LOW)
  if (lastModeState == HIGH && modeState == LOW && (nowMs - lastButtonEventMs) > debounceMs) {
    settingMode = (settingMode > 0) ? 0 : 1;
    Serial.println(settingMode ? "MODE - Enter setting" : "MODE - Normal display");
    lastButtonEventMs = nowMs;
  }
  lastModeState = modeState;

  // SECTION button: cycle setting field (HIGH → LOW)
  if (lastSectionState == HIGH && sectionState == LOW && (nowMs - lastButtonEventMs) > debounceMs) {
    if (settingMode > 0) {
      settingMode = (settingMode >= 6) ? 1 : settingMode + 1;
      Serial.println("SECTION - SettingMode: " + String(settingMode));
    }
    lastButtonEventMs = nowMs;
  }
  lastSectionState = sectionState;

  if (settingMode > 0) {
    Serial.println("DEBUG: In setting mode " + String(settingMode));
    int y  = now.year();
    int m  = now.month();
    int d  = now.day();
    int h  = now.hour();
    int mn = now.minute();
    int s  = now.second();

    // UP button: increase selected value
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

    // DOWN button: decrease selected value
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
    if (settingMode == 5) {
      char azLine[17];
      snprintf(azLine, sizeof(azLine), "Azan Min: %02d  ", azanLenMinutes);
      lcd.print(azLine);
    }
    if (settingMode == 6) {
      char azLine[17];
      snprintf(azLine, sizeof(azLine), "Azan Sec: %02d  ", azanLenSeconds);
      lcd.print(azLine);
    }

  } else {
    Serial.println("DEBUG: In normal display mode");

    lastDownState = downState;
    lastUpState   = upState;

    char line1[17];
    snprintf(line1, sizeof(line1), "%02d/%02d %02d:%02d:%02d",
             now.day(), now.month(), now.hour(), now.minute(), now.second());

    lcd.setCursor(0, 0);
    lcd.print("                ");
    lcd.setCursor(0, 0);
    lcd.print(line1);

    Serial.print("Time: ");
    Serial.println(line1);

    const char* currentPrayer = "";
    bool prayerTimeNow = false;

    const PrayerTime* today = getPrayerTimesForDate(now.day(), now.month());
    if (today != NULL) {
      int hours[5]   = { today->fajr_hour,  today->dhuhr_hour,  today->asr_hour,  today->maghrib_hour,  today->isha_hour  };
      int minutes[5] = { today->fajr_min,   today->dhuhr_min,   today->asr_min,   today->maghrib_min,   today->isha_min   };
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
      digitalWrite(RELAY_PIN, LOW);
      Serial.println("AZAN TIME: " + currentAzanName);
    }

    if (azanActive && (millis() - azanStartTime >= getAzanDurationMs())) {
      azanActive = false;
      currentAzanName = "";
      digitalWrite(RELAY_PIN, HIGH);
      Serial.println("AZAN FINISHED");
    }

    lcd.setCursor(0, 1);
    lcd.print("                ");
    lcd.setCursor(0, 1);
    if (manualMode) {
      lcd.print("MANUAL ON       ");
    } else if (azanActive) {
      lcd.print("AZAN: ");
      lcd.print(currentAzanName);
    } else {
      lcd.print(currentPrayer);
    }

    Serial.print("Current Prayer: ");
    Serial.println(currentPrayer);
    Serial.print("Azan Active: ");
    Serial.println(azanActive ? "YES" : "NO");
    Serial.print("Azan Name: ");
    Serial.println(currentAzanName);
    Serial.print("Time since azan start: ");
    Serial.println(azanActive ? (millis() - azanStartTime) / 1000 : 0);

    delay(1000);
  }

  // Relay reassertion — manual switch wins over azan (active-low: LOW = ON)
  if (manualMode) {
    digitalWrite(RELAY_PIN, LOW);
  } else {
    digitalWrite(RELAY_PIN, azanActive ? LOW : HIGH);
  }
}
