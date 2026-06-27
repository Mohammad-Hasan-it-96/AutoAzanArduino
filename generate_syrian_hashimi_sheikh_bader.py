from datetime import datetime, timedelta
from typing import Dict, Tuple

# نعتمد على الحسابات الفلكية المحلية (بدون أي API)
from improved_prayer_times import ImprovedPrayerTimes


# إعدادات الموقع: محافظة طرطوس - منطقة الشيخ بدر
SHEIKH_BADER_LAT = 34.9917
SHEIKH_BADER_LON = 36.0835


def generate_day_times(calculator: ImprovedPrayerTimes, date: datetime) -> Dict[str, str]:
    """يحسب أوقات الصلاة ليوم محدد بطريقة التقويم الهاشمي المحسّنة (محلي بالكامل)."""
    # نستخدم طريقة الهاشمي السوري المحسّنة المعتمدة في المشروع
    # فجر: -20°، عشاء: -18°، ظهر: عبور، عصر: ظل = 1
    return calculator.method_syrian_hashimi_improved(date)


def extract_hm(time_str: str) -> Tuple[int, int]:
    h, m = map(int, time_str.split(":"))
    return h, m


def generate_header_for_year(year: int = None,
                             latitude: float = SHEIKH_BADER_LAT,
                             longitude: float = SHEIKH_BADER_LON,
                             output_filename: str = "prayer_times_improved_syrian_hashimi_sheikh_bader.h") -> str:
    """يولّد ملف .h يحوي أوقات الصلاة لعام كامل (365 يوم) لمنطقة الشيخ بدر بطريقة الهاشمي السوري.

    - الحساب محلي بالكامل عبر ephem (ضمن ImprovedPrayerTimes)، بدون أي اتصال شبكي.
    - يمكن تمرير سنة محددة، وإلا تُستخدم السنة الحالية.
    """
    if year is None:
        year = datetime.now().year

    start_date = datetime(year, 1, 1)
    days = 365  # حافظ على 365 يوماً دائماً مثل بقية الملفات

    calculator = ImprovedPrayerTimes(latitude, longitude)

    header = """#ifndef PRAYER_TIMES_IMPROVED_SYRIAN_HASHIMI_SHEIKH_BADER_H
#define PRAYER_TIMES_IMPROVED_SYRIAN_HASHIMI_SHEIKH_BADER_H

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

// Syrian Hashimi (improved) prayer times for Sheikh Bader (Lat 34.9917, Lon 36.0835)
// Computed locally without any API, year %d
const PrayerTime prayer_times_improved_syrian_hashimi_sheikh_bader[%d] = {
""" % (year, days)

    footer = """};

#endif // PRAYER_TIMES_IMPROVED_SYRIAN_HASHIMI_SHEIKH_BADER_H"""

    lines = []

    date = start_date
    generated = 0
    while generated < days:
        # تجاوز 29 فبراير في السنوات الكبيسة للحفاظ على طول 365 فقط
        if date.month == 2 and date.day == 29:
            date += timedelta(days=1)
            continue
        times = generate_day_times(calculator, date)

        fajr_h, fajr_m = extract_hm(times['Fajr'])
        dhuhr_h, dhuhr_m = extract_hm(times['Dhuhr'])
        asr_h, asr_m = extract_hm(times['Asr'])
        maghrib_h, maghrib_m = extract_hm(times['Maghrib'])
        isha_h, isha_m = extract_hm(times['Isha'])

        line = f"  {{{date.day}, {date.month}, {fajr_h}, {fajr_m}, {dhuhr_h}, {dhuhr_m}, {asr_h}, {asr_m}, {maghrib_h}, {maghrib_m}, {isha_h}, {isha_m}}},"
        lines.append(line)
        generated += 1
        date += timedelta(days=1)

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n" + footer)

    return output_filename


if __name__ == "__main__":
    filename = generate_header_for_year()
    print(f"✅ Generated {filename}")


