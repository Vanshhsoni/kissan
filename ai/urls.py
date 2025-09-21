# ai/urls.py
from django.urls import path
from . import views

app_name = "ai"

urlpatterns = [
    # Main AI chatbot page
    path("", views.ai_page, name="ai_page"),
    path("chat/", views.ai_page, name="chat_page"),
    
    # API endpoints for AI functionality
    path("api/user-context/", views.get_user_context, name="user_context"),
    path("api/farming-tips/", views.get_farming_tips, name="farming_tips"),
    
    # Chat interaction endpoints
    path("save_chat/", views.save_chat_interaction, name="save_chat_interaction"),
    path("api/save-chat/", views.save_chat_interaction, name="save_chat"),  # Alternative endpoint
    
    # Chat history endpoints
    path("history/", views.get_chat_history, name="get_chat_history"),
    path("history/<str:session_id>/", views.get_chat_session, name="get_chat_session"),
    
    # Debug endpoint (remove in production)
    path("debug/logs/", views.debug_chat_logs, name="debug_logs"),
]