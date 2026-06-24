from __future__ import annotations

import sys
from datetime import datetime
from typing import List, Tuple


DAYS_IN_MONTH = [
    31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31
]


def prompt_int(prompt: str, min_value: int, max_value: int) -> int:
    """Prompt the user for an integer within [min_value, max_value]."""
    while True:
        raw = input(prompt).strip()
        if raw.isdigit():
            value = int(raw)
            if min_value <= value <= max_value:
                return value
        print(f"Please enter a number between {min_value} and {max_value}.")


def prompt_filename(default_name: str) -> str:
    """Prompt for output filename with a default."""
    raw = input(f"Output filename [{default_name}]: ").strip()
    return raw or default_name


def build_dates_for_year(year: int) -> List[Tuple[int, int]]:
    """Build a list of (day, month) tuples for a non-leap year (365 days)."""
    # Always return 365 days to match the header format used in this project
    dates: List[Tuple[int, int]] = []
    for month_idx, days in enumerate(DAYS_IN_MONTH, start=1):
        for day in range(1, days + 1):
            dates.append((day, month_idx))
    return dates


def write_header(filename: str, entries: List[Tuple[int, int, int, int, int, int, int, int, int, int]]):
    """Write the .h file with the same structure/signature as prayer_times.h."""
    # entries: (day, month, fajr_h, fajr_m, dhuhr_h, dhuhr_m, asr_h, asr_m, maghrib_h, maghrib_m, isha_h, isha_m)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#ifndef PRAYER_TIMES_H\n")
        f.write("#define PRAYER_TIMES_H\n\n")
        f.write("typedef struct {\n")
        f.write("  uint8_t day;\n")
        f.write("  uint8_t month;\n")
        f.write("  uint8_t fajr_hour;\n")
        f.write("  uint8_t fajr_min;\n")
        f.write("  uint8_t dhuhr_hour;\n")
        f.write("  uint8_t dhuhr_min;\n")
        f.write("  uint8_t asr_hour;\n")
        f.write("  uint8_t asr_min;\n")
        f.write("  uint8_t maghrib_hour;\n")
        f.write("  uint8_t maghrib_min;\n")
        f.write("  uint8_t isha_hour;\n")
        f.write("  uint8_t isha_min;\n")
        f.write("} PrayerTime;\n\n")
        f.write("const PrayerTime prayer_times[365] = {\n")

        for idx, (day, month, fh, fm, dh, dm, ah, am, mh, mm, ih, im) in enumerate(entries):
            line = (
                f"  {{{day}, {month}, {fh}, {fm}, {dh}, {dm}, {ah}, {am}, {mh}, {mm}, {ih}, {im}}}"
            )
            if idx < len(entries) - 1:
                line += ","
            f.write(line + "\n")

        f.write("};\n\n")
        f.write("#endif // PRAYER_TIMES_H\n")


def main():
    print("Manual Prayer Times Builder (365 days)")
    print("=====================================")
    print("This tool will ask for each prayer time field, day by day.")
    print("Enter numeric values and press Enter to move to the next step.\n")

    # Choose year (for day/month labeling only)
    current_year = datetime.now().year
    year_raw = input(f"Enter year for labeling [{current_year}]: ").strip()
    year = int(year_raw) if year_raw.isdigit() else current_year

    # Prepare date list (365 days, non-leap)
    dates = build_dates_for_year(year)
    if len(dates) != 365:
        print("Internal error: dates list must be 365 entries.")
        sys.exit(1)

    output_filename = prompt_filename("prayer_times.h")
    print()

    entries: List[Tuple[int, int, int, int, int, int, int, int, int, int]] = []

    print("Start entering times. Format is 24-hour.\n")

    for i, (day, month) in enumerate(dates, start=1):
        print(f"Day {i}/365  ({day}-{month})")

        fajr_h = prompt_int(f"  add fajr hour for {day} - {month} (0-23): ", 0, 23)
        fajr_m = prompt_int(f"  add fajr min for {day} - {month} (0-59): ", 0, 59)

        dhuhr_h = prompt_int(f"  add dhuhr hour for {day} - {month} (0-23): ", 0, 23)
        dhuhr_m = prompt_int(f"  add dhuhr min for {day} - {month} (0-59): ", 0, 59)

        asr_h = prompt_int(f"  add asr hour for {day} - {month} (0-23): ", 0, 23)
        asr_m = prompt_int(f"  add asr min for {day} - {month} (0-59): ", 0, 59)

        maghrib_h = prompt_int(f"  add maghrib hour for {day} - {month} (0-23): ", 0, 23)
        maghrib_m = prompt_int(f"  add maghrib min for {day} - {month} (0-59): ", 0, 59)

        isha_h = prompt_int(f"  add isha hour for {day} - {month} (0-23): ", 0, 23)
        isha_m = prompt_int(f"  add isha min for {day} - {month} (0-59): ", 0, 59)

        entries.append((day, month, fajr_h, fajr_m, dhuhr_h, dhuhr_m, asr_h, asr_m, maghrib_h, maghrib_m, isha_h, isha_m))

        input("  Press Enter to continue to next day...")
        print()

    print("Writing header file...\n")
    write_header(output_filename, entries)
    print(f"Done. Generated {output_filename}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.")

