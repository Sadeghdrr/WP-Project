from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser

# Dynamic system roles model
# Includes: System Admin, Police Chief, Captain, Sergeant, Detective, Patrol Officer, Trainee, Forensic Doctor, Plaintiff, and Defendant
class Role(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Role Title")
    description = models.TextField(blank=True, null=True, verbose_name="Role Description")
    # hierarchy_level field specifies the user's power level in the police hierarchy (e.g., Police Chief = 10, Trainee = 1)
    hierarchy_level = models.PositiveSmallIntegerField(default=0, verbose_name="Hierarchy Level")

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ['-hierarchy_level']

    def __str__(self):
        return self.name


# Custom user model for the system (replaces Django's default User)
class User(AbstractUser):
    # Required fields based on documentation
    national_id = models.CharField(max_length=10, unique=True, verbose_name="National ID")
    phone_number = models.CharField(max_length=15, unique=True, verbose_name="Phone Number")
    email = models.EmailField(unique=True, verbose_name="Email")
    
    # User's role relationship (each user has one main role at a time)
    role = models.ForeignKey(
        Role, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users', 
        verbose_name="User Role"
    )

    # Fields prompted when creating a superuser in the terminal
    REQUIRED_FIELDS = ['email', 'national_id', 'phone_number']

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        role_name = self.role.name if self.role else "No Role"
        return f"{self.username} ({self.get_full_name()}) - {role_name}"
