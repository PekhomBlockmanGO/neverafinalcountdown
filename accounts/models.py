from django.db import models


class EmergencyContact(models.Model):
    """
    Singleton-like model — only one row is needed.
    Use EmergencyContact.get_solo() to always retrieve or create it safely.
    """
    phone_number = models.CharField(max_length=15)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Emergency Contact"
        verbose_name_plural = "Emergency Contacts"

    def __str__(self):
        return self.phone_number

    @classmethod
    def get_solo(cls):
        """Return the single emergency contact, creating a blank one if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
