# advisory_engine.py

import requests
from datetime import date, timedelta, datetime
from django.utils import timezone
from .models import Advisory, ActivityLog
import json
import logging

logger = logging.getLogger(__name__)

# District coordinates mapping (same as in your JavaScript)
DISTRICT_COORDINATES = {
    "തിരുവനന്തപുരം": {"lat": 8.5241, "lng": 76.9366, "name": "Thiruvananthapuram"},
    "കൊല്ലം": {"lat": 8.8932, "lng": 76.6141, "name": "Kollam"},
    "പത്തനംതിട്ട": {"lat": 9.2648, "lng": 76.7870, "name": "Pathanamthitta"},
    "ആലപ്പുഴ": {"lat": 9.4981, "lng": 76.3388, "name": "Alappuzha"},
    "കോട്ടയം": {"lat": 9.5916, "lng": 76.5222, "name": "Kottayam"},
    "ഇടുക്കി": {"lat": 9.8560, "lng": 76.9774, "name": "Idukki"},
    "എറണാകുളം": {"lat": 9.9312, "lng": 76.2673, "name": "Ernakulam"},
    "ത്രിശ്ശൂർ": {"lat": 10.5276, "lng": 76.2144, "name": "Thrissur"},
    "പാലക്കാട്": {"lat": 10.7867, "lng": 76.6548, "name": "Palakkad"},
    "മലപ്പുറം": {"lat": 11.0510, "lng": 76.0711, "name": "Malappuram"},
    "കോഴിക്കോട്": {"lat": 11.2588, "lng": 75.7804, "name": "Kozhikode"},
    "വയനാട്": {"lat": 11.6854, "lng": 76.1320, "name": "Wayanad"},
    "കണ്ണൂർ": {"lat": 11.8745, "lng": 75.3704, "name": "Kannur"},
    "കാസർഗോഡ്": {"lat": 12.4996, "lng": 74.9869, "name": "Kasaragod"}
}

def get_weather_forecast(district):
    """
    Fetch real weather data using the same API as dashboard
    Returns weather for today and next 5 days
    """
    try:
        coordinates = DISTRICT_COORDINATES.get(district)
        if not coordinates:
            logger.warning(f"District {district} not found in coordinates mapping")
            return None
        
        url = f"https://open-weather13.p.rapidapi.com/fivedaysforcast"
        
        headers = {
            "x-rapidapi-key": "a38a439451mshb66f632a04aaa95p137671jsn9f7929dd8de6",
            "x-rapidapi-host": "open-weather13.p.rapidapi.com"
        }
        
        params = {
            "latitude": coordinates["lat"],
            "longitude": coordinates["lng"],
            "lang": "EN"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Process the forecast data
            forecast = {
                "current": None,
                "today": [],
                "tomorrow": [],
                "week": []
            }
            
            if data.get("list"):
                # Group forecasts by day
                daily_forecasts = {}
                today = datetime.now().date()
                
                for item in data["list"]:
                    dt = datetime.fromtimestamp(item["dt"])
                    day_key = dt.date()
                    
                    if day_key not in daily_forecasts:
                        daily_forecasts[day_key] = []
                    
                    daily_forecasts[day_key].append({
                        "time": dt.strftime("%H:%M"),
                        "temp_c": round(item["main"]["temp"] - 273.15, 1),
                        "feels_like_c": round(item["main"]["feels_like"] - 273.15, 1),
                        "humidity": item["main"]["humidity"],
                        "description": item["weather"][0]["description"],
                        "main": item["weather"][0]["main"],
                        "wind_speed": item["wind"]["speed"],
                        "rain_3h": item.get("rain", {}).get("3h", 0),
                        "clouds": item["clouds"]["all"]
                    })
                
                # Set current weather (first item)
                if data["list"]:
                    first = data["list"][0]
                    forecast["current"] = {
                        "temp_c": round(first["main"]["temp"] - 273.15, 1),
                        "feels_like_c": round(first["main"]["feels_like"] - 273.15, 1),
                        "humidity": first["main"]["humidity"],
                        "description": first["weather"][0]["description"],
                        "main": first["weather"][0]["main"],
                        "wind_speed": first["wind"]["speed"],
                        "rain": first.get("rain", {}).get("3h", 0) > 0
                    }
                
                # Organize by day
                for day_key in sorted(daily_forecasts.keys()):
                    if day_key == today:
                        forecast["today"] = daily_forecasts[day_key]
                    elif day_key == today + timedelta(days=1):
                        forecast["tomorrow"] = daily_forecasts[day_key]
                    
                    # Add to week forecast
                    day_summary = {
                        "date": day_key,
                        "forecasts": daily_forecasts[day_key],
                        "max_temp": max(f["temp_c"] for f in daily_forecasts[day_key]),
                        "min_temp": min(f["temp_c"] for f in daily_forecasts[day_key]),
                        "avg_humidity": sum(f["humidity"] for f in daily_forecasts[day_key]) / len(daily_forecasts[day_key]),
                        "total_rain": sum(f["rain_3h"] for f in daily_forecasts[day_key]),
                        "has_rain": any(f["rain_3h"] > 0 for f in daily_forecasts[day_key])
                    }
                    forecast["week"].append(day_summary)
                
            return forecast
            
    except requests.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in weather fetch: {e}")
        return None
def analyze_crop_conditions(crop, weather_forecast):
    """
    Analyze crop conditions based on weather and activity logs
    """
    today = timezone.now().date()
    analysis = {
        "irrigation_needed": False,
        "fertilizer_needed": False,
        "pesticide_check": False,
        "harvest_reminder": False,
        "sowing_reminder": False,
        "weather_alerts": [],
        "care_tips": []
    }
    
    # Get recent activity logs
    recent_logs = ActivityLog.objects.filter(
        crop=crop
    ).order_by('-date')[:7]
    
    last_irrigation = None
    last_fertilizer = None
    last_pesticide = None
    
    for log in recent_logs:
        if getattr(log, 'did_irrigate', False) and not last_irrigation:
            last_irrigation = log.date
        if getattr(log, 'did_fertilize', False) and not last_fertilizer:
            last_fertilizer = log.date
        if getattr(log, 'did_apply_pesticide', False) and not last_pesticide:
            last_pesticide = log.date
    
    # Default weather values (safe defaults if API fails)
    rain_today = False
    rain_tomorrow = False
    current = {}
    today_forecast = []
    tomorrow_forecast = []
    week_forecast = []
    
    # Weather-based analysis
    if weather_forecast:
        current = weather_forecast.get("current", {}) or {}
        today_forecast = weather_forecast.get("today", []) or []
        tomorrow_forecast = weather_forecast.get("tomorrow", []) or []
        week_forecast = weather_forecast.get("week", []) or []
        
        # Check for rain in next 48 hours
        rain_today = any(f.get("rain_3h", 0) > 0 for f in today_forecast)
        rain_tomorrow = any(f.get("rain_3h", 0) > 0 for f in tomorrow_forecast)
        
        # Temperature analysis
        if current:
            temp = current.get("temp_c", None)
            humidity = current.get("humidity", None)
            
            # High temperature check
            if temp is not None and temp > 35:
                analysis["weather_alerts"].append({
                    "type": "high_temp",
                    "message": f"High temperature alert: {temp}°C",
                    "severity": "warning"
                })
                analysis["irrigation_needed"] = True
                analysis["care_tips"].append("Consider providing shade during peak hours")
            
            # Low temperature check
            if temp is not None and temp < 15:
                analysis["weather_alerts"].append({
                    "type": "low_temp",
                    "message": f"Low temperature alert: {temp}°C",
                    "severity": "info"
                })
                analysis["care_tips"].append("Monitor for frost damage")
            
            # Humidity analysis
            if humidity is not None:
                if humidity > 85:
                    analysis["pesticide_check"] = True
                    analysis["care_tips"].append("High humidity may increase fungal disease risk")
                elif humidity < 30:
                    analysis["irrigation_needed"] = True
                    analysis["care_tips"].append("Low humidity - ensure adequate soil moisture")
        
        # Rain forecast analysis
        if rain_today:
            analysis["weather_alerts"].append({
                "type": "rain",
                "message": "Rain expected today",
                "severity": "info"
            })
            if last_irrigation and (today - last_irrigation).days <= 1:
                analysis["care_tips"].append("Skip irrigation today due to expected rain")
        
        if rain_tomorrow:
            analysis["weather_alerts"].append({
                "type": "rain",
                "message": "Rain expected tomorrow",
                "severity": "info"
            })
        
        # Check weekly rain accumulation
        if week_forecast:
            total_rain_week = sum(day.get("total_rain", 0) for day in week_forecast[:5])
            if total_rain_week > 50:  # mm
                analysis["weather_alerts"].append({
                    "type": "heavy_rain",
                    "message": f"Heavy rain expected this week: {total_rain_week:.1f}mm",
                    "severity": "warning"
                })
                analysis["care_tips"].append("Ensure proper drainage to prevent waterlogging")
    
    # Irrigation schedule analysis (safe even if weather data was missing)
    if last_irrigation:
        days_since_irrigation = (today - last_irrigation).days
        
        # Adjust based on weather (uses safe rain_today/rain_tomorrow defaults)
        if not rain_today and not rain_tomorrow:
            if days_since_irrigation >= 3:
                analysis["irrigation_needed"] = True
            elif days_since_irrigation >= 2 and current and current.get("temp_c", 25) > 30:
                analysis["irrigation_needed"] = True
    else:
        # No irrigation record
        if not rain_today:
            analysis["irrigation_needed"] = True
    
    # Fertilizer schedule analysis
    if last_fertilizer:
        days_since_fertilizer = (today - last_fertilizer).days
        if days_since_fertilizer >= 14:  # 2 weeks
            analysis["fertilizer_needed"] = True
    elif getattr(crop, 'is_sown', False) and getattr(crop, 'sown_date', None):
        # If sown but never fertilized
        days_since_sowing = (today - crop.sown_date).days
        if days_since_sowing >= 7:
            analysis["fertilizer_needed"] = True
    
    # Pesticide schedule analysis
    if last_pesticide:
        days_since_pesticide = (today - last_pesticide).days
        if days_since_pesticide >= 21:  # 3 weeks
            analysis["pesticide_check"] = True
    elif getattr(crop, 'pesticide', None) and getattr(crop, 'is_sown', False):
        analysis["pesticide_check"] = True
    
    # Sowing and harvesting reminders
    current_month = today.strftime("%B")
    
    if not getattr(crop, 'is_sown', False) and getattr(crop, 'sowing_months', None):
        if current_month in crop.sowing_months:
            analysis["sowing_reminder"] = True
    
    if getattr(crop, 'is_sown', False) and not getattr(crop, 'is_harvested', False) and getattr(crop, 'harvesting_months', None):
        if current_month in crop.harvesting_months:
            analysis["harvest_reminder"] = True
    
    return analysis

def generate_advisories_for_crop(crop):
    """
    Generate intelligent advisories based on weather and crop analysis
    """
    today = timezone.now().date()
    
    # Don't generate multiple advisories on the same day
    existing_today = Advisory.objects.filter(
        crop=crop,
        date=today
    ).exists()
    
    if existing_today:
        return []
    
    # Get weather forecast
    weather = get_weather_forecast(crop.user.district)
    
    # Analyze conditions
    analysis = analyze_crop_conditions(crop, weather)
    
    advisories = []
    
    # Priority 1: Weather alerts
    for alert in analysis["weather_alerts"]:
        if alert["severity"] == "warning":
            priority_emoji = "⚠️"
        else:
            priority_emoji = "ℹ️"
        
        message = f"{priority_emoji} {alert['message']}"
        
        if alert["type"] == "rain" and analysis.get("irrigation_needed"):
            message += f" - Skip irrigation for {crop.english_name or crop.name} today"
        elif alert["type"] == "high_temp":
            message += f" - Ensure adequate water for {crop.english_name or crop.name}"
        elif alert["type"] == "heavy_rain":
            message += f" - Check drainage around {crop.english_name or crop.name}"
        
        advisories.append(message)
    
    # Priority 2: Irrigation advice
    if analysis["irrigation_needed"] and not any("rain" in alert["type"] for alert in analysis["weather_alerts"]):
        advisories.append(
            f"💧 Irrigation recommended for {crop.english_name or crop.name}. "
            f"Suggested amount: {crop.irrigation_liters or 'as per crop requirement'}"
        )
    
    # Priority 3: Fertilizer advice
    if analysis["fertilizer_needed"]:
        fertilizer_type = crop.fertilizer or "balanced NPK fertilizer"
        advisories.append(
            f"🌱 Time to apply fertilizer to {crop.english_name or crop.name}. "
            f"Recommended: {fertilizer_type}"
        )
    
    # Priority 4: Pest control
    if analysis["pesticide_check"]:
        pesticide_info = crop.pesticide or "appropriate pesticide"
        advisories.append(
            f"🐛 Check {crop.english_name or crop.name} for pests. "
            f"If needed, apply: {pesticide_info}"
        )
    
    # Priority 5: Seasonal reminders
    if analysis["sowing_reminder"]:
        advisories.append(
            f"🌾 Perfect time to sow {crop.english_name or crop.name}! "
            f"This month ({today.strftime('%B')}) is ideal for sowing."
        )
    
    if analysis["harvest_reminder"]:
        if crop.sown_date:
            days_grown = (today - crop.sown_date).days
            advisories.append(
                f"🎯 {crop.english_name or crop.name} may be ready for harvest "
                f"(grown for {days_grown} days). Check maturity signs."
            )
        else:
            advisories.append(
                f"🎯 Check if {crop.english_name or crop.name} is ready for harvest."
            )
    
    # Priority 6: Care tips
    for tip in analysis["care_tips"][:2]:  # Limit to top 2 tips
        advisories.append(f"💡 {tip}")
    
    # Save advisories to database
    saved_advisories = []
    for message in advisories[:5]:  # Limit to 5 advisories per day
        advisory = Advisory.objects.create(
            crop=crop,
            message=message,
            date=today
        )
        saved_advisories.append(advisory)
    
    return saved_advisories

def get_weather_summary(district):
    """
    Get a simple weather summary for display
    """
    weather = get_weather_forecast(district)
    
    if not weather or not weather.get("current"):
        return {
            "status": "unavailable",
            "message": "Weather data unavailable"
        }
    
    current = weather["current"]
    
    return {
        "status": "available",
        "temperature": current.get("temp_c"),
        "description": current.get("description"),
        "humidity": current.get("humidity"),
        "has_rain": current.get("rain", False)
    }