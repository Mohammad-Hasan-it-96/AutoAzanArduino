from datetime import datetime
import requests
import json
from typing import Dict, List

# Actual Roznama prayer times for 2025-01-01
ROZNAMA_TIMES = {
    'Fajr': '06:04',
    'Dhuhr': '12:40', 
    'Asr': '15:16',
    'Maghrib': '17:36',
    'Isha': '19:06'
}

# Damascus coordinates
DAMASCUS_LAT = 33.5138
DAMASCUS_LON = 36.2765

def test_aladhan_methods():
    """Test all Aladhan API methods to find the best match for Roznama times"""
    date_str = "01-01-2025"
    
    print("🔍 Searching for best match to Roznama prayer times...")
    print(f"Roznama times for 2025-01-01:")
    for prayer, time in ROZNAMA_TIMES.items():
        print(f"  {prayer}: {time}")
    print()
    
    # Test all available Aladhan methods
    methods = [
        {'method': 1, 'school': 1, 'name': 'Method 1 - Hanafi'},
        {'method': 2, 'school': 1, 'name': 'Method 2 - Shafi'},
        {'method': 3, 'school': 1, 'name': 'Method 3 - Shafi'},
        {'method': 4, 'school': 1, 'name': 'Method 4 - Shafi'},
        {'method': 5, 'school': 1, 'name': 'Method 5 - Shafi'},
        {'method': 6, 'school': 1, 'name': 'Method 6 - Shafi'},
        {'method': 7, 'school': 1, 'name': 'Method 7 - Shafi'},
        {'method': 8, 'school': 1, 'name': 'Method 8 - Shafi'},
        {'method': 9, 'school': 1, 'name': 'Method 9 - Shafi'},
        {'method': 10, 'school': 1, 'name': 'Method 10 - Shafi'},
        {'method': 11, 'school': 1, 'name': 'Method 11 - Shafi'},
        {'method': 12, 'school': 1, 'name': 'Method 12 - Shafi'},
        {'method': 13, 'school': 1, 'name': 'Method 13 - Shafi'},
        {'method': 14, 'school': 1, 'name': 'Method 14 - Shafi'},
        {'method': 15, 'school': 1, 'name': 'Method 15 - Shafi'},
        {'method': 16, 'school': 1, 'name': 'Method 16 - Shafi'},
        {'method': 17, 'school': 1, 'name': 'Method 17 - Shafi'},
        {'method': 18, 'school': 1, 'name': 'Method 18 - Shafi'},
        {'method': 19, 'school': 1, 'name': 'Method 19 - Shafi'},
        {'method': 20, 'school': 1, 'name': 'Method 20 - Shafi'},
    ]
    
    results = []
    
    for method in methods:
        try:
            url = f"http://api.aladhan.com/v1/timings/{date_str}"
            params = {
                'latitude': DAMASCUS_LAT,
                'longitude': DAMASCUS_LON,
                'method': method['method'],
                'school': method['school']
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                timings = data['data']['timings']
                
                # Calculate total difference
                total_diff = 0
                differences = {}
                
                for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
                    if prayer in timings and prayer in ROZNAMA_TIMES:
                        # Convert times to minutes for comparison
                        roz_h, roz_m = map(int, ROZNAMA_TIMES[prayer].split(':'))
                        roz_minutes = roz_h * 60 + roz_m
                        
                        api_h, api_m = map(int, timings[prayer].split(':'))
                        api_minutes = api_h * 60 + api_m
                        
                        diff = abs(roz_minutes - api_minutes)
                        total_diff += diff
                        differences[prayer] = diff
                
                results.append({
                    'method': method['name'],
                    'timings': timings,
                    'total_diff': total_diff,
                    'differences': differences
                })
                
                print(f"✅ {method['name']}:")
                for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
                    if prayer in timings:
                        diff = differences.get(prayer, 0)
                        print(f"  {prayer}: {timings[prayer]} (diff: {diff} min)")
                print()
                
        except Exception as e:
            print(f"❌ {method['name']}: Error - {e}")
    
    # Sort by total difference (best match first)
    results.sort(key=lambda x: x['total_diff'])
    
    print("🏆 BEST MATCHES (sorted by total difference):")
    print("=" * 80)
    
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result['method']} - Total diff: {result['total_diff']} minutes")
        for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if prayer in result['timings']:
                diff = result['differences'].get(prayer, 0)
                print(f"   {prayer}: {result['timings'][prayer]} (diff: {diff} min)")
        print()

def test_custom_angles():
    """Test custom angles to find the best match for Roznama times"""
    print("🔧 Testing custom angles for better match...")
    print()
    
    # Test different Fajr angles
    fajr_angles = [-15, -16, -17, -18, -19, -20, -21, -22, -23, -24, -25]
    isha_angles = [-15, -16, -17, -18, -19, -20]
    
    best_match = None
    best_total_diff = float('inf')
    
    for fajr_angle in fajr_angles:
        for isha_angle in isha_angles:
            # This is a simplified calculation - in practice you'd use ephem
            # For now, let's just show the concept
            print(f"Testing Fajr: {fajr_angle}°, Isha: {isha_angle}°")
    
    print("Note: Custom angle testing would require implementing with ephem library")

if __name__ == "__main__":
    test_aladhan_methods()
    test_custom_angles() 