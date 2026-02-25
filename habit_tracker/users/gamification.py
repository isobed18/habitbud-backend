import math

class GamificationEngine:
    """
    Central scoring engine using logarithmic multiplier curves.
    
    Philosophy: Streaks only count verified completions.
    Self-completion → flat XP. Verification → multiplied XP.
    """

    # Base XP values
    BASE_SELF_XP = 5       # Self-completion without proof
    BASE_VERIFY_XP = 15    # Sender XP when proof is verified
    BASE_VERIFIER_XP = 5   # Verifier XP for verifying friend's proof

    # Streak tiers: (min_streak, tier_number, name)
    STREAK_TIERS = [
        (100, 6, 'Eternal'),
        (60,  5, 'Phoenix'),
        (30,  4, 'Inferno'),
        (14,  3, 'Blaze'),
        (7,   2, 'Flame'),
        (1,   1, 'Spark'),
        (0,   0, 'None'),
    ]

    @staticmethod
    def calculate_habit_streak_multiplier(streak_days):
        """
        Logarithmic multiplier based on habit verification streak.
        Formula: 1.0 + ln(1 + streak / 10)
        
        Examples:
          1d  → 1.10x    7d  → 1.53x
         30d  → 2.39x  100d  → 3.40x
        365d  → 4.62x
        """
        if streak_days <= 0:
            return 1.0
        return 1.0 + math.log(1 + streak_days / 10)

    @staticmethod
    def calculate_friend_streak_multiplier(friend_streak_days):
        """
        Logarithmic multiplier based on friendship verification streak.
        Formula: 1.0 + 0.5 × ln(1 + streak / 5)
        
        Examples:
          0d → 1.00x    1d → 1.09x
         10d → 1.40x   30d → 1.74x
        100d → 2.16x
        """
        if friend_streak_days <= 0:
            return 1.0
        return 1.0 + 0.5 * math.log(1 + friend_streak_days / 5)

    @staticmethod
    def calculate_full_reward(base_xp, habit_streak=0, friend_streak=0):
        """
        Full XP calculation: base × habit_mult × friend_mult.
        Returns (total_xp, habit_mult, friend_mult) tuple.
        """
        h_mult = GamificationEngine.calculate_habit_streak_multiplier(habit_streak)
        f_mult = GamificationEngine.calculate_friend_streak_multiplier(friend_streak)
        total = int(base_xp * h_mult * f_mult)
        return total, round(h_mult, 2), round(f_mult, 2)

    @staticmethod
    def get_streak_tier(streak_days):
        """
        Returns (tier_number, tier_name) for a given streak.
        """
        for min_streak, tier, name in GamificationEngine.STREAK_TIERS:
            if streak_days >= min_streak:
                return tier, name
        return 0, 'None'

    @staticmethod
    def calculate_level(total_xp):
        """
        Non-linear leveling: Level = sqrt(XP / 50) + 1
        """
        if total_xp < 0:
            return 1
        return int(math.sqrt(total_xp / 50)) + 1

    @staticmethod
    def calculate_xp_for_next_level(current_level):
        """
        XP needed for next level: 50 × (level)^2
        """
        return 50 * (current_level ** 2)
