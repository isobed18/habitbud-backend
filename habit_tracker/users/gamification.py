import math

class GamificationEngine:
    """
    Central logic for XP, Leveling, and Streak Multipliers.
    Inspired by Snapchat and RPG progression systems.
    """
    
    BASE_XP = 10
    MAX_MULTIPLIER = 3.0
    
    @staticmethod
    def calculate_level(total_xp):
        """
        Non-linear leveling curve.
        Formula: Level = sqrt(XP / 50) + 1
        
        Examples:
        0 XP -> Lvl 1
        50 XP -> Lvl 2
        200 XP -> Lvl 3 (Gap: 150)
        450 XP -> Lvl 4 (Gap: 250)
        800 XP -> Lvl 5 (Gap: 350)
        """
        if total_xp < 0: return 1
        return int(math.sqrt(total_xp / 50)) + 1

    @staticmethod
    def calculate_xp_for_next_level(current_level):
        """
        Reverse formula: XP = 50 * (Level - 1)^2
        Returns total XP needed to reach (current_level + 1).
        """
        next_level = current_level + 1
        return 50 * ((next_level - 1) ** 2)

    @staticmethod
    def calculate_streak_multiplier(streak_days):
        """
        Calculates XP multiplier based on streak duration.
        Logic:
        - Days 0-7: 1.0x (Building habit)
        - Days 7-30: +0.1x per day (Momentum)
        - Cap: 3.0x
        """
        if streak_days < 7:
            return 1.0
        
        # Bonus starts after day 7
        bonus_days = streak_days - 7
        multiplier = 1.0 + (bonus_days * 0.05) # Growth: 5% per day
        
        return min(multiplier, GamificationEngine.MAX_MULTIPLIER)

    @staticmethod
    def calculate_habit_xp(habit_streak):
        """
        Returns (base_xp, multiplier, total_xp) tuple.
        """
        multiplier = GamificationEngine.calculate_streak_multiplier(habit_streak)
        earned_xp = int(GamificationEngine.BASE_XP * multiplier)
        return earned_xp, round(multiplier, 2)
