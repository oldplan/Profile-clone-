import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.errors import RPCError, FloodWaitError, MessageNotModifiedError

# ─── CONFIG ───────────────────────────────────────────────────────────────────
API_ID       = 
API_HASH     = ""
SESSION_NAME = "forwarder_session"

BACKUP_PHOTO   = "original_profile_photo.jpg"
TEMP_PHOTO     = "temp_clone_photo.jpg"
MAX_FLOOD_WAIT = 15
ANIM_SPEED     = 0.55   # seconds between animation frames
# ──────────────────────────────────────────────────────────────────────────────

client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)

original_profile = {
    "first_name": None,
    "last_name":  None,
    "about":      None,
    "photo_path": None,
}

# ─── ANIMATION FRAMES ─────────────────────────────────────────────────────────

def _clone_frames(name: str) -> list[str]:
    return [
        "```\n"
        "╔══════════════════════╗\n"
        "║   CLONE  INITIATED   ║\n"
        "╚══════════════════════╝\n"
        f"  target : {name}\n"
        "```",

        "```\n"
        "  [▓░░░░░░░░░]  10%\n"
        "  → scanning identity...\n"
        "```",

        "```\n"
        "  [▓▓▓░░░░░░░]  30%\n"
        "  → extracting metadata...\n"
        "```",

        "```\n"
        "  [▓▓▓▓▓░░░░░]  50%\n"
        "  → pulling profile photo...\n"
        "```",

        "```\n"
        "  [▓▓▓▓▓▓▓░░░]  70%\n"
        "  → reading bio...\n"
        "```",

        "```\n"
        "  [▓▓▓▓▓▓▓▓▓░]  90%\n"
        "  → overwriting local profile...\n"
        "```",

        "```\n"
        "  [▓▓▓▓▓▓▓▓▓▓]  100%\n"
        "  → erasing traces...\n"
        "```",

        f"✦  **CLONED** → `{name}`\n"
        f"› name • bio • photo copied\n"
        f"› `!rv` to revert",
    ]

def _revert_frames(name: str) -> list[str]:
    return [
        "```\n"
        "╔══════════════════════╗\n"
        "║   REVERT  INITIATED  ║\n"
        "╚══════════════════════╝\n"
        "```",

        "```\n"
        "  [▓▓░░░░░░░░]  20%\n"
        "  → restoring name...\n"
        "```",

        "```\n"
        "  [▓▓▓▓▓░░░░░]  50%\n"
        "  → restoring bio...\n"
        "```",

        "```\n"
        "  [▓▓▓▓▓▓▓▓░░]  80%\n"
        "  → re-uploading photo...\n"
        "```",

        "```\n"
        "  [▓▓▓▓▓▓▓▓▓▓]  100%\n"
        "  → identity restored.\n"
        "```",

        f"✅  **RESTORED** → `{name}`\n"
        f"› you're yourself again.",
    ]

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _cleanup(*paths: str) -> None:
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

def _clear_backup() -> None:
    original_profile.update({
        "first_name": None,
        "last_name":  None,
        "about":      None,
        "photo_path": None,
    })

async def _safe_delete(msg) -> None:
    try:
        await msg.delete()
    except Exception:
        pass

async def _safe_edit(msg, text: str) -> None:
    try:
        await msg.edit(text)
    except (MessageNotModifiedError, FloodWaitError):
        pass
    except Exception:
        pass

async def _animate(msg, frames: list[str], delay: float = ANIM_SPEED) -> None:
    for frame in frames:
        await _safe_edit(msg, frame)
        await asyncio.sleep(delay)

async def _flood_safe(fn, *args, **kwargs):
    try:
        return await fn(*args, **kwargs)
    except FloodWaitError as e:
        if e.seconds <= MAX_FLOOD_WAIT:
            await asyncio.sleep(e.seconds + 1)
            return await fn(*args, **kwargs)
        raise

# ─── PROFILE OPS ──────────────────────────────────────────────────────────────

async def backup_profile() -> bool | str:
    try:
        me   = await client.get_me()
        full = await client(GetFullUserRequest(me))

        original_profile["first_name"] = me.first_name or ""
        original_profile["last_name"]  = me.last_name  or ""
        original_profile["about"]      = full.full_user.about or ""

        _cleanup(BACKUP_PHOTO)
        downloaded = await client.download_profile_photo(me, BACKUP_PHOTO)
        original_profile["photo_path"] = BACKUP_PHOTO if downloaded else None
        return True

    except RPCError as e:
        return f"RPC error during backup: {e}"
    except Exception as e:
        return f"Backup failed: {e}"

def _parse_clone_args(text: str):
    parts = text.strip().split()[1:]
    username = None
    for part in parts:
        if part.startswith("@") or (part.isalnum() and len(part) > 1):
            username = part.lstrip("@")
    return username

# ─── HANDLERS ─────────────────────────────────────────────────────────────────

@client.on(events.NewMessage(outgoing=True, pattern=r'^!clone(?:\s+[\w@]+)?$'))
async def clone_handler(event):
    await _safe_delete(event.message)

    username    = _parse_clone_args(event.text)
    target_user = None

    try:
        if event.is_reply:
            target_user = await (await event.get_reply_message()).get_sender()
        elif username:
            try:
                target_user = await client.get_entity(username)
            except Exception:
                msg = await client.send_message("me", f"✘ Clone failed: @{username} not found.")
                return
        else:
            await client.send_message("me", "✘ Clone: Reply to a message OR use: !clone @username")
            return

        if not target_user:
            await client.send_message("me", "✘ Clone: Could not resolve target user.")
            return

    except RPCError as e:
        await client.send_message("me", f"✘ Clone RPC error: {e}")
        return

    first     = target_user.first_name or ""
    last      = target_user.last_name  or ""
    full_name = f"{first} {last}".strip()

    # Start animation in Saved Messages
    anim_msg = await client.send_message("me", "⏳ Initialising...")
    frames   = _clone_frames(full_name)

    # Play first 3 frames while doing prep work
    await _animate(anim_msg, frames[:3])

    # Fetch target bio
    target_about = ""
    try:
        target_full  = await client(GetFullUserRequest(target_user))
        target_about = target_full.full_user.about or ""
    except Exception:
        pass

    # Backup own profile
    result = await backup_profile()
    if result is not True:
        await _safe_edit(anim_msg, f"✘ Backup failed: {result}")
        return

    # Download photo (frame 4)
    await _safe_edit(anim_msg, frames[3])
    _cleanup(TEMP_PHOTO)
    try:
        downloaded = await client.download_profile_photo(target_user, TEMP_PHOTO)
        if not downloaded:
            await _safe_edit(anim_msg, f"✘ {full_name} has no profile photo.")
            return
    except Exception as e:
        await _safe_edit(anim_msg, f"✘ Photo download failed: {e}")
        return

    # Bio frame
    await _safe_edit(anim_msg, frames[4])
    await asyncio.sleep(ANIM_SPEED)

    # Apply name + bio (frame 5)
    await _safe_edit(anim_msg, frames[5])
    try:
        await _flood_safe(
            client,
            UpdateProfileRequest(first_name=first, last_name=last, about=target_about)
        )
    except RPCError as e:
        _cleanup(TEMP_PHOTO)
        await _safe_edit(anim_msg, f"✘ Name/bio update failed: {e}")
        return

    # Upload photo (frame 6)
    await _safe_edit(anim_msg, frames[6])
    await asyncio.sleep(ANIM_SPEED)
    try:
        file = await client.upload_file(TEMP_PHOTO)
        await _flood_safe(client, UploadProfilePhotoRequest(file=file))
    except RPCError as e:
        await _safe_edit(anim_msg, f"✘ Photo upload failed: {e}")
        return
    finally:
        _cleanup(TEMP_PHOTO)

    # Final success frame
    await _safe_edit(anim_msg, frames[7])


@client.on(events.NewMessage(outgoing=True, pattern=r'^!rv$'))
async def reverse_handler(event):
    await _safe_delete(event.message)

    if original_profile["first_name"] is None:
        await client.send_message("me", "✘ No backup found. Run !clone first.")
        return

    own_name = original_profile["first_name"] + (
        " " + original_profile["last_name"] if original_profile["last_name"] else ""
    )

    anim_msg = await client.send_message("me", "⏳ Reverting...")
    frames   = _revert_frames(own_name)

    # Restore name + bio
    await _safe_edit(anim_msg, frames[1])
    await asyncio.sleep(ANIM_SPEED)
    try:
        await _flood_safe(
            client,
            UpdateProfileRequest(
                first_name=original_profile["first_name"],
                last_name=original_profile["last_name"],
                about=original_profile["about"],
            )
        )
    except RPCError:
        pass

    # Restore photo
    await _safe_edit(anim_msg, frames[2])
    await asyncio.sleep(ANIM_SPEED)
    await _safe_edit(anim_msg, frames[3])
    await asyncio.sleep(ANIM_SPEED)

    photo_path = original_profile.get("photo_path")
    if photo_path and os.path.exists(photo_path):
        try:
            file = await client.upload_file(photo_path)
            await _flood_safe(client, UploadProfilePhotoRequest(file=file))
        except RPCError:
            pass
        finally:
            _cleanup(photo_path)
            original_profile["photo_path"] = None
    else:
        try:
            me = await client.get_me()
            photos = await client.get_profile_photos(me)
            if photos:
                await client(DeletePhotosRequest(photos[:1]))
        except Exception:
            pass

    _clear_backup()
    await _safe_edit(anim_msg, frames[4])
    await asyncio.sleep(ANIM_SPEED)
    await _safe_edit(anim_msg, frames[5])


# ─── STARTUP ──────────────────────────────────────────────────────────────────

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  Userbot online — Clone + Anim Mode")
print("  !clone           → clone (reply)")
print("  !clone @username → clone by username")
print("  !rv              → restore original")
print("  Animations play in Saved Messages")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

client.start()
client.run_until_disconnected()
      
