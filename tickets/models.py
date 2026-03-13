from django.db import models
from masters.models import Site, Area, Location, SpecificArea 

class Ticket(models.Model):
    CATEGORY_CHOICES = [
    ('HVAC', 'HVAC'),
    ('Electrical', 'Electrical'),
    ('Plumbing', 'Plumbing'),
    ('Housekeeping', 'Housekeeping'),
    ('Carpentry', 'Carpentry'),
    ('STP/WTP', 'STP/WTP'),
    ('Safety', 'Safety'),
    ('Security', 'Security'),
    ('Parking', 'Parking'),
    ('Other', 'Other'),
]

    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]

    # 🌟 Friend's expanded status choices
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Attended', 'Attended'),
        ('In Progress', 'In Progress'),
        ('Delayed', 'Delayed'),
        ('Closed', 'Closed'),
    ]

    SOURCE_CHOICES = [
        ('QR', 'QR Code'),
        ('Manual', 'Manual Entry'),
    ]

    # 🌟 OUR PERFECT 4-LAYER LOGIC
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, null=True, blank=True) # Building
    location = models.ForeignKey(Location, on_delete=models.CASCADE) # Floor
    specific_area = models.ForeignKey(SpecificArea, on_delete=models.SET_NULL, blank=True, null=True) # Area

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    description = models.TextField()

    reporter_name = models.CharField(max_length=100, blank=True, null=True)
    reporter_phone = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to='complaint_photos/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    
    # 🌟 Friend's new remarks field for the "Why?" button
    remarks = models.TextField(blank=True, null=True, help_text="Reason for delay")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='QR')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # 🌟 Friend's new tracker

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket #{self.id} | {self.location.name} | {self.status}"


# 🌟 NEW CLASS ALIGNED TO THE LEFT 🌟
class TicketLog(models.Model):
    # 🌟 This links the log directly to the specific ticket!
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20)
    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp'] # Shows newest logs at the top

    def __str__(self):
        return f"Ticket #{self.ticket.id} -> {self.status}"