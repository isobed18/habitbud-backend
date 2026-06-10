# HabitBud Economy — XP, Diamonds, Shop Sweet Spots

## Earning rates (after the anti-farm guards)

| Action | XP | 💎 | Daily cap |
|---|---|---|---|
| Send a check (first per habit/day) | +5 flat | — | 1×/habit/day |
| Check approved (sender) | 10 × habit_mult × friend_mult | +1 | 1×/habit/day |
| Approve a friend's check (verifier) | 3 × friend_mult | +1 | 1×/habit/day (per habit) |
| Self-complete (no check) | +5 flat | — | idempotent per day |
| Streak milestone (5/7/14/30/60/100/365) | — | streak×2 | once, gated with daily reward |
| Challenge completion | template reward_xp | template reward_points | per challenge |

Multipliers stay logarithmic (habit: 1+ln(1+s/10), friend: 1+0.5·ln(1+s/5)), so
a fully engaged free user (5 habits, friends active) lands around **100–150 XP
and ~5–10 💎 per day**. That's the number shop prices hang off.

## Anti-farm guards (implemented)

- **Submit XP**: only the first check per habit per day pays (+5). Re-sending the
  same habit's check to other friends still works socially — just no XP.
- **Approval payout** (sender XP, verifier XP, both 💎, milestone bonus): only the
  first approval per habit per day. Mutual ping-pong approving = status only.
- **AI quota**: free 5 approved AI verifications/day; only APPROVED consumes;
  per-day per-user counter → habit add/delete churn can't farm or reset it.
- **Rate limits**: checks 30/hour (scoped), user 300/min, anon 60/min.
- **Self-complete** is idempotent per day (HabitCompletion unique per day).
- **Freeze stockpiling** capped at 2.

## Shop sweet spots (suggested price bands)

Anchor: ~7 💎/day for an active free user.

| Tier | Price | Rationale |
|---|---|---|
| Common cosmetic item | 15–25 💎 | ~3 days of play |
| Rare cosmetic | 40–60 💎 | ~1 week — visible flex |
| Epic / animated | 90–140 💎 | ~2–3 weeks, aspirational |
| Streak Freeze | 20 💎 (max 2 held) | meaningful but not hoardable |
| Legendary / seasonal | 200+ 💎 or paid-only | whale/premium anchor |

Set per-item prices in admin (`Item.price_points`, `is_shop_item`); keep paid
users' perks functional (unlimited habits + unlimited AI) rather than pay-to-win
XP, so leaderboards stay fair.

## Known leftovers / watchlist

- Verifier XP has no global daily cap (per-habit cap holds; a user verifying 50
  different friends' habits earns 3×mult each). Add a daily cap if abused.
- Challenge rewards depend on template values — audit templates before launch.
- `users/views.py:439` grants -5 XP on check unsend; unsend+resend on the same
  habit nets 0 with the new first-per-day rule (resend pays nothing). OK.
