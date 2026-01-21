from django.db import models

class Device(models.Model):
    id = models.AutoField(primary_key=True)
    serial_id = models.CharField(max_length=255, unique=True, null=False)
    name = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True)
    user = models.ForeignKey('users.User' , on_delete=models.CASCADE, null=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        db_table = 'devices'
        indexes = [
            models.Index(fields=['user'], name='idx_devices_user_id'),
            models.Index(fields=['is_active'], name='idx_devices_is_active'),
        ]