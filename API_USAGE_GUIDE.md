# BinBuddy Points & Rewards API - Usage Guide

## Authentication
All endpoints require JWT token in Authorization header:
```
Authorization: Bearer <your_access_token>
```

## Endpoints Reference

### 1. Get Current User's Points
**Endpoint:** `GET /api/points/user`

**Request:**
```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:5000/api/points/user
```

**Response:**
```json
{
  "id": 2,
  "name": "Ramesh Patil",
  "points": 150,
  "tier": "bronze",
  "role": "collector",
  "next_tier_points": {
    "tier": "silver",
    "points_needed": 650
  }
}
```

---

### 2. Get Public Points (For Leaderboards)
**Endpoint:** `GET /api/points/user/<user_id>`

**Request:**
```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:5000/api/points/user/2
```

**Response:**
```json
{
  "id": 2,
  "name": "Ramesh Patil",
  "points": 150,
  "tier": "bronze",
  "role": "collector"
}
```

---

### 3. Get Leaderboard (Top Earners)
**Endpoint:** `GET /api/points/leaderboard?role=collector&limit=50`

**Query Parameters:**
- `role` (optional): Filter by "collector" or "citizen"
- `limit` (optional, default: 50): Max number of users to return

**Request:**
```bash
# Get top 10 workers
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:5000/api/points/leaderboard?role=collector&limit=10"

# Get top 20 citizens
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:5000/api/points/leaderboard?role=citizen&limit=20"
```

**Response:**
```json
[
  {
    "rank": 1,
    "id": 2,
    "name": "Ramesh Patil",
    "points": 1250,
    "tier": "gold",
    "role": "collector",
    "zone": "Gandhi Nagar Ward"
  },
  {
    "rank": 2,
    "id": 3,
    "name": "Sanjay Kumar",
    "points": 980,
    "tier": "silver",
    "role": "collector",
    "zone": "Nehru Nagar Ward"
  }
]
```

---

### 4. Get User's Points Transaction History
**Endpoint:** `GET /api/points/ledger?limit=50`

**Query Parameters:**
- `limit` (optional, default: 50): Max transactions to return

**Request:**
```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:5000/api/points/ledger?limit=20"
```

**Response:**
```json
[
  {
    "id": 5,
    "complaint_id": 3,
    "points_earned": 50,
    "action_type": "early_resolve",
    "reason": "Resolved complaint within 24 hours",
    "created_at": "2026-02-27T14:35:22"
  },
  {
    "id": 4,
    "complaint_id": 2,
    "points_earned": 30,
    "action_type": "complaint_resolved",
    "reason": "Resolved complaint",
    "created_at": "2026-02-26T10:20:45"
  },
  {
    "id": 3,
    "complaint_id": 1,
    "points_earned": 30,
    "action_type": "complaint_resolved",
    "reason": "Resolved complaint",
    "created_at": "2026-02-25T09:15:30"
  }
]
```

---

### 5. List Available Rewards
**Endpoint:** `GET /api/points/rewards?role=collector`

**Query Parameters:**
- `role` (optional): Filter rewards by role

**Request:**
```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:5000/api/points/rewards
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Coffee Voucher",
    "description": "Free coffee at local cafe",
    "points_required": 500,
    "category": "voucher",
    "reward_type": "voucher",
    "value": "₹200"
  },
  {
    "id": 2,
    "name": "Lunch Voucher",
    "description": "Lunch voucher at municipal cafeteria",
    "points_required": 1000,
    "category": "voucher",
    "reward_type": "voucher",
    "value": "₹500"
  },
  {
    "id": 5,
    "name": "Gold Badge",
    "description": "Gold tier badge on profile",
    "points_required": 2000,
    "category": "badge",
    "reward_type": "badge",
    "value": "gold_badge"
  }
]
```

---

### 6. Redeem a Reward
**Endpoint:** `POST /api/points/redeem/<reward_id>`

**Path Parameters:**
- `reward_id`: ID of the reward to redeem

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:5000/api/points/redeem/1
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Reward redeemed successfully",
  "claim_code": "ABC7XYZ9",
  "reward": "Coffee Voucher",
  "remaining_points": 1595
}
```

**Response (Insufficient Points):**
```json
{
  "error": "Insufficient points",
  "required": 500,
  "current": 150
}
```

**Response (Reward Not Available):**
```json
{
  "error": "Reward is no longer available"
}
```

---

### 7. Get User's Redeemed Rewards
**Endpoint:** `GET /api/points/user-rewards?limit=100`

**Query Parameters:**
- `limit` (optional, default: 100): Max rewards to return

**Request:**
```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:5000/api/points/user-rewards"
```

**Response:**
```json
[
  {
    "id": 1,
    "reward_name": "Coffee Voucher",
    "claim_code": "ABC7XYZ9",
    "status": "pending",
    "redeemed_at": "2026-02-27T15:45:22"
  },
  {
    "id": 2,
    "reward_name": "Lunch Voucher",
    "claim_code": "DEF5KLM2",
    "status": "claimed",
    "redeemed_at": "2026-02-26T11:20:15"
  }
]
```

---

## Common Use Cases

### Use Case 1: Display User Dashboard Points
```javascript
async function displayPoints() {
  const response = await fetch('/api/points/user', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await response.json();
  
  document.getElementById('points').innerText = data.points;
  document.getElementById('tier').innerText = data.tier.toUpperCase();
  document.getElementById('next-tier').innerText = 
    `${data.next_tier_points.points_needed} more points to ' ${data.next_tier_points.tier.toUpperCase()}'`;
}
```

### Use Case 2: Show Leaderboard
```javascript
async function showLeaderboard(role = 'collector') {
  const response = await fetch(`/api/points/leaderboard?role=${role}&limit=10`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const users = await response.json();
  
  const html = users.map(u => `
    <tr>
      <td>${u.rank}</td>
      <td>${u.name}</td>
      <td>${u.points}</td>
      <td>${u.tier}</td>
    </tr>
  `).join('');
  
  document.getElementById('leaderboard-body').innerHTML = html;
}
```

### Use Case 3: Display Rewards and Handle Redemption
```javascript
async function showRewards() {
  const response = await fetch('/api/points/rewards', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const rewards = await response.json();
  
  // Display rewards...
}

async function redeemReward(rewardId) {
  const response = await fetch(`/api/points/redeem/${rewardId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  const result = await response.json();
  if (result.success) {
    alert(`Claim Code: ${result.claim_code}`);
  } else {
    alert(`Error: ${result.error}`);
  }
}
```

### Use Case 4: Show Points Transaction History
```javascript
async function showPointsHistory() {
  const response = await fetch('/api/points/ledger?limit=30', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const transactions = await response.json();
  
  const html = transactions.map(t => `
    <tr>
      <td>Complaint #${t.complaint_id}</td>
      <td>${t.action_type}</td>
      <td class="positive">+${t.points_earned}</td>
      <td>${new Date(t.created_at).toLocaleDateString()}</td>
    </tr>
  `).join('');
  
  document.getElementById('history-body').innerHTML = html;
}
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad request (insufficient points, etc.) |
| 401 | Unauthorized (invalid/missing token) |
| 404 | Resource not found |
| 500 | Server error |

**Example Error Response:**
```json
{
  "error": "Insufficient points",
  "required": 500,
  "current": 150
}
```

---

## Notes

1. **Points are awarded automatically** when complaints are filed/resolved in the system
2. **Tier updates are automatic** based on total points
3. **Claim codes are unique** and can be used for redemption validation by municipal office
4. **All timestamps are in UTC** and returned in ISO 8601 format
5. **Points cannot go negative** - redemption will be rejected if insufficient points
6. **Rewards can be deactivated** by municipal admins (set `is_active = 0` in database)

