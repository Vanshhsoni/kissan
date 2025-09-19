# ai/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
import json
from core.models import Crop, ActivityLog, Advisory
from accounts.models import User

@login_required
def ai_page(request):
    """
    Main AI chatbot page with user context
    """
    user = request.user
    
    # Get user's crops with recent activity
    user_crops = user.crops.all().select_related().prefetch_related('activity_logs')
    
    # Get recent activity logs (last 10 days)
    recent_activities = ActivityLog.objects.filter(
        crop__user=user,
        date__gte=timezone.now().date() - timedelta(days=10)
    ).select_related('crop').order_by('-date')[:20]
    
    # Get pending advisories
    pending_advisories = Advisory.objects.filter(
        crop__user=user,
        is_acknowledged=False
    ).select_related('crop').order_by('-date')[:5]
    
    context = {
        'user_crops': user_crops,
        'recent_activities': recent_activities,
        'pending_advisories': pending_advisories,
        'total_crops': user_crops.count(),
        'sown_crops': user_crops.filter(is_sown=True, is_harvested=False).count(),
        'harvested_crops': user_crops.filter(is_harvested=True).count(),
    }
    
    return render(request, "ai/ai.html", context)

@login_required
@csrf_exempt
def get_user_context(request):
    """
    API endpoint to get user context for AI
    """
    if request.method == 'GET':
        user = request.user
        
        # Build comprehensive user profile
        user_profile = {
            'name': user.name or 'Farmer',
            'district': dict(user.DISTRICTS).get(user.district, user.district) if user.district else 'Kerala',
            'acreage': dict(user.ACREAGE_CHOICES).get(user.acreage, user.acreage) if user.acreage else 'Not specified',
            'soil_type': dict(user.SOIL_TYPES).get(user.soil_type, user.soil_type) if user.soil_type else 'Mixed',
            'pincode': user.pincode or '',
        }
        
        # Get crops information
        crops_data = []
        for crop in user.crops.all():
            crop_info = {
                'name': crop.name,
                'english_name': crop.english_name or '',
                'is_sown': crop.is_sown,
                'is_harvested': crop.is_harvested,
                'sown_date': crop.sown_date.strftime('%Y-%m-%d') if crop.sown_date else '',
                'harvested_date': crop.harvested_date.strftime('%Y-%m-%d') if crop.harvested_date else '',
                'fertilizer': crop.fertilizer or '',
                'pesticide': crop.pesticide or '',
                'irrigation_liters': crop.irrigation_liters or '',
                'sunlight_hours': crop.sunlight_hours or '',
                'notes': crop.notes or ''
            }
            crops_data.append(crop_info)
        
        # Get recent activities
        recent_activities = []
        activities = ActivityLog.objects.filter(
            crop__user=user,
            date__gte=timezone.now().date() - timedelta(days=15)
        ).select_related('crop').order_by('-date')[:20]
        
        for activity in activities:
            activity_info = {
                'crop_name': activity.crop.name,
                'date': activity.date.strftime('%Y-%m-%d'),
                'did_irrigate': activity.did_irrigate,
                'did_fertilize': activity.did_fertilize,
                'did_apply_pesticide': activity.did_apply_pesticide,
                'notes': activity.notes or ''
            }
            recent_activities.append(activity_info)
        
        # Get pending advisories
        advisories_data = []
        advisories = Advisory.objects.filter(
            crop__user=user,
            is_acknowledged=False
        ).select_related('crop').order_by('-date')[:5]
        
        for advisory in advisories:
            advisory_info = {
                'crop_name': advisory.crop.name,
                'message': advisory.message,
                'category': advisory.category,
                'date': advisory.date.strftime('%Y-%m-%d')
            }
            advisories_data.append(advisory_info)
        
        # Get weather context (you might want to integrate with a weather API)
        current_season = get_current_season()
        
        response_data = {
            'profile': user_profile,
            'crops': crops_data,
            'recent_activities': recent_activities,
            'pending_advisories': advisories_data,
            'season': current_season,
            'location': {
                'district': user_profile['district'],
                'pincode': user_profile['pincode']
            }
        }
        
        return JsonResponse(response_data)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def get_current_season():
    """
    Determine current agricultural season in Kerala
    """
    current_month = timezone.now().month
    
    if current_month in [6, 7, 8, 9]:  # June to September
        return "Kharif (വർഷാക്കാലം)"
    elif current_month in [10, 11, 12, 1]:  # October to January
        return "Rabi (ശീതകാലം)"
    else:  # February to May
        return "Summer (വേനൽക്കാലം)"

@login_required
@csrf_exempt
def save_chat_interaction(request):
    """
    Save important chat interactions for future reference
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_question = data.get('question', '')
            ai_response = data.get('response', '')
            language = data.get('language', 'ml')
            category = data.get('category', 'general')  # general, advice, weather, etc.
            
            # You might want to create a ChatLog model to store these
            # For now, we'll log them or store in session
            
            # Store in session for quick access
            if 'recent_chats' not in request.session:
                request.session['recent_chats'] = []
            
            chat_entry = {
                'question': user_question,
                'response': ai_response,
                'language': language,
                'category': category,
                'timestamp': timezone.now().isoformat()
            }
            
            request.session['recent_chats'].insert(0, chat_entry)
            request.session['recent_chats'] = request.session['recent_chats'][:50]  # Keep last 50
            request.session.modified = True
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def get_farming_tips(request):
    """
    Get contextual farming tips based on user's profile and current season
    """
    user = request.user
    current_season = get_current_season()
    
    # Generate tips based on user's crops and activities
    tips = []
    
    # Season-specific tips
    if "വർഷാക്കാലം" in current_season:  # Monsoon
        tips.extend([
            "മഴക്കാലത്ത് ഡ്രെയിനേജ് ശരിയായി ക്രമീകരിക്കുക",
            "ഫംഗൽ അണുബാധയ്ക്കെതിരെ ജാഗ്രത പാലിക്കുക",
            "വെള്ളം കേടുപാടുകൾക്കെതിരെ വിളകൾ സംരക്ഷിക്കുക"
        ])
    elif "ശീതകാലം" in current_season:  # Winter
        tips.extend([
            "ശീതകാല വിളകൾക്കുള്ള തയ്യാറെടുപ്പുകൾ നടത്തുക",
            "മണ്ണിന്റെ ഈർപ്പം നിലനിർത്തുക",
            "കീടങ്ങളുടെ ആക്രമണത്തിൽ നിന്ന് സംരക്ഷിക്കുക"
        ])
    
    # Crop-specific tips
    for crop in user.crops.filter(is_sown=True, is_harvested=False):
        if crop.name:
            tips.append(f"{crop.name} വിളയ്ക്കുള്ള പരിചരണം തുടരുക")
    
    return JsonResponse({'tips': tips[:10]})  # Return max 10 tips

# You might also want to add these utility functions

def get_weather_advice(district, pincode=None):
    """
    Get weather-based farming advice (integrate with weather API)
    """
    # This would integrate with a weather service
    # For now, return generic advice
    return {
        'temperature': 'moderate',
        'humidity': 'high',
        'rainfall': 'expected',
        'advice': 'Good weather for most crops. Monitor for excess moisture.'
    }

def get_crop_recommendations(user_profile, season):
    """
    Recommend crops based on user profile and season
    """
    recommendations = []
    
    if user_profile.get('district') in ['കോഴിക്കോട്', 'കണ്ണൂർ', 'വയനാട്']:
        # Northern Kerala recommendations
        if "വർഷാക്കാലം" in season:
            recommendations.extend(['നെൽ', 'കവുങ്ങ്', 'കുരുമുളക്'])
    
    # Add more region and season-specific recommendations
    
    return recommendations