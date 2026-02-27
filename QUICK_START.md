# Points & Rewards System - Quick Start Guide

## Installation (2 minutes)

### Step 1: Run Database Migration
```bash
cd backend
python migrate_db.py
```
This adds the points system tables and columns to your database.

### Step 2: Seed Sample Rewards
```bash
python fix_rewards.py
```
This creates 8 sample rewards that users can redeem.

### Step 3: Done! 
The system is fully operational. No app restart needed (Flask will reload).

---

## How to Use

### For Workers (Collectors)
1. **Go to Worker Dashboard**
2. **Overview Tab:**
   - See "My Points" KPI card showing your current points
   - See "Current Tier" showing your level (Bronze/Silver/Gold/Platinum)
3. **Leaderboard Tab:**
   - See top earners in your zone
   - Filter by Workers or Citizens
4. **Rewards Tab:**
   - Browse available rewards
   - Click "Redeem Now" when you have enough points
   - Get a unique claim code to use at municipal office

**How to Earn Points:**
- Resolve a complaint = **30 points**
- Resolve within 24 hours = **50 points** (30 + 20 bonus)

### For Citizens
1. **Go to Citizen Dashboard**
2. **My Dashboard:**
   - See "My Points" showing points earned from complaints
   - See "Current Tier" 
3. **Report Issue Tab:**
   - File a new complaint = **10 points**

---

## Points System Flow

### When a Complaint is Filed:
```
Citizen files complaint
         ↓
System checks: Did citizen include photo & description?
         ↓
✅ Complaint saved → +10 points added to citizen
                  → Tier updated if needed
```

### When a Complaint is Resolved:
```
Worker completes complaint with photo
         ↓
System marks as "resolved"
         ↓
✅ Check: Within 24 hours of creation?
   • YES → +50 points (30 base + 20 bonus)  
   • NO  → +30 points (base)
         ↓
Worker's tier updated automatically
Points appear in Rewards tab leaderboard
```

---

## Reward Tiers

| Tier | Points | What it means |
|------|--------|--------------|
| 🥉 **Bronze** | 0-799 | Getting started |
| 🥈 **Silver** | 800-1999 | Good progress |
| 🥇 **Gold** | 2000-4999 | Top performer |
| 🏆 **Platinum** | 5000+ | Elite status |

---

## Available Rewards

| Reward | Cost | Type |
|--------|------|------|
| ☕ Coffee Voucher | 500 pts | ₹200 value |
| 🍽️ Lunch Voucher | 1000 pts | ₹500 value |
| 🎬 Movie Ticket | 800 pts | ₹300 value |
| 🛒 Shopping Voucher | 1500 pts | ₹750 value |
| 🏅 Gold Badge | 2000 pts | Profile display |
| 🎁 Special Gift Pack | 3000 pts | Premium kit |
| 👑 Platinum Badge | 5000 pts | Profile display |
| 💳 Bonus Voucher | 2500 pts | ₹1000 value |

---

## Frequently Asked Questions

### Q: When do I earn points?
**A:** 
- Citizens: When you file a complaint (+10 points)
- Workers: When you resolve a complaint (+30 base, +20 bonus if within 24h)

### Q: How are tiers assigned?
**A:** Automatically based on total points. No action needed - just earn points!

### Q: Can I lose points?
**A:** Yes, only when you redeem a reward. Points deducted = reward cost.

### Q: What is a claim code?
**A:** A unique code generated when you redeem a reward. Show it to the municipal office to claim your reward.

### Q: Can I undo a redemption?
**A:** Contact your municipal office admin to reverse a redemption.

### Q: What if I don't have enough points?
**A:** The "Redeem Now" button will show "Not Enough Points" and be disabled. Keep working!

### Q: Are rewards available to everyone?
**A:** Yes! Both workers and citizens can earn points and redeem rewards.

### Q: What happens if a reward expires?
**A:** Currently rewards don't expire, but check with your municipal coordinator.

---

## Admin Management (For Municipal Office)

### View All User Points
```bash
# Direct database query
SELECT id, name, points, tier, role FROM users ORDER BY points DESC;
```

### View Rewards Transactions
```bash
# See all redemptions
SELECT u.name, r.name, ur.claim_code, ur.status, ur.redeemed_at 
FROM user_rewards ur
JOIN users u ON ur.user_id = u.id
JOIN rewards r ON ur.reward_id = r.id
ORDER BY ur.redeemed_at DESC;
```

### Add New Reward (if needed)
```bash
INSERT INTO rewards (name, description, points_required, category, reward_type, value, is_active)
VALUES ('Gift Name', 'Description', 2500, 'voucher', 'voucher', '₹Value', 1);
```

### Deactivate a Reward
```bash
UPDATE rewards SET is_active = 0 WHERE id = 5;
```

### Reset User Points (if needed)
```bash
UPDATE users SET points = 0, tier = 'bronze' WHERE id = <user_id>;
DELETE FROM points_ledger WHERE user_id = <user_id>;
```

---

## Troubleshooting

### Points not showing?
1. Refresh the page (Ctrl+F5)
2. Check if complaintsAPI is returning data
3. Verify token is still valid (login again if needed)

### Reward redemption failing?
1. Check if you have enough points
2. Ensure network connection is stable
3. Try again or contact support

### Can't see leaderboard?
1. Make sure you're logged in
2. Check network tab in browser for errors
3. Reload the page

### Points not updated after resolving complaint?
1. Ensure complaint was marked as "resolved" successfully
2. Refresh the browser
3. If still not showing, contact admin

---

## API Reference (For Developers)

### Get Current Points
```bash
GET /api/points/user
Response: { points: 150, tier: "bronze", next_tier_points: {...} }
```

### Get Leaderboard
```bash
GET /api/points/leaderboard?role=collector&limit=10
Response: [ { rank: 1, name: "...", points: 500, tier: "gold" }, ... ]
```

### List Rewards
```bash
GET /api/points/rewards
Response: [ { id: 1, name: "...", points_required: 500, ... }, ... ]
```

### Redeem Reward
```bash
POST /api/points/redeem/1
Response: { success: true, claim_code: "ABC123XYZ", remaining_points: 50 }
```

### Get Points History
```bash
GET /api/points/ledger?limit=20
Response: [ { action_type: "complaint_resolved", points_earned: 30, ... }, ... ]
```

See [API_USAGE_GUIDE.md](API_USAGE_GUIDE.md) for complete API documentation.

---

## Support

If you encounter issues:
1. Check the system logs: `tail -f logs/binbuddy.log`
2. Verify database connection is working
3. Ensure all tables exist: `SHOW TABLES LIKE '%reward%';`
4. Contact your technical administrator

---

**System Status:** ✅ Online & Operational  
**Last Updated:** Feb 27, 2026
