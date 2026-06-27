import requests
import json
from datetime import datetime, timedelta
import math
from typing import Dict, Tuple

# إعدادات الموقع الجغرافي (دمشق)
DAMASCUS_LAT = 33.5138
DAMASCUS_LON = 36.2765

class AlternativePrayerTimes:
    """فئة لحساب أوقات الصلاة باستخدام طرق مختلفة"""
    
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        
    def calculate_sun_position(self, date: datetime) -> Tuple[float, float]:
        """حساب موقع الشمس باستخدام معادلات فلكية"""
        # حساب اليوم من بداية السنة
        year_start = datetime(date.year, 1, 1)
        day_of_year = (date - year_start).days + 1
        
        # حساب زاوية الشمس
        B = 2 * math.pi * (day_of_year - 81) / 365
        EOT = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
        
        # حساب زاوية الارتفاع
        declination = 23.45 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        
        return declination, EOT
    
    def method_egyptian_general_authority(self, date: datetime) -> Dict[str, str]:
        """طريقة الهيئة المصرية العامة للأرصاد الجوية"""
        declination, EOT = self.calculate_sun_position(date)
        
        # زوايا الفجر والعشاء (طريقة مصرية)
        fajr_angle = 19.5
        isha_angle = 17.5
        
        # حساب أوقات الصلاة
        fajr = self._calculate_prayer_time(date, fajr_angle, declination, EOT, is_sunrise=False)
        dhuhr = self._calculate_dhuhr_time(date, EOT)
        asr = self._calculate_asr_time(date, declination, EOT)
        maghrib = self._calculate_sunset_time(date, declination, EOT)
        isha = self._calculate_prayer_time(date, isha_angle, declination, EOT, is_sunrise=False)
        
        return {
            'Fajr': fajr,
            'Dhuhr': dhuhr,
            'Asr': asr,
            'Maghrib': maghrib,
            'Isha': isha
        }
    
    def method_umm_al_qura(self, date: datetime) -> Dict[str, str]:
        """طريقة جامعة أم القرى (مكة المكرمة)"""
        declination, EOT = self.calculate_sun_position(date)
        
        # زوايا الفجر والعشاء (طريقة أم القرى)
        fajr_angle = 18.5
        isha_angle = 90  # 90 دقيقة بعد المغرب
        
        fajr = self._calculate_prayer_time(date, fajr_angle, declination, EOT, is_sunrise=False)
        dhuhr = self._calculate_dhuhr_time(date, EOT)
        asr = self._calculate_asr_time(date, declination, EOT)
        maghrib = self._calculate_sunset_time(date, declination, EOT)
        
        # حساب العشاء (90 دقيقة بعد المغرب)
        maghrib_dt = datetime.strptime(maghrib, '%H:%M')
        isha_dt = maghrib_dt + timedelta(minutes=90)
        isha = isha_dt.strftime('%H:%M')
        
        return {
            'Fajr': fajr,
            'Dhuhr': dhuhr,
            'Asr': asr,
            'Maghrib': maghrib,
            'Isha': isha
        }
    
    def method_syrian_hashimi(self, date: datetime) -> Dict[str, str]:
        """طريقة التقويم الهاشمي السوري (محاولة تقريبية)"""
        declination, EOT = self.calculate_sun_position(date)
        
        # زوايا مخصصة للتقويم الهاشمي السوري
        fajr_angle = 18.5  # زاوية أكبر للفجر
        isha_angle = 19.0   # زاوية أكبر للعشاء
        
        fajr = self._calculate_prayer_time(date, fajr_angle, declination, EOT, is_sunrise=False)
        dhuhr = self._calculate_dhuhr_time(date, EOT)
        asr = self._calculate_asr_time(date, declination, EOT)
        maghrib = self._calculate_sunset_time(date, declination, EOT)
        isha = self._calculate_prayer_time(date, isha_angle, declination, EOT, is_sunrise=False)
        
        return {
            'Fajr': fajr,
            'Dhuhr': dhuhr,
            'Asr': asr,
            'Maghrib': maghrib,
            'Isha': isha
        }
    
    def api_aladhan(self, date: datetime) -> Dict[str, str]:
        """استخدام API Aladhan"""
        try:
            date_str = date.strftime('%d-%m-%Y')
            url = f"http://api.aladhan.com/v1/timings/{date_str}"
            params = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'method': 4,  # طريقة جامعة أم القرى
                'school': 1   # مدرسة شافعي
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                timings = data['data']['timings']
                
                return {
                    'Fajr': timings['Fajr'],
                    'Dhuhr': timings['Dhuhr'],
                    'Asr': timings['Asr'],
                    'Maghrib': timings['Maghrib'],
                    'Isha': timings['Isha']
                }
        except Exception as e:
            print(f"خطأ في API Aladhan: {e}")
            return {}
    
    def api_prayertimes(self, date: datetime) -> Dict[str, str]:
        """استخدام API PrayerTimes.org"""
        try:
            date_str = date.strftime('%Y-%m-%d')
            url = f"https://api.prayertimes.org/v1/timings/{date_str}"
            params = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'method': 'egyptian',
                'school': 'shafi'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                timings = data['timings']
                
                return {
                    'Fajr': timings['fajr'],
                    'Dhuhr': timings['dhuhr'],
                    'Asr': timings['asr'],
                    'Maghrib': timings['maghrib'],
                    'Isha': timings['isha']
                }
        except Exception as e:
            print(f"خطأ في API PrayerTimes: {e}")
            return {}
    
    def _calculate_prayer_time(self, date: datetime, angle: float, declination: float, EOT: float, is_sunrise: bool = False) -> str:
        """حساب وقت الصلاة بناءً على زاوية معينة"""
        # تحويل الزاوية إلى راديان
        angle_rad = math.radians(angle)
        lat_rad = math.radians(self.latitude)
        decl_rad = math.radians(declination)
        
        # حساب زاوية الساعة
        cos_h = (math.sin(angle_rad) - math.sin(lat_rad) * math.sin(decl_rad)) / (math.cos(lat_rad) * math.cos(decl_rad))
        cos_h = max(-1, min(1, cos_h))  # التأكد من أن القيمة بين -1 و 1
        
        h = math.acos(cos_h)
        if is_sunrise:
            h = -h
        
        # تحويل إلى وقت
        time_offset = h * 12 / math.pi
        time_offset += EOT / 60
        
        # إضافة 12 ساعة للفجر والعشاء
        if not is_sunrise:
            time_offset += 12
        
        # تحويل إلى ساعات ودقائق
        hours = int(time_offset)
        minutes = int((time_offset - hours) * 60)
        
        return f"{hours:02d}:{minutes:02d}"
    
    def _calculate_dhuhr_time(self, date: datetime, EOT: float) -> str:
        """حساب وقت الظهر"""
        # الظهر عند منتصف النهار + تصحيح المعادلة الزمنية
        time_offset = 12 + EOT / 60
        hours = int(time_offset)
        minutes = int((time_offset - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def _calculate_asr_time(self, date: datetime, declination: float, EOT: float) -> str:
        """حساب وقت العصر"""
        # العصر عندما يكون ظل الجسم مساوياً لطوله + طول الظل عند الظهر
        lat_rad = math.radians(self.latitude)
        decl_rad = math.radians(declination)
        
        # حساب زاوية العصر
        shadow_factor = 1  # ظل الجسم = طوله
        angle_rad = math.atan(1 / shadow_factor)
        
        # حساب زاوية الساعة للعصر
        cos_h = (math.sin(angle_rad) - math.sin(lat_rad) * math.sin(decl_rad)) / (math.cos(lat_rad) * math.cos(decl_rad))
        cos_h = max(-1, min(1, cos_h))
        
        h = math.acos(cos_h)
        
        # تحويل إلى وقت
        time_offset = h * 12 / math.pi
        time_offset += EOT / 60 + 12
        
        hours = int(time_offset)
        minutes = int((time_offset - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def _calculate_sunset_time(self, date: datetime, declination: float, EOT: float) -> str:
        """حساب وقت غروب الشمس"""
        return self._calculate_prayer_time(date, 0, declination, EOT, is_sunrise=False)

def generate_alternative_prayer_times():
    """توليد أوقات الصلاة باستخدام الطرق البديلة"""
    
    # إعدادات
    latitude = DAMASCUS_LAT
    longitude = DAMASCUS_LON
    start_date = datetime(2025, 1, 1)
    days = 365
    
    calculator = AlternativePrayerTimes(latitude, longitude)
    
    # رأس ملف الهيدر C++
    header = """\
#ifndef ALTERNATIVE_PRAYER_TIMES_H
#define ALTERNATIVE_PRAYER_TIMES_H

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

// أوقات الصلاة بطريقة الهيئة المصرية
const PrayerTime prayer_times_egyptian[365] = {
"""
    
    footer = "};\n\n#endif // ALTERNATIVE_PRAYER_TIMES_H"
    
    # توليد أوقات الصلاة لكل طريقة
    methods = {
        'egyptian': calculator.method_egyptian_general_authority,
        'umm_al_qura': calculator.method_umm_al_qura,
        'syrian_hashimi': calculator.method_syrian_hashimi
    }
    
    for method_name, method_func in methods.items():
        print(f"جاري حساب أوقات الصلاة بطريقة: {method_name}")
        
        lines = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            times = method_func(date)
            
            if times:
                # استخراج الساعة والدقيقة
                def extract_hour_minute(t):
                    h, m = map(int, t.split(':'))
                    return h, m
                
                fajr_h, fajr_m = extract_hour_minute(times['Fajr'])
                dhuhr_h, dhuhr_m = extract_hour_minute(times['Dhuhr'])
                asr_h, asr_m = extract_hour_minute(times['Asr'])
                maghrib_h, maghrib_m = extract_hour_minute(times['Maghrib'])
                isha_h, isha_m = extract_hour_minute(times['Isha'])
                
                # توليد سطر C++
                line = f"  {{{date.day}, {date.month}, {fajr_h}, {fajr_m}, {dhuhr_h}, {dhuhr_m}, {asr_h}, {asr_m}, {maghrib_h}, {maghrib_m}, {isha_h}, {isha_m}}},"
                lines.append(line)
            
            # طباعة تقدم العمل
            if (i + 1) % 30 == 0:
                print(f"تم حساب {i + 1} يوم من أصل {days}")
        
        # كتابة الملف
        filename = f"prayer_times_{method_name}.h"
        with open(filename, "w", encoding='utf-8') as f:
            f.write(header + "\n".join(lines) + "\n" + footer)
        
        print(f"✅ تم توليد ملف {filename} بنجاح.")

def test_api_methods():
    """اختبار طرق API المختلفة"""
    calculator = AlternativePrayerTimes(DAMASCUS_LAT, DAMASCUS_LON)
    test_date = datetime(2025, 1, 1)
    
    print("=== مقارنة أوقات الصلاة لليوم الأول من يناير 2025 ===")
    print(f"الموقع: دمشق ({DAMASCUS_LAT}, {DAMASCUS_LON})")
    print()
    
    # اختبار الطرق المحسوبة
    methods = {
        'الهيئة المصرية': calculator.method_egyptian_general_authority,
        'أم القرى': calculator.method_umm_al_qura,
        'التقويم الهاشمي السوري': calculator.method_syrian_hashimi
    }
    
    for method_name, method_func in methods.items():
        times = method_func(test_date)
        print(f"طريقة {method_name}:")
        for prayer, time in times.items():
            print(f"  {prayer}: {time}")
        print()
    
    # اختبار APIs
    print("=== اختبار APIs ===")
    api_methods = {
        'Aladhan API': calculator.api_aladhan,
        'PrayerTimes API': calculator.api_prayertimes
    }
    
    for api_name, api_func in api_methods.items():
        times = api_func(test_date)
        if times:
            print(f"{api_name}:")
            for prayer, time in times.items():
                print(f"  {prayer}: {time}")
        else:
            print(f"{api_name}: غير متاح")
        print()

if __name__ == "__main__":
    print("🚀 بدء توليد أوقات الصلاة البديلة...")
    print()
    
    # اختبار الطرق أولاً
    test_api_methods()
    
    # توليد الملفات
    generate_alternative_prayer_times()
    
    print("✅ تم الانتهاء من جميع العمليات بنجاح!") 