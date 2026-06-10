# Chat Rooms & Shared Streaks — Review Notes (2026-06-10)

Scope: "chat oda mantığı modernleştirilecek" + "ortak streak gözden geçirilecek".
What changed now, and what the next concrete steps are.

## Done in this pass

- **Perf**: conversations list prefetches participants; messages select_related
  sender; (conversation, created_at) index; last-message joins sender. Group
  payloads no longer N+1.
- **Group presence**: members' 3D avatars side-by-side in group chat
  ("Ekibi 3D gör" toggle — opt-in so canvases don't tax every open).
- **Custom chat UI** (gifted-chat removed) — full control for the next steps.

## Shared/friendship streak — current behavior (verified in code)

- `Friendship.update_streak()` bumps the pair streak whenever a check between
  the two is approved; it feeds the friend multiplier (1 + 0.5·ln(1+s/5)).
- Group rooms have freeze pooling (reserve ❄️) and recovery banners.
- Anti-farm now caps approval payouts at 1/habit/day, so pair streaks can't be
  spammed for XP.

## Recommended next steps (not yet built)

1. **Group habit ritual**: a room-level daily target ("everyone checks in
   today") with a room streak counter — the social-accountability core the user
   wants. Model: `Conversation.room_streak`, bumped when ALL members have an
   approved check that day (cron or on-verify hook).
2. **Modern chat ergonomics**: message pagination (currently full list),
   optimistic send, delivery states, image thumbnails in list.
3. **WS presence**: who's online in the room (channels groups already exist).
4. **Shared streak surfacing**: show the pair streak in the chat header next to
   the flame (data already in Friendship.streak).
