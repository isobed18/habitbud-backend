import math


class GamificationEngine:
    """
    Central scoring engine for HabitBud.

    Core idea (Duolingo-style, social-first):
      - Sending a "check" (a habit-proof snap to a friend) is cheap but rewarded.
      - The real value comes when a friend APPROVES your check.
      - Streaks (habit streak + friendship streak) act as multipliers, so
        consistency compounds — but logarithmically, so it never runs away.

    XP flow per check:
      sender on submit        -> BASE_SUBMIT_XP                       (flat)
      sender on approval      -> BASE_VERIFY_XP   x habit_mult x friend_mult
      verifier on approval    -> BASE_VERIFIER_XP x friend_mult
    """

    # ---- Base XP values -----------------------------------------------------
    BASE_SUBMIT_XP = 5      # sending a check (the "paper-plane" reward)
    BASE_SELF_XP = 5        # self-marking a habit complete without a check
    BASE_VERIFY_XP = 10     # sender's reward when a check gets approved
    BASE_VERIFIER_XP = 3    # reward for the friend who approves a check

    # ---- Streak tiers (verification streak) ---------------------------------
    # (min_streak, tier_number, name)
    STREAK_TIERS = [
        (100, 6, 'Eternal'),
        (60,  5, 'Phoenix'),
        (30,  4, 'Inferno'),
        (14,  3, 'Blaze'),
        (7,   2, 'Flame'),
        (1,   1, 'Spark'),
        (0,   0, 'None'),
    ]

    # Streak lengths that trigger a celebration (badge + push notification).
    STREAK_MILESTONES = (5, 7, 14, 30, 60, 100, 365)

    # ---- Multipliers --------------------------------------------------------
    @staticmethod
    def calculate_habit_streak_multiplier(streak_days):
        """
        Habit streak multiplier: 1.0 + ln(1 + streak / 10)
          1d -> 1.10x   7d -> 1.53x   30d -> 2.39x   100d -> 3.40x
        """
        if streak_days <= 0:
            return 1.0
        return 1.0 + math.log(1 + streak_days / 10)

    @staticmethod
    def calculate_friend_streak_multiplier(friend_streak_days):
        """
        Friendship streak multiplier: 1.0 + 0.5 * ln(1 + streak / 5)
          1d -> 1.09x   10d -> 1.40x   30d -> 1.74x   100d -> 2.16x
        """
        if friend_streak_days <= 0:
            return 1.0
        return 1.0 + 0.5 * math.log(1 + friend_streak_days / 5)

    @staticmethod
    def calculate_full_reward(base_xp, habit_streak=0, friend_streak=0):
        """
        Full reward: base * habit_mult * friend_mult.
        Returns (total_xp:int, habit_mult:float, friend_mult:float).
        """
        h_mult = GamificationEngine.calculate_habit_streak_multiplier(habit_streak)
        f_mult = GamificationEngine.calculate_friend_streak_multiplier(friend_streak)
        total = int(round(base_xp * h_mult * f_mult))
        return total, round(h_mult, 2), round(f_mult, 2)

    # ---- Tiers / milestones -------------------------------------------------
    @staticmethod
    def get_streak_tier(streak_days):
        """Returns (tier_number, tier_name) for a given streak."""
        for min_streak, tier, name in GamificationEngine.STREAK_TIERS:
            if streak_days >= min_streak:
                return tier, name
        return 0, 'None'

    @staticmethod
    def is_milestone(streak_days):
        """True when this streak length deserves a celebration."""
        return streak_days in GamificationEngine.STREAK_MILESTONES

    # ---- Levels -------------------------------------------------------------
    @staticmethod
    def calculate_level(total_xp):
        """Non-linear leveling: level = floor(sqrt(xp / 50)) + 1."""
        if total_xp < 0:
            return 1
        return int(math.sqrt(total_xp / 50)) + 1

    @staticmethod
    def calculate_xp_for_next_level(current_level):
        """XP threshold to reach the next level: 50 * level^2."""
        return 50 * (current_level ** 2)
