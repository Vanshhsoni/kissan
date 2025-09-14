from django.db import models
from django.utils import timezone
from accounts.models import User

class Crop(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crops")
    name = models.CharField(max_length=100)  # Malayalam name
    english_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Details from CSV
    image_url = models.URLField(blank=True, null=True)
    fertilizer = models.CharField(max_length=200, blank=True, null=True)
    pesticide = models.CharField(max_length=200, blank=True, null=True)
    irrigation_liters = models.CharField(max_length=50, blank=True, null=True)
    sunlight_hours = models.CharField(max_length=50, blank=True, null=True)
    sowing_months = models.CharField(max_length=200, blank=True, null=True)
    harvesting_months = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Timeline
    sown_date = models.DateField(blank=True, null=True)
    harvested_date = models.DateField(blank=True, null=True)

    # Status
    is_sown = models.BooleanField(default=False)
    is_harvested = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.english_name or ''}) - {self.user.name or self.user.mobile}"

# **RECOMMENDED NEW MODEL**
# This model represents a single day's log for a crop.
class ActivityLog(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="activity_logs")
    date = models.DateField(default=timezone.now)

    # Boolean fields that map directly to your UI toggles
    did_irrigate = models.BooleanField(default=False)
    did_fertilize = models.BooleanField(default=False)
    did_apply_pesticide = models.BooleanField(default=False)
    
    notes = models.TextField(blank=True, null=True)  # For any extra notes for the day

    class Meta:
        # This is very important: it ensures you can only have ONE log entry per crop per day.
        unique_together = ('crop', 'date')
        ordering = ['-date'] # Show the most recent logs first

    def __str__(self):
        return f"Log for {self.crop.name} on {self.date}"

# This model is for sending advice TO the farmer. It's separate from the daily logs.
class Advisory(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="advisories")
    message = models.TextField()  # e.g. "Rain expected, avoid irrigation"
    date = models.DateField(auto_now_add=True)
    is_acknowledged = models.BooleanField(default=False)

    def __str__(self):
        return f"Advisory for {self.crop.name} on {self.date}"