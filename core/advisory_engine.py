# core/advisory_engine.py

import requests
from datetime import date, timedelta, datetime
from django.utils import timezone
from .models import Advisory, ActivityLog, Crop
import logging

# It's good practice to use Django's logging
logger = logging.getLogger(__name__)

# District coordinates mapping (same as before)
DISTRICT_COORDINATES = {
    "തിരുവനന്തപുരം": {"lat": 8.5241, "lng": 76.9366}, "കൊല്ലം": {"lat": 8.8932, "lng": 76.6141},
    "പത്തനംതിട്ട": {"lat": 9.2648, "lng": 76.7870}, "ആലപ്പുഴ": {"lat": 9.4981, "lng": 76.3388},
    "കോട്ടയം": {"lat": 9.5916, "lng": 76.5222}, "ഇടുക്കി": {"lat": 9.8560, "lng": 76.9774},
    "എറണാകുളം": {"lat": 9.9312, "lng": 76.2673}, "ത്രിശ്ശൂർ": {"lat": 10.5276, "lng": 76.2144},
    "പാലക്കാട്": {"lat": 10.7867, "lng": 76.6548}, "മലപ്പുറം": {"lat": 11.0510, "lng": 76.0711},
    "കോഴിക്കോട്": {"lat": 11.2588, "lng": 75.7804}, "വയനാട്": {"lat": 11.6854, "lng": 76.1320},
    "കണ്ണൂർ": {"lat": 11.8745, "lng": 75.3704}, "കാസർഗോഡ്": {"lat": 12.4996, "lng": 74.9869}
}

def get_weather_forecast(district: str):
    """
    Fetches and processes 5-day weather forecast.
    Returns a simplified dictionary or None on failure.
    """
    coordinates = DISTRICT_COORDINATES.get(district)
    if not coordinates:
        logger.warning(f"District '{district}' not found in coordinates mapping.")
        return None

    # IMPORTANT: Replace with your actual, non-expired RapidAPI key
    api_key = "a38a439451mshb66f632a04aaa95p137671jsn9f7929dd8de6" 
    if not api_key:
        logger.error("RapidAPI key is not set. Weather forecast will not work.")
        return None
        
    url = "https://open-weather13.p.rapidapi.com/fivedaysforcast"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "open-weather13.p.rapidapi.com"
    }
    params = {"latitude": coordinates["lat"], "longitude": coordinates["lng"]}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if not data.get("list"):
            return None

        forecast_by_day = {}
        for item in data["list"]:
            day_key = datetime.fromtimestamp(item["dt"]).date()
            if day_key not in forecast_by_day:
                forecast_by_day[day_key] = []
            
            forecast_by_day[day_key].append({
                "temp": round(item["main"]["temp"] - 273.15, 1),
                "humidity": item["main"]["humidity"],
                "description": item["weather"][0]["description"],
                "main": item["weather"][0]["main"],
                "rain_3h": item.get("rain", {}).get("3h", 0),
            })

        processed_forecast = []
        for day, forecasts in forecast_by_day.items():
            if not forecasts: continue
            processed_forecast.append({
                "date": day,
                "max_temp": max(f['temp'] for f in forecasts),
                "min_temp": min(f['temp'] for f in forecasts),
                "avg_humidity": sum(f['humidity'] for f in forecasts) / len(forecasts),
                "will_rain": any(f['rain_3h'] > 0 for f in forecasts),
                "total_rain": sum(f['rain_3h'] for f in forecasts),
                "conditions": [f['main'] for f in forecasts]
            })
        
        return sorted(processed_forecast, key=lambda x: x['date'])

    except requests.RequestException as e:
        logger.error(f"Error fetching weather data for {district}: {e}")
        return None


def analyze_crop_and_weather(crop: Crop, weather_forecast: list):
    """
    The core analysis function.
    Decides what actions are needed based on logs and weather.
    """
    today = timezone.now().date()
    advisories = []

    # --- Get Recent Activity ---
    # Fetch the last log for each activity type
    last_irrigation_log = ActivityLog.objects.filter(crop=crop, did_irrigate=True).order_by('-date').first()
    last_fertilizer_log = ActivityLog.objects.filter(crop=crop, did_fertilize=True).order_by('-date').first()
    last_pesticide_log = ActivityLog.objects.filter(crop=crop, did_apply_pesticide=True).order_by('-date').first()

    days_since_irrigation = (today - last_irrigation_log.date).days if last_irrigation_log else 99
    days_since_fertilizer = (today - last_fertilizer_log.date).days if last_fertilizer_log else 99
    days_since_pesticide = (today - last_pesticide_log.date).days if last_pesticide_log else 99
    
    crop_age = (today - crop.sown_date).days if crop.is_sown and crop.sown_date else None

    # --- Weather Analysis ---
    rain_today = False
    rain_in_next_2_days = False
    high_temp_alert = False
    high_humidity_alert = False

    if weather_forecast and len(weather_forecast) > 0:
        today_weather = weather_forecast[0]
        if today_weather['date'] == today:
            rain_today = today_weather['will_rain']
            if today_weather['max_temp'] > 35:
                high_temp_alert = True
                advisories.append({
                    "message": f"High temperature warning ({today_weather['max_temp']}°C). Ensure your crop has enough water.",
                    "category": "URGENT"
                })
            if today_weather['avg_humidity'] > 85:
                high_humidity_alert = True
        
        # Check for rain in the next 2 days to advise on holding irrigation
        rain_in_next_2_days = any(d['will_rain'] for d in weather_forecast[:3])

    # --- Rule-Based Advisory Generation ---

    # 1. Irrigation Logic
    if rain_in_next_2_days:
        advisories.append({
            "message": "Rain is expected in the next 2 days. You may be able to skip irrigation.",
            "category": "TIP"
        })
    elif days_since_irrigation >= 3 or (days_since_irrigation >= 2 and high_temp_alert):
        advisories.append({
            "message": f"It's been {days_since_irrigation} days since the last irrigation. It's time to water your crop.",
            "category": "ROUTINE"
        })
    
    # 2. Fertilizer Logic
    # Apply fertilizer after 15 days, and then every 20 days.
    if crop_age is not None:
        if 15 <= crop_age < 20 and days_since_fertilizer > 15:
             advisories.append({
                "message": f"Your crop is about {crop_age} days old. It's a good time for the first fertilizer application.",
                "category": "ROUTINE"
            })
        elif days_since_fertilizer >= 20:
             advisories.append({
                "message": f"It's been {days_since_fertilizer} days. Consider applying fertilizer. Recommended: {crop.fertilizer or 'a balanced NPK mix'}.",
                "category": "ROUTINE"
            })

    # 3. Pesticide Logic
    if high_humidity_alert:
        advisories.append({
            "message": "High humidity increases the risk of fungal diseases. Inspect your plants closely.",
            "category": "URGENT"
        })
    elif days_since_pesticide >= 21:
        advisories.append({
            "message": f"It's been {days_since_pesticide} days since the last application. Check for pests. If needed, apply {crop.pesticide or 'an appropriate pesticide'}.",
            "category": "ROUTINE"
        })

    # 4. Sowing/Harvesting Reminders
    current_month = today.strftime("%B")
    if not crop.is_sown and crop.sowing_months and current_month in crop.sowing_months:
        advisories.append({
            "message": f"Now is a great time to sow {crop.name}! The current month is ideal for sowing.",
            "category": "TIP"
        })
    
    if crop.is_sown and not crop.is_harvested and crop.harvesting_months and current_month in crop.harvesting_months:
        advisories.append({
            "message": f"Your {crop.name} might be ready for harvest. Check for signs of maturity.",
            "category": "ROUTINE"
        })
    
    # --- Fallback/General Tip ---
    if not advisories:
        advisories.append({
            "message": "Everything looks good! Continue to monitor your crop daily for any changes.",
            "category": "TIP"
        })
    
    # Add a generic tip if there are few advisories
    if len(advisories) < 2:
        advisories.append({
            "message": f"Did you know? Proper sunlight ({crop.sunlight_hours or '6-8'} hours) is crucial for healthy {crop.name} growth.",
            "category": "TIP"
        })

    return advisories


def generate_advisories_for_crop(crop: Crop):
    """
    Public function to trigger the advisory generation for a single crop.
    This will delete old advisories and create new ones for today.
    """
    today = timezone.now().date()
    
    # Clean up old advisories for this crop from today to avoid duplicates
    Advisory.objects.filter(crop=crop, date=today).delete()
    
    # Fetch fresh weather data
    weather_forecast = get_weather_forecast(crop.user.district)
    
    # Get a list of advisory messages and categories
    advisory_data = analyze_crop_and_weather(crop, weather_forecast)
    
    # Create new Advisory objects in the database
    saved_advisories = []
    for data in advisory_data:
        advisory = Advisory.objects.create(
            crop=crop,
            message=data["message"],
            category=data["category"],
            date=today,
            is_acknowledged=False  # Always start as unread
        )
        saved_advisories.append(advisory)
        
    logger.info(f"Generated {len(saved_advisories)} new advisories for crop {crop.id} ({crop.name}).")
    return saved_advisories

def get_weather_summary(district: str):
    """
    Simplified weather summary for the AJAX endpoint.
    """
    forecast = get_weather_forecast(district)
    if not forecast or forecast[0]['date'] != timezone.now().date():
        return {"status": "unavailable", "message": "Weather data could not be fetched."}
    
    current_day = forecast[0]
    return {
        "status": "available",
        "temperature": current_day['max_temp'],
        "description": f"Max temp {current_day['max_temp']}°C, Min {current_day['min_temp']}°C",
        "humidity": round(current_day['avg_humidity']),
        "has_rain": current_day['will_rain']
    }