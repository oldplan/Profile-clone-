# 🕶️ Userbot — Silent Clone System

A Telethon-based userbot that clones any Telegram user's profile (name, bio, photo) into yours — silently. No messages left in any chat. All feedback plays privately in **Saved Messages**.

---

## ⚙️ Setup

### 1. Install dependencies
```bash
pip install telethon
```

### 2. Configure credentials
Open `userbot.py` and set your values at the top:
```python
API_ID       = your_api_id
API_HASH     = "your_api_hash"
SESSION_NAME = "forwarder_session"   # session file name, change if needed
```

Get your `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org).

### 3. Run
```bash
python userbot.py
```
On first run, Telethon will ask for your phone number and OTP to create a session file.

---

## 🧩 Commands

| Command | Description |
|---|---|
| `!clone` | Clone the user you replied to |
| `!clone @username` | Clone a user by username |
| `!rv` | Revert your profile back to original |

---

## 🔄 What Gets Cloned & Reverted

| Field | Cloned | Reverted |
|---|---|---|
| First name | ✅ | ✅ |
| Last name | ✅ | ✅ |
| Bio (about) | ✅ | ✅ |
| Profile photo | ✅ | ✅ |

---

## 🎬 Animation

Both `!clone` and `!rv` play a live progress animation **only in your Saved Messages** — no one else sees it. Each frame is synced to an actual operation (backup → download → apply → upload), so the progress bar reflects real work.

---

## 🔒 Privacy

- Your command message is **deleted instantly** before anything runs
- No messages are sent to any group or chat
- All status updates go to **Saved Messages** only
- Temp photo files are cleaned up automatically after each operation

---

## 📁 Files

```
userbot.py                  — main bot
forwarder_session.session   — Telethon session (auto-created)
original_profile_photo.jpg  — your backup photo (auto-created, auto-deleted)
temp_clone_photo.jpg        — target photo temp file (auto-deleted)
```

---

## ⚠️ Notes

- If the target user has no profile photo, the clone will abort and notify you in Saved Messages
- If the target's bio is private/restricted, the clone proceeds with an empty bio
- FloodWait errors are handled automatically (up to 15 seconds)
- Always run `!rv` before cloning someone new to avoid losing your original backup

---

## 🛠️ Config Options

Inside `userbot.py` you can tweak:

```python
MAX_FLOOD_WAIT = 15     # max seconds to wait on FloodWait before giving up
ANIM_SPEED     = 0.55   # delay between animation frames (seconds)
```

