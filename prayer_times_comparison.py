import requests
import json
from datetime import datetime, timedelta
import math
from typing import Dict, Tuple
import ephem

# إعدادات الموقع الجغرافي (دمشق)
DAMASCUS_LAT = 33.5138
DAMASCUS_LON = 36.2765

class PrayerTimesComparison:
    """فئة لمقارنة أوقات الصلاة من مصادر مختلفة"""
    
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        
    def get_all_methods(self, date: datetime) -> Dict[str, Dict[str, str]]:
        """الحصول على أوقات الصلاة من جميع الطرق المتاحة"""
        results = {}
        
        # الطرق المحسوبة باستخدام ephem
        try:
            results['الهيئة المصرية (ephem)'] = self._calculate_egyptian_ephem(date)
        except Exception as e:
            results['الهيئة المصرية (ephem)'] = {'error': str(e)}
        
        try:
            results['أم القرى (ephem)'] = self._calculate_umm_al_qura_ephem(date)
        except Exception as e:
            results['أم القرى (ephem)'] = {'error': str(e)}
        
        try:
            results['التقويم الهاشمي السوري (ephem)'] = self._calculate_syrian_hashimi_ephem(date)
        except Exception as e:
            results['التقويم الهاشمي السوري (ephem)'] = {'error': str(e)}
        
        # APIs
        aladhan_results = self._get_aladhan_methods(date)
        results.update(aladhan_results)
        
        return results
    
    def _calculate_egyptian_ephem(self, date: datetime) -> Dict[str, str]:
        """حساب أوقات الصلاة بطريقة الهيئة المصرية باستخدام ephem"""
        observer = ephem.Observer()
        observer.lat = str(self.latitude)
        observer.lon = str(self.longitude)
        observer.date = date
        
        sun = ephem.Sun()
        
        # الفجر (زاوية -18 درجة)
        observer.horizon = '-18'
        fajr = observer.next_rising(sun)
        
        # الظهر
        observer.horizon = '0'
        dhuhr = observer.next_transit(sun)
        
        # العصر
        asr_time = self._calculate_asr_ephem(date)
        
        # المغرب
        maghrib = observer.next_setting(sun)
        
        # العشاء (زاوية -17 درجة)
        observer.horizon = '-17'
        isha = observer.next_setting(sun)
        
        return {
            'Fajr': fajr.datetime().strftime('%H:%M'),
            'Dhuhr': dhuhr.datetime().strftime('%H:%M'),
            'Asr': asr_time,
            'Maghrib': maghrib.datetime().strftime('%H:%M'),
            'Isha': isha.datetime().strftime('%H:%M')
        }
    
    def _calculate_umm_al_qura_ephem(self, date: datetime) -> Dict[str, str]:
        """حساب أوقات الصلاة بطريقة أم القرى باستخدام ephem"""
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
        asr_time = self._calculate_asr_ephem(date)
        
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
    
    def _calculate_syrian_hashimi_ephem(self, date: datetime) -> Dict[str, str]:
        """حساب أوقات الصلاة بطريقة التقويم الهاشمي السوري باستخدام ephem"""
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
        asr_time = self._calculate_asr_ephem(date)
        
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
    
    def _calculate_asr_ephem(self, date: datetime) -> str:
        """حساب وقت العصر باستخدام ephem"""
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
    
    def _get_aladhan_methods(self, date: datetime) -> Dict[str, Dict[str, str]]:
        """الحصول على أوقات الصلاة من API Aladhan بطرق مختلفة"""
        results = {}
        
        try:
            date_str = date.strftime('%d-%m-%Y')
            
            # طرق مختلفة من Aladhan API
            methods = [
                {'method': 4, 'school': 1, 'name': 'Aladhan - أم القرى - شافعي'},
                {'method': 2, 'school': 1, 'name': 'Aladhan - جامعة العلوم الإسلامية - شافعي'},
                {'method': 3, 'school': 1, 'name': 'Aladhan - جامعة أم القرى - شافعي'},
                {'method': 1, 'school': 1, 'name': 'Aladhan - جامعة أم القرى - حنفي'},
                {'method': 5, 'school': 1, 'name': 'Aladhan - جامعة أم القرى - مالكي'},
                {'method': 6, 'school': 1, 'name': 'Aladhan - جامعة أم القرى - حنبلي'},
                {'method': 7, 'school': 1, 'name': 'Aladhan - جامعة أم القرى - شافعي'},
                {'method': 8, 'school': 1, 'name': 'Aladhan - جامعة أم القرى - حنفي'},
                {'method': 9, 'school': 1, 'name': 'Aladhan - جامعة أم القرى - مالكي'},
                {'method': 10, 'school': 1, 'name': 'Aladhan - جامعة أم القرى - حنبلي'},
            ]
            
            for method in methods:
                try:
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
                except Exception as e:
                    results[method['name']] = {'error': str(e)}
                    
        except Exception as e:
            results['Aladhan API'] = {'error': str(e)}
        
        return results

def print_comparison_table(all_results: Dict[str, Dict[str, str]], date: datetime):
    """طباعة جدول مقارنة أوقات الصلاة"""
    print(f"\n{'='*80}")
    print(f"مقارنة أوقات الصلاة لليوم: {date.strftime('%Y-%m-%d')}")
    print(f"الموقع: دمشق ({DAMASCUS_LAT}, {DAMASCUS_LON})")
    print(f"{'='*80}")
    
    # تحديد الطرق المتاحة
    methods = list(all_results.keys())
    prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
    
    # طباعة رأس الجدول
    header = f"{'الطريقة':<40}"
    for prayer in prayers:
        header += f"{prayer:>8}"
    print(header)
    print("-" * 80)
    
    # طباعة البيانات
    for method_name, times in all_results.items():
        if 'error' in times:
            print(f"{method_name:<40} {'خطأ':>8}")
        else:
            row = f"{method_name:<40}"
            for prayer in prayers:
                if prayer in times:
                    row += f"{times[prayer]:>8}"
                else:
                    row += f"{'N/A':>8}"
            print(row)
    
    print("-" * 80)

def find_best_matches(original_times: Dict[str, str], all_results: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """البحث عن أفضل التطابقات مع الأوقات الأصلية"""
    if 'error' in original_times:
        return {}
    
    best_matches = {}
    prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
    
    for prayer in prayers:
        if prayer not in original_times:
            continue
            
        original_time = original_times[prayer]
        best_method = None
        min_diff = float('inf')
        
        for method_name, times in all_results.items():
            if 'error' in times or prayer not in times:
                continue
                
            # تحويل الأوقات إلى دقائق للمقارنة
            try:
                orig_h, orig_m = map(int, original_time.split(':'))
                orig_minutes = orig_h * 60 + orig_m
                
                comp_h, comp_m = map(int, times[prayer].split(':'))
                comp_minutes = comp_h * 60 + comp_m
                
                diff = abs(orig_minutes - comp_minutes)
                
                if diff < min_diff:
                    min_diff = diff
                    best_method = method_name
                    
            except ValueError:
                continue
        
        if best_method:
            best_matches[prayer] = {
                'method': best_method,
                'time': all_results[best_method][prayer],
                'difference_minutes': min_diff
            }
    
    return best_matches

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء مقارنة أوقات الصلاة...")
    
    # إنشاء كائن المقارنة
    comparator = PrayerTimesComparison(DAMASCUS_LAT, DAMASCUS_LON)
    
    # اختبار عدة أيام
    test_dates = [
        datetime(2025, 1, 1),   # الشتاء
        datetime(2025, 6, 21),  # الصيف
        datetime(2025, 3, 21),  # الربيع
        datetime(2025, 9, 23),  # الخريف
    ]
    
    for test_date in test_dates:
        # الحصول على جميع النتائج
        all_results = comparator.get_all_methods(test_date)
        
        # طباعة جدول المقارنة
        print_comparison_table(all_results, test_date)
        
        # البحث عن أفضل التطابقات مع الأوقات الأصلية (من الكود الأصلي)
        # هذه قيم تقريبية من الكود الأصلي
        original_times = {
            'Fajr': '06:23',
            'Dhuhr': '12:39',
            'Asr': '15:16',
            'Maghrib': '17:52',
            'Isha': '18:45'
        }
        
        best_matches = find_best_matches(original_times, all_results)
        
        if best_matches:
            print(f"\nأفضل التطابقات مع الأوقات الأصلية:")
            for prayer, match in best_matches.items():
                print(f"  {prayer}: {match['method']} - {match['time']} (فرق: {match['difference_minutes']} دقيقة)")
        
        print("\n" + "="*80 + "\n")
    
    print("✅ تم الانتهاء من المقارنة!")

if __name__ == "__main__":
    main() 