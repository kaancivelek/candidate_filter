from django.db import models
from cvs.models import CV
from jobs.models import Job

class MatchResult(models.Model):
    cv = models.OneToOneField(CV, on_delete=models.CASCADE, related_name='match_result')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='match_results')
    
    overall_score = models.FloatField(default=0.0)
    skills_score = models.FloatField(default=0.0)
    experience_score = models.FloatField(default=0.0)
    education_score = models.FloatField(default=0.0)
    
    ai_summary = models.TextField(blank=True, null=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Match {self.overall_score}% - CV {self.cv.id} to Job {self.job.id}"