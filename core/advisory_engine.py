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
    The FIXED core analysis function.
    Decides what actions are needed based on logs and weather.
    Now properly handles unsown crops and prevents illogical advisories.
    """
    today = timezone.now().date()
    advisories = []

    # --- CRITICAL FIX: Check if crop is actually sown ---
    if not crop.is_sown or not crop.sown_date:
        # For unsown crops, only provide sowing-related advice
        current_month = today.strftime("%B")
        if crop.sowing_months and current_month in crop.sowing_months:
            advisories.append({
                "message": f"Perfect timing! {current_month} is ideal for sowing {crop.name}. Prepare your field and sow soon.",
                "category": "URGENT"
            })
        else:
            advisories.append({
                "message": f"Your {crop.name} is ready to be sown. Check optimal sowing months: {', '.join(crop.sowing_months) if crop.sowing_months else 'Not specified'}.",
                "category": "TIP"
            })
        
        # Add preparation tips for unsown crops
        advisories.append({
            "message": f"Prepare your field with proper soil preparation and ensure good drainage before sowing {crop.name}.",
            "category": "TIP"
        })
        
        return advisories  # Return early for unsown crops

    # --- Get Recent Activity (Only for sown crops) ---
    last_irrigation_log = ActivityLog.objects.filter(crop=crop, did_irrigate=True).order_by('-date').first()
    last_fertilizer_log = ActivityLog.objects.filter(crop=crop, did_fertilize=True).order_by('-date').first()
    last_pesticide_log = ActivityLog.objects.filter(crop=crop, did_apply_pesticide=True).order_by('-date').first()

    # Calculate days since last activities (with proper defaults)
    days_since_irrigation = (today - last_irrigation_log.date).days if last_irrigation_log else 0
    days_since_fertilizer = (today - last_fertilizer_log.date).days if last_fertilizer_log else 0
    days_since_pesticide = (today - last_pesticide_log.date).days if last_pesticide_log else 0
    
    # Calculate crop age (guaranteed to be valid since crop is sown)
    crop_age = (today - crop.sown_date).days

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
                    "message": f"High temperature warning ({today_weather['max_temp']}°C). Ensure your {crop.name} has adequate water and consider providing shade if possible.",
                    "category": "URGENT"
                })
            if today_weather['avg_humidity'] > 85:
                high_humidity_alert = True
        
        # Check for rain in the next 2 days
        rain_in_next_2_days = any(d['will_rain'] for d in weather_forecast[:3])

    # --- Rule-Based Advisory Generation (For Sown Crops Only) ---

    # 1. Irrigation Logic (Smart logic based on crop age and conditions)
    if crop_age <= 2:
        # Very young crops need more frequent watering
        if days_since_irrigation >= 2:
            advisories.append({
                "message": f"Young {crop.name} (Day {crop_age}) needs regular watering. Water gently to avoid disturbing roots.",
                "category": "URGENT"
            })
    elif crop_age <= 30:
        # Established seedlings 
        if rain_in_next_2_days and days_since_irrigation <= 2:
            advisories.append({
                "message": "Rain is expected in the next 2 days. You can skip irrigation today and let nature water your crop.",
                "category": "TIP"
            })
        elif days_since_irrigation >= 3 or (days_since_irrigation >= 2 and high_temp_alert):
            advisories.append({
                "message": f"It's been {days_since_irrigation} days since irrigation. Your {crop.name} needs watering.",
                "category": "ROUTINE"
            })
    else:
        # Mature crops - less frequent watering needed
        if rain_in_next_2_days and days_since_irrigation <= 3:
            advisories.append({
                "message": "Rain expected soon. Your mature crop can wait for natural irrigation.",
                "category": "TIP"
            })
        elif days_since_irrigation >= 4 or (days_since_irrigation >= 3 and high_temp_alert):
            advisories.append({
                "message": f"It's been {days_since_irrigation} days since irrigation. Time to water your {crop.name}.",
                "category": "ROUTINE"
            })
    
    # 2. Fertilizer Logic (Age-based and sensible timing)
    if crop_age >= 7 and crop_age < 15 and days_since_fertilizer >= 7:
        advisories.append({
            "message": f"Your {crop.name} is {crop_age} days old. First fertilizer application is due. Use a balanced starter fertilizer.",
            "category": "ROUTINE"
        })
    elif crop_age >= 15 and crop_age < 25 and days_since_fertilizer >= 15:
        advisories.append({
            "message": f"Second fertilizer application recommended. Your {crop.name} is in active growth phase. Consider: {crop.fertilizer or 'balanced NPK fertilizer'}.",
            "category": "ROUTINE"
        })
    elif crop_age >= 25 and days_since_fertilizer >= 20:
        advisories.append({
            "message": f"Regular fertilizer application due ({days_since_fertilizer} days since last). Use: {crop.fertilizer or 'appropriate fertilizer for your crop stage'}.",
            "category": "ROUTINE"
        })

    # 3. Pesticide/Disease Management Logic
    if high_humidity_alert and days_since_pesticide >= 7:
        advisories.append({
            "message": f"High humidity ({today_weather['avg_humidity']:.0f}%) increases disease risk. Inspect your {crop.name} for fungal issues and consider preventive treatment.",
            "category": "URGENT"
        })
    elif crop_age >= 14 and days_since_pesticide >= 21:
        advisories.append({
            "message": f"Regular pest inspection due. It's been {days_since_pesticide} days. Check for common {crop.name} pests. Apply {crop.pesticide or 'appropriate pesticide'} if needed.",
            "category": "ROUTINE"
        })
    elif crop_age >= 7 and days_since_pesticide >= 14 and high_temp_alert:
        advisories.append({
            "message": f"Hot weather can increase pest activity. Monitor your {crop.name} closely for signs of pest damage.",
            "category": "TIP"
        })

    # 4. Harvesting Reminders (Only for mature crops)
    current_month = today.strftime("%B")
    if not crop.is_harvested and crop.harvesting_months and current_month in crop.harvesting_months:
        if crop_age >= 60:  # Only suggest harvest for mature crops
            advisories.append({
                "message": f"Your {crop.name} (Day {crop_age}) might be ready for harvest! Check for maturity signs and harvest at optimal time.",
                "category": "URGENT"
            })
        else:
            advisories.append({
                "message": f"Harvest season for {crop.name} is approaching. Monitor your crop closely for signs of maturity.",
                "category": "TIP"
            })
    
    # 5. Growth Stage Specific Tips
    if crop_age <= 7:
        advisories.append({
            "message": f"Critical establishment phase! Keep soil consistently moist and protect young {crop.name} from extreme weather.",
            "category": "TIP"
        })
    elif 8 <= crop_age <= 30:
        advisories.append({
            "message": f"Active growth phase for your {crop.name}. Ensure adequate nutrition and regular monitoring for optimal development.",
            "category": "TIP"
        })
    elif crop_age > 60 and not crop.is_harvested:
        advisories.append({
            "message": f"Your {crop.name} is mature (Day {crop_age}). Monitor closely for harvest readiness and maintain proper care until harvest.",
            "category": "TIP"
        })

    # --- Fallback for very few advisories ---
    if len(advisories) < 2:
        advisories.append({
            "message": f"Your {crop.name} is looking good on Day {crop_age}! Continue regular monitoring and maintain consistent care routines.",
            "category": "TIP"
        })
        
        if crop.sunlight_hours:
            advisories.append({
                "message": f"Ensure your {crop.name} gets adequate sunlight ({crop.sunlight_hours} hours daily) for healthy growth.",
                "category": "TIP"
            })

    return advisories


def generate_advisories_for_crop(crop: Crop):
    """
    Public function to trigger the advisory generation for a single crop.
    This will delete old advisories and create new ones for today.
    FIXED: Better cleanup logic and error handling.
    """
    today = timezone.now().date()
    
    # Clean up old advisories (keep last 7 days, remove older ones)
    one_week_ago = today - timedelta(days=7)
    deleted_count = Advisory.objects.filter(crop=crop, date__lt=one_week_ago).delete()[0]
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old advisories for crop {crop.id}")
    
    # Clean up today's advisories to avoid duplicates
    Advisory.objects.filter(crop=crop, date=today).delete()
    
    # Fetch fresh weather data
    weather_forecast = get_weather_forecast(crop.user.district)
    if not weather_forecast:
        logger.warning(f"Could not fetch weather data for {crop.user.district}. Using fallback logic.")
    
    # Get a list of advisory messages and categories
    try:
        advisory_data = analyze_crop_and_weather(crop, weather_forecast)
    except Exception as e:
        logger.error(f"Error analyzing crop {crop.id}: {e}")
        # Fallback advisory
        advisory_data = [{
            "message": f"Unable to generate specific advice right now. Please check your {crop.name} manually and ensure basic care is provided.",
            "category": "TIP"
        }]
    
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


def cleanup_old_advisories():
    """
    Utility function to clean up old advisories across all crops.
    Call this daily via a management command or cron job.
    """
    one_week_ago = timezone.now().date() - timedelta(days=7)
    deleted_count = Advisory.objects.filter(date__lt=one_week_ago).delete()[0]
    logger.info(f"Cleaned up {deleted_count} old advisories from database")
    return deleted_count


def get_weather_summary(district: str):
    """
    Simplified weather summary for the AJAX endpoint.
    Enhanced with better error handling.
    """
    forecast = get_weather_forecast(district)
    if not forecast or len(forecast) == 0:
        return {
            "status": "unavailable", 
            "message": "Weather data could not be fetched. Please check your internet connection."
        }
    
    current_day = forecast[0]
    
    # Check if we have today's data
    if current_day['date'] != timezone.now().date():
        return {
            "status": "unavailable", 
            "message": "Current weather data is not available."
        }
    
    return {
        "status": "available",
        "temperature": current_day['max_temp'],
        "description": f"Max {current_day['max_temp']}°C, Min {current_day['min_temp']}°C",
        "humidity": round(current_day['avg_humidity']),
        "has_rain": current_day['will_rain'],
        "rain_amount": current_day.get('total_rain', 0)
    }


def mark_all_advisories_read_for_crop(crop_id: int, user):
    """
    Mark all unread advisories for a specific crop as read.
    """
    try:
        updated_count = Advisory.objects.filter(
            crop_id=crop_id,
            crop__user=user,
            is_acknowledged=False
        ).update(is_acknowledged=True)
        
        logger.info(f"Marked {updated_count} advisories as read for crop {crop_id}")
        return updated_count
    except Exception as e:
        logger.error(f"Error marking advisories as read for crop {crop_id}: {e}")
        return 0


def get_advisory_stats_for_user(user):
    """
    Get advisory statistics for a user.
    """
    active_crops = user.crops.filter(is_harvested=False)
    
    # Get advisories from last 7 days
    week_ago = timezone.now().date() - timedelta(days=7)
    recent_advisories = Advisory.objects.filter(
        crop__user=user,
        crop__is_harvested=False,
        date__gte=week_ago
    )
    
    stats = {
        "active_crops": active_crops.count(),
        "total_advisories": recent_advisories.count(),
        "urgent_count": recent_advisories.filter(category="URGENT").count(),
        "unread_total": recent_advisories.filter(is_acknowledged=False).count(),
        "routine_count": recent_advisories.filter(category="ROUTINE").count(),
        "tips_count": recent_advisories.filter(category="TIP").count(),
    }
    
    return stats