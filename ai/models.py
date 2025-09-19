from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

# Create your models here.
# Add this to your core/models.py file

class ChatLog(models.Model):
    """
    Model to store AI chat interactions for analysis and improvement
    """
    LANGUAGE_CHOICES = [
        ('ml', 'Malayalam'),
        ('en', 'English'),
    ]
    
    CATEGORY_CHOICES = [
        ('GENERAL', 'General Query'),
        ('CROP_ADVICE', 'Crop Advice'),
        ('WEATHER', 'Weather Related'),
        ('PEST_CONTROL', 'Pest Control'),
        ('SOIL_HEALTH', 'Soil Health'),
        ('FERTILIZER', 'Fertilizer Advice'),
        ('IRRIGATION', 'Irrigation'),
        ('MARKET', 'Market Information'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_logs")
    session_id = models.CharField(max_length=100)  # To group conversations
    user_question = models.TextField()
    ai_response = models.TextField()
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='ml')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='GENERAL')
    
    # Context information
    user_district = models.CharField(max_length=50, blank=True, null=True)
    crops_mentioned = models.JSONField(default=list, blank=True)  # List of crop names mentioned
    
    # Feedback and rating
    user_rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-5 rating
    is_helpful = models.BooleanField(null=True, blank=True)
    user_feedback = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['session_id', '-created_at']),
            models.Index(fields=['category', '-created_at']),
        ]
    
    def _str_(self):
        return f"Chat by {self.user.name or self.user.mobile} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

# You can also add this helper model for storing common farming FAQs
class FarmingFAQ(models.Model):
    """
    Common farming questions and answers for quick responses
    """
    LANGUAGE_CHOICES = [
        ('ml', 'Malayalam'),
        ('en', 'English'),
        ('both', 'Both Languages'),
    ]
    
    question_ml = models.TextField(help_text="Question in Malayalam")
    question_en = models.TextField(help_text="Question in English", blank=True)
    answer_ml = models.TextField(help_text="Answer in Malayalam")
    answer_en = models.TextField(help_text="Answer in English", blank=True)
    
    category = models.CharField(max_length=50)
    keywords = models.JSONField(default=list, help_text="Keywords for matching queries")
    
    # Targeting
    applicable_districts = models.JSONField(default=list, blank=True)
    applicable_seasons = models.JSONField(default=list, blank=True)
    applicable_crops = models.JSONField(default=list, blank=True)
    
    is_active = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(default=1)  # Higher number = higher priority
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = "Farming FAQ"
        verbose_name_plural = "Farming FAQs"
    
    def _str_(self):
        return f"FAQ: {self.question_ml[:50]}..."