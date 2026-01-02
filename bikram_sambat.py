#!/usr/bin/env python3

import json
import os
import sys
import datetime
from pathlib import Path

# ---------------- CONFIG ---------------- #

# Path to the data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), "bs_data")

NEPALI_MONTHS_EN = {
    1: "Baishakh", 2: "Jestha", 3: "Ashad", 4: "Shrawan",
    5: "Bhadra", 6: "Ashwin", 7: "Kartik", 8: "Mangsir",
    9: "Poush", 10: "Magh", 11: "Falgun", 12: "Chaitra"
}

# Cache for loaded years
_YEAR_CACHE = {}

# ---------------------------------------- #

def get_year_data(year):
    """Load data for a specific BS year"""
    year_str = str(year)
    if year_str in _YEAR_CACHE:
        return _YEAR_CACHE[year_str]
    
    file_path = os.path.join(DATA_DIR, f"{year_str}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _YEAR_CACHE[year_str] = data
                return data
        except Exception:
            return None
    return None

def get_bs_month_data(year, month):
    """
    Get BS month data from local file.
    Returns a dict with 'days' list suitable for the calendar widget.
    """
    year_data = get_year_data(year)
    if not year_data:
        return None
    
    # Access data: year_data[str(month)]
    month_str = str(month)
    
    if month_str not in year_data:
        return None
        
    data = year_data[month_str]

    days = []
    for day_data in data:
        info = day_data.get("calendarInfo", {})
        bs = info.get("dates", {}).get("bs", {})
        ad = info.get("dates", {}).get("ad", {})
        events = day_data.get("eventDetails", [])
        
        bs_day = int(bs.get("day", {}).get("en", 0))
        ad_date_str = ad.get("full", {}).get("en")
        
        if ad_date_str:
            dt = datetime.datetime.strptime(ad_date_str, "%Y-%m-%d").date()
            weekday_idx = (dt.weekday() + 1) % 7 # 0=Sun
        else:
            weekday_idx = 0

        days.append({
            "bs_day": weekday_idx, 
            "bs_date": bs_day,     
            "ad_date": ad_date_str,
            "events": events
        })
    
    return {"days": days}

def ad_to_bs_date(ad_date):
    """
    Convert AD date to BS date (Year, Month, Day).
    """
    if ad_date.month < 4:
        bs_year_guess = ad_date.year + 56
    else:
        bs_year_guess = ad_date.year + 57
        
    likely_month = (ad_date.month + 8) % 12
    if likely_month == 0: likely_month = 12
    
    search_order = [likely_month, likely_month-1, likely_month+1]
    search_order = [m if m > 0 else 12 for m in search_order]
    search_order = [m if m <= 12 else 1 for m in search_order]
    
    # JSON uses YYYY-M-D format (no leading zeros), while isoformat uses YYYY-MM-DD
    target_ad = f"{ad_date.year}-{ad_date.month}-{ad_date.day}"
    
    for m in search_order:
        year_str = str(bs_year_guess)
        month_str = str(m)
        
        year_data = get_year_data(bs_year_guess)
        if year_data and month_str in year_data:
            data = year_data[month_str]
            for day in data:
                info = day.get("calendarInfo", {})
                ad = info.get("dates", {}).get("ad", {})
                if ad.get("full", {}).get("en") == target_ad:
                    bs = info.get("dates", {}).get("bs", {})
                    return (
                        int(bs.get("year", {}).get("en")),
                        int(bs.get("month", {}).get("code", {}).get("en")),
                        int(bs.get("day", {}).get("en"))
                    )
    return None

def format_bs_date(year, month, day, use_nepali=False):
    """Format BS date string"""
    month_name = NEPALI_MONTHS_EN.get(month, str(month))
    return f"{month_name} {day}, {year}"

def get_events_for_ad_date(ad_date):
    """Get events for a specific AD date from BS calendar"""
    bs_date = ad_to_bs_date(ad_date)
    if not bs_date:
        return None
        
    year, month, day = bs_date
    
    year_data = get_year_data(year)
    if not year_data:
        return None
        
    month_str = str(month)
    if month_str not in year_data:
        return None
        
    data = year_data[month_str]
        
    for d in data:
        info = d.get("calendarInfo", {})
        bs = info.get("dates", {}).get("bs", {})
        if int(bs.get("day", {}).get("en")) == day:
            # Extract events
            raw_events = d.get("eventDetails", [])
            processed_events = []
            for evt in raw_events:
                title_obj = evt.get("title", {})
                title = title_obj.get("en") or title_obj.get("np") or "Unknown Event"
                
                category_obj = evt.get("category", {})
                category = category_obj.get("name", "Event").capitalize()
                
                processed_events.append({
                    "title": title,
                    "category": category
                })

            # Extract tithi
            tithi_details = d.get("tithiDetails")
            tithi = ""
            if tithi_details:
                tithi_obj = tithi_details.get("title", {})
                tithi = tithi_obj.get("en") or tithi_obj.get("np") or ""

            return {
                "events": processed_events,
                "tithi": tithi
            }
    return None

def get_today_bs(data):
    """
    Extract today's BS date from month data
    """
    today = datetime.date.today().isoformat()

    for day in data:
        info = day.get("calendarInfo", {})
        ad = info.get("dates", {}).get("ad", {})

        if ad.get("full", {}).get("en") == today:
            return info

    return None

def waybar_output(text, tooltip=None):
    out = {"text": text}
    if tooltip:
        out["tooltip"] = tooltip
    print(json.dumps(out, ensure_ascii=False))

def main():
    today = datetime.date.today()
    bs_date = ad_to_bs_date(today)
    
    if bs_date:
        year, month, day = bs_date
        
        year_data = get_year_data(year)
        if year_data and str(month) in year_data:
            data = year_data[str(month)]
            today_info = get_today_bs(data)
            if today_info:
                bs = today_info["dates"]["bs"]
                d = bs["day"]["np"]
                m = bs["month"]["np"]
                y = bs["year"]["np"]
                weekday = today_info["days"]["dayOfWeek"]["np"]
                
                text = f"{d} {m}"
                tooltip = f"{d} {m} {y}\n{weekday}"
                waybar_output(text, tooltip)
                return

    waybar_output("BS ?", "Calendar unavailable")

if __name__ == "__main__":
    main()
