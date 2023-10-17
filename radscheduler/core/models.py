from datetime import date
from enum import IntEnum

from django.contrib.postgres.fields import ArrayField
from django.db import models

from radscheduler import roster
from radscheduler.users.models import User


class ISOWeekday(IntEnum):
    MON = 1
    TUE = 2
    WED = 3
    THUR = 4
    FRI = 5
    SAT = 6
    SUN = 7


class Registrar(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_number = models.CharField(max_length=20, blank=True, null=True)
    senior = models.BooleanField(default=False)
    start = models.DateField("start date", null=True, blank=True, help_text="Date started training")
    finish = models.DateField("finish date", null=True, blank=True, help_text="Date finished training")
    created = models.DateTimeField(auto_now_add=True)
    last_edited = models.DateTimeField(auto_now=True)

    def __repr__(self) -> str:
        return f"<Registrar: {self.user.username}>"

    def __str__(self) -> str:
        return self.user.username

    @property
    def year(self):
        if self.start is None:
            return None
        if date.today() > self.finish:
            return None
        return ((date.today() - self.start).days // 365) + 1


class Shift(models.Model):
    date = models.DateField("shift date")
    type = models.CharField("shift type", max_length=10, choices=roster.ShiftType.choices)
    registrar = models.ForeignKey(
        Registrar,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    stat_day = models.BooleanField(default=False)
    extra_duty = models.BooleanField(default=False)
    fatigue_override = models.FloatField(default=0.0)
    created = models.DateTimeField(auto_now_add=True)
    last_edited = models.DateTimeField(auto_now=True)

    def __repr__(self) -> str:
        if self.registrar:
            registrar = self.registrar.username
        else:
            registrar = "N/A"
        return f"<{roster.ShiftType(self.type).name} Shift {self.date} ({roster.Weekday(self.date.weekday()).name}): {registrar}>"

    class Meta:
        unique_together = ["date", "type", "registrar", "extra_duty"]


class Status(models.Model):
    """
    Given a date range, a registrar can be assigned a status.

    - Pre-oncall: 1st years
    - Reliever: no auto assignment, only manual rostering
    - Part time: do not work on some days
    - Pre-exam: 2 weeks before pathology, 6 months before viva
    - Buddy: 2nd years requiring a buddy when oncall
    """

    start = models.DateField("start date")
    end = models.DateField("end date")
    type = models.IntegerField(choices=roster.StatusType.choices)
    registrar = models.ForeignKey(Registrar, blank=False, null=False, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    last_edited = models.DateTimeField(auto_now=True)
    weekdays = ArrayField(
        models.IntegerField(choices=[(x.value, x.name) for x in ISOWeekday]),
        default=list,
        size=7,
    )
    shift_types = ArrayField(models.CharField(max_length=10, choices=roster.ShiftType.choices), default=list)

    def __repr__(self) -> str:
        return (
            f"<Status: {self.registrar.user.username} {self.start}--{self.end} ({roster.StatusType(self.type).label})>"
        )


class Leave(models.Model):
    date = models.DateField("date of leave")
    type = models.IntegerField(choices=roster.LeaveType.choices)
    portion = models.CharField(
        "portion of day",
        max_length=5,
        choices=[("ALL", "All day"), ("AM", "AM"), ("PM", "PM")],
        default="ALL",
    )
    approved = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    comment = models.TextField()

    registrar = models.ForeignKey(Registrar, blank=False, null=False, on_delete=models.CASCADE)
    form = models.ForeignKey("leave_application.LeaveForm", on_delete=models.PROTECT, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    last_edited = models.DateTimeField(auto_now=True)

    def __repr__(self) -> str:
        return f"<Leave: {self.registrar.username} {self.date} ({roster.LeaveType(self.type).name})>"

    class Meta:
        unique_together = ["date", "type", "registrar"]
