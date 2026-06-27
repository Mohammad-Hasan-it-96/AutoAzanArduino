from prayer_times_calculator import PrayerTimesCalculator
from datetime import datetime, timedelta

# إعدادات الموقع الجغرافي (مثال: دمشق)
latitude = 35.0210
longitude = 36.1111

# تاريخ البدء وعدد الأيام (سنة كاملة)
start_date = datetime(2025, 1, 1)
days = 365

# رأس ملف الهيدر C++
header = """\
#ifndef PRAYER_TIMES_H
#define PRAYER_TIMES_H

typedef struct {
  uint8_t day;
  uint8_t month;
  uint8_t fajr_hour;
  uint8_t fajr_min;
  uint8_t dhuhr_hour;
  uint8_t dhuhr_min;
  uint8_t asr_hour;
  uint8_t asr_min;
  uint8_t maghrib_hour;
  uint8_t maghrib_min;
  uint8_t isha_hour;
  uint8_t isha_min;
} PrayerTime;

const PrayerTime prayer_times[365] = {
"""

# نهاية ملف الهيدر
footer = "};\n\n#endif // PRAYER_TIMES_H"

lines = []

# حساب أوقات الصلاة لكل يوم في السنة
for i in range(days):
    date = start_date + timedelta(days=i)
    
    # تحويل التاريخ إلى النموذج المطلوب للـ string (YYYY-M-D)
    date_string = f"{date.year}-{date.month}-{date.day}"
    
    # إنشاء كائن جديد لحساب أوقات الصلاة لكل تاريخ
    pt = PrayerTimesCalculator(latitude, longitude, "jafari", date_string)
    times = pt.fetch_prayer_times()

    # استخراج الساعة والدقيقة من كل وقت صلاة
    def extract_hour_minute(t):
        h, m = map(int, t.split(':'))
        return h, m

    fajr_h, fajr_m = extract_hour_minute(times['Fajr'])
    dhuhr_h, dhuhr_m = extract_hour_minute(times['Dhuhr'])
    asr_h, asr_m = extract_hour_minute(times['Asr'])
    maghrib_h, maghrib_m = extract_hour_minute(times['Maghrib'])
    isha_h, isha_m = extract_hour_minute(times['Isha'])

    # توليد سطر C++ يمثل هذا اليوم
    line = f"  {{{date.day}, {date.month}, {fajr_h}, {fajr_m}, {dhuhr_h}, {dhuhr_m}, {asr_h}, {asr_m}, {maghrib_h}, {maghrib_m}, {isha_h}, {isha_m}}},"
    lines.append(line)
    
    # طباعة تقدم العمل
    if (i + 1) % 30 == 0:
        print(f"تم حساب {i + 1} يوم من أصل {days}")

# كتابة الملف النهائي
with open("prayer_times.h", "w") as f:
    f.write(header + "\n".join(lines) + "\n" + footer)

print("✅ تم توليد ملف prayer_times.h بنجاح.")
