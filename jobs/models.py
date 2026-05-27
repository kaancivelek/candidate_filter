from django.db import models
from django.conf import settings

class Job(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='jobs'
    )
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=150)
    description = models.TextField()
    min_experience = models.PositiveIntegerField(default=0)
    education_level = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class JobSkill(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='required_skills')
    skill_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('job', 'skill_name')

    def __str__(self):
        return f"{self.skill_name} ({self.job.title})"