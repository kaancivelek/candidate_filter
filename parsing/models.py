from django.db import models
from cvs.models import CV, Candidate

class ParsedData(models.Model):
    cv = models.OneToOneField(CV, on_delete=models.CASCADE, related_name='parsed_data')
    raw_text = models.TextField(blank=True, null=True)
    gpa = models.CharField(max_length=50, blank=True, null=True)
    degree = models.CharField(max_length=255, blank=True, null=True)
    
    # JSONFields to store python lists directly from the parser script
    universities = models.JSONField(default=list, blank=True)
    workplaces = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    
    parsed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ParsedData for CV {self.cv.id}"


class CandidateSkill(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='skills')
    skill_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('candidate', 'skill_name')

    def __str__(self):
        return f"{self.skill_name} - {self.candidate.full_name}"