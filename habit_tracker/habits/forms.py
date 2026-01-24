from django import forms
from .models import Habit

class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ['name', 'habit_type', 'target_count', 'target_time', 'frequency']  # total_time kaldırıldı

    def clean(self):
        cleaned_data = super().clean()
        habit_type = cleaned_data.get("habit_type")
        target_count = cleaned_data.get("target_count")
        target_time = cleaned_data.get("target_time")  # target_time kontrolü

        if habit_type == 'count':
            if target_count is None:
                self.add_error('target_count', 'Target count is required for count-based habits.')
        elif habit_type == 'time':
            if target_time is None:  # target_time kontrolü
                self.add_error('target_time', 'Target time is required for time-based habits.')