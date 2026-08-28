from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    class Role(models.TextChoices):
        DEVELOPER = "DEVELOPER", "Developer"
        OWNER = "OWNER", "Owner"
        MANAGER = "MANAGER", "Manager"
        CREW = "CREW", "Crew"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CREW)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def is_super_role(self):
        return self.role in {self.Role.DEVELOPER, self.Role.OWNER}

    @property
    def is_management(self):
        return self.role in {
            self.Role.DEVELOPER,
            self.Role.OWNER,
            self.Role.MANAGER,
        }