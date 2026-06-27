import requests
import json
from datetime import datetime, timedelta
import math
from typing import Dict, Tuple
import ephem  # for more accurate astronomical calculations

# إعدادات الموقع الجغرافي (دمشق)
DAMASCUS_LAT = 33.5138
DAMASCUS_LON = 36.2765

class ImprovedPrayerTimes:
    """فئة محسنة لحساب أوقات الصلاة باستخدام معادلات فلكية دقيقة"""
    
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        
    def calculate_accurate_sun_position(self, date: datetime) -> Tuple[float, float, float]:
        """حساب دقيق لموقع الشمس باستخدام مكتبة ephem"""
        # إنشاء كائن الشمس
        sun = ephem.Sun()
        
        # تعيين التاريخ
        observer = ephem.Observer()
        observer.lat = str(self.latitude)
        observer.lon = str(self.longitude)
        observer.date = date
        
        # حساب موقع الشمس
        sun.compute(observer)
        
        # حساب زاوية الارتفاع والانحراف
        altitude = float(sun.alt) * 180 / math.pi  # تحويل إلى درجات
        azimuth = float(sun.az) * 180 / math.pi
        declination = float(sun.dec) * 180 / math.pi
        
        return altitude, azimuth, declination
    
    def method_accurate_egyptian(self, date: datetime) -> Dict[str, str]:
        """طريقة الهيئة المصرية باستخدام حسابات دقيقة"""
        observer = ephem.Observer()
        observer.lat = str(self.latitude)
        observer.lon = str(self.longitude)
        observer.date = date
        
        # حساب أوقات الصلاة باستخدام ephem
        sun = ephem.Sun()
        
        # الفجر (زاوية -18 درجة تحت الأفق)
        observer.horizon = '-18'
        fajr = observer.next_rising(sun)
        
        # الظهر (منتصف النهار)
        observer.horizon = '0'
        dhuhr = observer.next_transit(sun)
        
        # العصر (ظل الجسم = طوله)
        # حساب العصر باستخدام معادلة فلكية
        asr_time = self._calculate_accurate_asr(date)
        
        # المغرب (غروب الشمس)
        maghrib = observer.next_setting(sun)
        
        # العشاء (زاوية -17 درجة تحت الأفق)
        observer.horizon = '-17'
        isha = observer.next_setting(sun)
        
        return {
            'Fajr': fajr.datetime().strftime('%H:%M'),
            'Dhuhr': dhuhr.datetime().strftime('%H:%M'),
            'Asr': asr_time,
            'Maghrib': maghrib.datetime().strftime('%H:%M'),
            'Isha': isha.datetime().strftime('%H:%M')
        }
    
    def method_accurate_umm_al_qura(self, date: datetime) -> Dict[str, str]:
        """طريقة أم القرى باستخدام حسابات دقيقة"""
        observer = ephem.Observer()
        observer.lat = str(self.latitude)
        observer.lon = str(self.longitude)
        observer.date = date
        
        sun = ephem.Sun()
        
        # الفجر (زاوية -18.5 درجة)
        observer.horizon = '-18.5'
        fajr = observer.next_rising(sun)
        
        # الظهر
        observer.horizon = '0'
        dhuhr = observer.next_transit(sun)
        
        # العصر
        asr_time = self._calculate_accurate_asr(date)
        
        # المغرب
        maghrib = observer.next_setting(sun)
        
        # العشاء (90 دقيقة بعد المغرب)
        maghrib_dt = maghrib.datetime()
        isha_dt = maghrib_dt + timedelta(minutes=90)
        isha = isha_dt.strftime('%H:%M')
        
        return {
            'Fajr': fajr.datetime().strftime('%H:%M'),
            'Dhuhr': dhuhr.datetime().strftime('%H:%M'),
            'Asr': asr_time,
            'Maghrib': maghrib.datetime().strftime('%H:%M'),
            'Isha': isha
        }
    
    def method_syrian_hashimi_improved(self, date: datetime) -> Dict[str, str]:
        """طريقة محسنة للتقويم الهاشمي السوري"""
        observer = ephem.Observer()
        observer.lat = str(self.latitude)
        observer.lon = str(self.longitude)
        observer.date = date
        
        sun = ephem.Sun()
        
        # الفجر (زاوية -20 درجة - مخصصة للتقويم الهاشمي)
        observer.horizon = '-20'
        fajr = observer.next_rising(sun)
        
        # الظهر
        observer.horizon = '0'
        dhuhr = observer.next_transit(sun)
        
        # العصر
        asr_time = self._calculate_accurate_asr(date)
        
        # المغرب
        maghrib = observer.next_setting(sun)
        
        # العشاء (زاوية -18 درجة)
        observer.horizon = '-18'
        isha = observer.next_setting(sun)
        
        return {
            'Fajr': fajr.datetime().strftime('%H:%M'),
            'Dhuhr': dhuhr.datetime().strftime('%H:%M'),
            'Asr': asr_time,
            'Maghrib': maghrib.datetime().strftime('%H:%M'),
            'Isha': isha.datetime().strftime('%H:%M')
        }
    
    def _calculate_accurate_asr(self, date: datetime) -> str:
        """حساب دقيق لوقت العصر"""
        observer = ephem.Observer()
        observer.lat = str(self.latitude)
        observer.lon = str(self.longitude)
        observer.date = date
        
        sun = ephem.Sun()
        sun.compute(observer)
        
        # حساب زاوية العصر (ظل الجسم = طوله)
        declination = float(sun.dec)
        latitude = math.radians(self.latitude)
        
        # حساب زاوية الساعة للعصر
        shadow_factor = 1.0  # ظل الجسم = طوله
        angle = math.atan(shadow_factor)
        
        # حساب زاوية الساعة
        cos_h = (math.sin(angle) - math.sin(latitude) * math.sin(declination)) / (math.cos(latitude) * math.cos(declination))
        cos_h = max(-1, min(1, cos_h))
        
        h = math.acos(cos_h)
        
        # تحويل إلى وقت
        time_offset = h * 12 / math.pi
        time_offset += 12  # إضافة 12 ساعة
        
        hours = int(time_offset)
        minutes = int((time_offset - hours) * 60)
        
        return f"{hours:02d}:{minutes:02d}"
    
    def api_aladhan_improved(self, date: datetime) -> Dict[str, str]:
        """استخدام API Aladhan مع خيارات متعددة"""
        try:
            date_str = date.strftime('%d-%m-%Y')
            
            # تجربة طرق مختلفة
            methods = [
                {'method': 4, 'school': 1, 'name': 'أم القرى - شافعي'},
                {'method': 2, 'school': 1, 'name': 'جامعة العلوم الإسلامية - شافعي'},
                {'method': 3, 'school': 1, 'name': 'جامعة أم القرى - شافعي'},
                {'method': 1, 'school': 1, 'name': 'جامعة أم القرى - حنفي'},
                {'method': 5, 'school': 1, 'name': 'جامعة أم القرى - مالكي'},
                {'method': 6, 'school': 1, 'name': 'جامعة أم القرى - حنبلي'},
                {'method': 7, 'school': 1, 'name': 'جامعة أم القرى - شافعي'},
                {'method': 8, 'school': 1, 'name': 'جامعة أم القرى - حنفي'},
                {'method': 9, 'school': 1, 'name': 'جامعة أم القرى - مالكي'},
                {'method': 10, 'school': 1, 'name': 'جامعة أم القرى - حنبلي'},
                {'method': 11, 'school': 1, 'name': 'جامعة أم القرى - شافعي'},
                {'method': 12, 'school': 1, 'name': 'جامعة أم القرى - حنفي'},
                {'method': 13, 'school': 1, 'name': 'جامعة أم القرى - مالكي'},
                {'method': 14, 'school': 1, 'name': 'جامعة أم القرى - حنبلي'},
                {'method': 15, 'school': 1, 'name': 'جامعة أم القرى - شافعي'},
                {'method': 16, 'school': 1, 'name': 'جامعة أم القرى - حنفي'},
                {'method': 17, 'school': 1, 'name': 'جامعة أم القرى - مالكي'},
                {'method': 18, 'school': 1, 'name': 'جامعة أم القرى - حنبلي'},
                {'method': 19, 'school': 1, 'name': 'جامعة أم القرى - شافعي'},
                {'method': 20, 'school': 1, 'name': 'جامعة أم القرى - حنفي'},
            ]
            
            results = {}
            for method in methods:
                url = f"http://api.aladhan.com/v1/timings/{date_str}"
                params = {
                    'latitude': self.latitude,
                    'longitude': self.longitude,
                    'method': method['method'],
                    'school': method['school']
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    timings = data['data']['timings']
                    
                    results[method['name']] = {
                        'Fajr': timings['Fajr'],
                        'Dhuhr': timings['Dhuhr'],
                        'Asr': timings['Asr'],
                        'Maghrib': timings['Maghrib'],
                        'Isha': timings['Isha']
                    }
            
            return results
            
        except Exception as e:
            print(f"خطأ في API Aladhan: {e}")
            return {}
    
    def api_prayertimes_org(self, date: datetime) -> Dict[str, str]:
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
            print(f"خطأ في API PrayerTimes.org: {e}")
            return {}
    
    def api_muslimsalat(self, date: datetime) -> Dict[str, str]:
        """استخدام API MuslimSalat"""
        try:
            date_str = date.strftime('%Y-%m-%d')
            url = f"http://muslimsalat.com/api/timings/{date_str}"
            params = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'timezone': 3  # توقيت دمشق
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                timings = data['timings']
                
                return {
                    'Fajr': timings['Fajr'],
                    'Dhuhr': timings['Dhuhr'],
                    'Asr': timings['Asr'],
                    'Maghrib': timings['Maghrib'],
                    'Isha': timings['Isha']
                }
        except Exception as e:
            print(f"خطأ في API MuslimSalat: {e}")
            return {}

def test_improved_methods():
    """اختبار الطرق المحسنة"""
    calculator = ImprovedPrayerTimes(DAMASCUS_LAT, DAMASCUS_LON)
    test_date = datetime(2025, 1, 1)
    
    print("=== مقارنة أوقات الصلاة المحسنة لليوم الأول من يناير 2025 ===")
    print(f"الموقع: دمشق ({DAMASCUS_LAT}, {DAMASCUS_LON})")
    print()
    
    # اختبار الطرق المحسوبة
    methods = {
        'الهيئة المصرية (محسنة)': calculator.method_accurate_egyptian,
        'أم القرى (محسنة)': calculator.method_accurate_umm_al_qura,
        'التقويم الهاشمي السوري (محسنة)': calculator.method_syrian_hashimi_improved
    }
    
    for method_name, method_func in methods.items():
        try:
            times = method_func(test_date)
            print(f"طريقة {method_name}:")
            for prayer, time in times.items():
                print(f"  {prayer}: {time}")
            print()
        except Exception as e:
            print(f"خطأ في {method_name}: {e}")
            print()
    
    # اختبار APIs
    print("=== اختبار APIs المحسنة ===")
    
    # اختبار Aladhan مع طرق متعددة
    aladhan_results = calculator.api_aladhan_improved(test_date)
    if aladhan_results:
        print("Aladhan API (طرق متعددة):")
        for method_name, times in aladhan_results.items():
            print(f"  {method_name}:")
            for prayer, time in times.items():
                print(f"    {prayer}: {time}")
        print()
    
    # اختبار APIs أخرى
    other_apis = {
        'PrayerTimes.org': calculator.api_prayertimes_org,
        'MuslimSalat': calculator.api_muslimsalat
    }
    
    for api_name, api_func in other_apis.items():
        times = api_func(test_date)
        if times:
            print(f"{api_name}:")
            for prayer, time in times.items():
                print(f"  {prayer}: {time}")
        else:
            print(f"{api_name}: غير متاح")
        print()

def generate_improved_prayer_times():
    """توليد أوقات الصلاة باستخدام الطرق المحسنة"""
    
    # إعدادات
    latitude = DAMASCUS_LAT
    longitude = DAMASCUS_LON
    start_date = datetime(2025, 1, 1)
    days = 365
    
    calculator = ImprovedPrayerTimes(latitude, longitude)
    
    # رأس ملف الهيدر C++
    header = """\
#ifndef IMPROVED_PRAYER_TIMES_H
#define IMPROVED_PRAYER_TIMES_H

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

// أوقات الصلاة بطريقة الهيئة المصرية المحسنة
const PrayerTime prayer_times_improved_egyptian[365] = {
"""
    
    footer = "};\n\n#endif // IMPROVED_PRAYER_TIMES_H"
    
    # توليد أوقات الصلاة لكل طريقة
    methods = {
        'improved_egyptian': calculator.method_accurate_egyptian,
        'improved_umm_al_qura': calculator.method_accurate_umm_al_qura,
        'improved_syrian_hashimi': calculator.method_syrian_hashimi_improved
    }
    
    for method_name, method_func in methods.items():
        print(f"جاري حساب أوقات الصلاة بطريقة: {method_name}")
        
        lines = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            
            try:
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
                
            except Exception as e:
                print(f"خطأ في حساب اليوم {date.strftime('%Y-%m-%d')}: {e}")
                continue
            
            # طباعة تقدم العمل
            if (i + 1) % 30 == 0:
                print(f"تم حساب {i + 1} يوم من أصل {days}")
        
        # كتابة الملف
        filename = f"prayer_times_{method_name}.h"
        with open(filename, "w", encoding='utf-8') as f:
            f.write(header + "\n".join(lines) + "\n" + footer)
        
        print(f"✅ تم توليد ملف {filename} بنجاح.")

if __name__ == "__main__":
    print("🚀 بدء توليد أوقات الصلاة المحسنة...")
    print()
    
    # اختبار الطرق أولاً
    test_improved_methods()
    
    # توليد الملفات
    generate_improved_prayer_times()
    
    print("✅ تم الانتهاء من جميع العمليات بنجاح!") 