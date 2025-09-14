# <-- FIX: All imports are consolidated at the top for clarity. -->
import csv
import os
import calendar
from datetime import date
import pandas as pd
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.conf import settings
from django.utils import timezone
from django.contrib import messages

from .models import Crop, ActivityLog


import csv
import os
from datetime import date, timedelta
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def get_weather_icon(forecast):
    """Returns an SVG icon string based on the weather forecast."""
    icons = {
        'Sunny': """<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-full h-full text-yellow-500"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" /></svg>""",
        'Rainy': """<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-full h-full text-blue-500"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" /></svg>""",
        'Cloudy': """<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-full h-full text-gray-500"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-2.086-5.432A4.5 4.5 0 006.75 7.5 4.5 4.5 0 002.25 15z" /></svg>""",
        'Thunderstorm': """<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-full h-full text-indigo-600"><path stroke-linecap="round" stroke-linejoin="round" d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.43 2.43a4.5 4.5 0 00-.586 7.756 4.5 4.5 0 00.723 7.756h9.243a4.5 4.5 0 00.723-7.756 2.25 2.25 0 01-2.43-2.43a3 3 0 00-5.78-1.128zM15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" /></svg>""",
        'Overcast': """<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-full h-full text-slate-600"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-2.086-5.432A4.5 4.5 0 006.75 7.5 4.5 4.5 0 002.25 15z M8.25 15a3.75 3.75 0 117.5 0 3.75 3.75 0 01-7.5 0z" /></svg>""",
    }
    # Return the specific icon or the 'Cloudy' icon as a default
    return icons.get(forecast, icons['Cloudy'])

@login_required
def dashboard(request):
    """
    Renders the main dashboard. Weather data is now fetched client-side.
    """
    # --- Crop Data Logic (from your original code) ---
    csv_path_crops = os.path.join(settings.BASE_DIR, "database", "kerala_crops_dataset.csv")
    crops_data = []
    try:
        with open(csv_path_crops, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                clean_row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items()}
                crops_data.append(clean_row)
    except FileNotFoundError:
        print("Crops CSV file not found, crop selection modal will be empty.")

    # --- Context for Template ---
    user_crops_sorted = request.user.crops.order_by('-id')
    
    context = {
        "crops": crops_data,
        "user_crops": user_crops_sorted,
        # We pass the user's district directly to the template for JavaScript to use
        "user_district": request.user.district, 
    }
    return render(request, "core/dashboard.html", context)
@login_required
def add_crop(request):
    if request.method == "POST":
        malayalam = request.POST.get("malayalam", "")
        english = request.POST.get("english", "")
        
        if Crop.objects.filter(user=request.user, name=malayalam, is_harvested=False).exists():
            messages.error(request, f"An active crop named '{malayalam}' is already in your list.")
            return redirect("dashboard")

        irrigation_liters = request.POST.get("irrigation_liters", "")
        image_url = request.POST.get("image_url", "")
        fertilizer = request.POST.get("fertilizer", "")
        pesticide = request.POST.get("pesticide", "")
        sunlight_hours = request.POST.get("sunlight_hours", "")
        sowing_months = request.POST.get("sowing_months", "")
        harvesting_months = request.POST.get("harvesting_months", "")  # ✅ fixed here
        notes = request.POST.get("notes", "")

        Crop.objects.create(
            user=request.user,
            name=malayalam,
            english_name=english,
            image_url=image_url,
            fertilizer=fertilizer,
            pesticide=pesticide,
            irrigation_liters=irrigation_liters,
            sunlight_hours=sunlight_hours,
            sowing_months=sowing_months,
            harvesting_months=harvesting_months,
            notes=notes,
        )
        
        messages.success(request, f"Successfully added a new cycle for '{malayalam}'!")
    
    return redirect("dashboard")


# <-- FIX: This is the main, consolidated view for the crop detail page. -->
@login_required
def crop_activity_log(request, crop_id):
    crop = get_object_or_404(Crop, id=crop_id, user=request.user)
    today = timezone.now().date()

    # --- Handle Form Submissions (POST requests) ---
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "sow":
            crop.is_sown = True
            crop.sown_date = today
            crop.save()
        
        elif action == "harvest":
            crop.is_harvested = True
            crop.harvested_date = today
            crop.save()

        elif action == "save_daily_log":
            did_irrigate = request.POST.get('did_irrigate') == 'on'
            did_fertilize = request.POST.get('did_fertilize') == 'on'
            did_apply_pesticide = request.POST.get('did_apply_pesticide') == 'on'
            # <-- BUG FIX: The 'notes' field was missing here and is now included. -->
            notes = request.POST.get('notes', '')

            ActivityLog.objects.update_or_create(
                crop=crop,
                date=today,
                defaults={
                    'did_irrigate': did_irrigate,
                    'did_fertilize': did_fertilize,
                    'did_apply_pesticide': did_apply_pesticide,
                    'notes': notes  # <-- BUG FIX: Added notes to the saved data.
                }
            )
        
        # After any POST action, redirect back to the same page to prevent re-submission.
        return redirect("crop_activity_log", crop_id=crop.id)

    # --- Prepare Data for Display (GET request) ---
    
    # Get today's log to pre-fill the form toggles.
    todays_log = ActivityLog.objects.filter(crop=crop, date=today).first()

    # <-- MERGED: The calendar processing logic is now part of this view. -->
    
    # 1. Fetch all logs for this crop once.
    all_logs = ActivityLog.objects.filter(crop=crop)

    # 2. Create a dictionary to easily look up events by date.
    events_by_date = {}
    for log in all_logs:
        log_date_str = log.date.strftime("%Y-%m-%d")
        if log_date_str not in events_by_date:
            events_by_date[log_date_str] = []
        
        if log.did_irrigate: events_by_date[log_date_str].append('irrigate')
        if log.did_fertilize: events_by_date[log_date_str].append('fertilize')
        if log.did_apply_pesticide: events_by_date[log_date_str].append('pesticide')

    # Add the special 'sown' and 'harvest' events from the Crop model.
    if crop.is_sown and crop.sown_date:
        sown_date_str = crop.sown_date.strftime("%Y-%m-%d")
        if sown_date_str not in events_by_date: events_by_date[sown_date_str] = []
        events_by_date[sown_date_str].append('sown')

    if crop.is_harvested and crop.harvested_date:
        harvest_date_str = crop.harvested_date.strftime("%Y-%m-%d")
        if harvest_date_str not in events_by_date: events_by_date[harvest_date_str] = []
        events_by_date[harvest_date_str].append('harvest')
    
    # 3. Build the final calendar structure for the template.
    calendar_data = []
    cal = calendar.Calendar()
    # Use the year from the sown date if available, otherwise use the current year.
    year_to_display = crop.sown_date.year if crop.sown_date else today.year

    for month_num in range(1, 13):
        month_name = calendar.month_name[month_num]
        month_weeks = []
        
        for week in cal.monthdayscalendar(year_to_display, month_num):
            week_days = []
            for day_num in week:
                if day_num == 0:
                    week_days.append({"day": None, "events": []})
                else:
                    day_date_str = f"{year_to_display}-{month_num:02d}-{day_num:02d}"
                    week_days.append({
                        "day": day_num,
                        "events": events_by_date.get(day_date_str, [])
                    })
            month_weeks.append(week_days)
        
        calendar_data.append({
            "year": year_to_display,
            "month_name": month_name,
            "weeks": month_weeks
        })

    context = {
        "crop": crop,
        "todays_log": todays_log,
        "calendar_data": calendar_data, # <-- Pass the new calendar data to the template.
    }
    # Note: "past_logs" is no longer needed as this data is in the calendar.
    return render(request, "logs/activity.html", context)


@login_required
def ai_page(request):
    return render(request, "core/ai.html")


def logout_view(request):
    logout(request)
    return redirect("landing")

@login_required
def profile_page(request):
    return render(request,"core/profile.html", {"user": request.user})

@login_required
def prices_page(request):
    # Path to your CSV file
    csv_path = os.path.join(settings.BASE_DIR, "database", "district_crop_prices.csv")

    # Read the CSV into a DataFrame
    df = pd.read_csv(csv_path)

    # Get the logged-in user's district
    user_district = request.user.district

    # Filter rows for that district
    df_filtered = df[df["district"] == user_district]

    # Convert DataFrame to list of dicts for template
    items = df_filtered.to_dict(orient="records")

    return render(request, "core/prices.html", {"items": items, "district": user_district})