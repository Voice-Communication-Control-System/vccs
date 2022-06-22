from django.db import models

class ControllerPositions(models.Model):
    name_of_position = models.CharField(max_length=20)
    radio_callsign = models.CharField(max_length=64)
    frequency = models.CharField(max_length=7)
    identifier = models.CharField(max_length=64)
    middle_letter = models.CharField(max_length=1)
    prefix = models.CharField(max_length=20)
    suffix = models.CharField(max_length=20)

    def __str__(self):
        return self.name_of_position

class BottomUp(models.Model):
    aerodrome = models.CharField(max_length=4)
    airspace_inheritance = models.CharField(max_length=256)

    def __str__(self):
        return self.aerodrome
