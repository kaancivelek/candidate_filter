from django.db import models
from jobs.models import Job

class Candidate(models.Model):
    full_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or "Unknown Candidate"


class CV(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='cvs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='received_cvs')
    file_path = models.FileField(upload_to='resumes/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CV_{self.id} - {self.candidate.full_name or 'Unknown'}"