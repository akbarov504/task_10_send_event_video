import os
import time
import uuid
import asyncio
import aiohttp
import aiofiles
import subprocess
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sqlite3

from core.config import (
    DB_PATH, LOCAL_PATH, Event,
    API_BASE_EVENT, TOKEN_FILE_PATH,
    CAMERA_INDEX_INNER, CAMERA_INDEX_FRONT,
    WIDTH, HEIGHT, FPS,
)
from utils.token_manager import get_valid_token

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────
DEFAULT_BEFORE = 5   # seconds before event if Event enum has None
DEFAULT_AFTER  = 5   # seconds after  event if Event enum has None

CLIP_DIR       = os.path.join(LOCAL_PATH, "event_clips")
os.makedirs(CLIP_DIR, exist_ok=True)

NOTIFY_URL     = f"{API_BASE_EVENT}/driver-events/media"

# How often the background loop runs (seconds)
POLL_INTERVAL  = 10

# ──────────────────────────────────────────────
# HELPERS: Event timing
# ──────────────────────────────────────────────

def _get_event_window(event_type: str) -> tuple[int, int]:
    """
    Return (before_sec, after_sec) for a given eventType string.
    If before is None → event has no before window, clip = after seconds only (before=0).
    If after  is None → fallback to DEFAULT_AFTER.

    Supports:
      - Exact match:   'HARSH_BRAKE'
      - Prefix match:  'HARSH' → first enum member starting with 'HARSH_'
    """
    # 1. Exact match
    ev = Event.__members__.get(event_type)

    # 2. Prefix match (e.g. 'HARSH' → 'HARSH_BRAKE')
    if ev is None:
        upper = event_type.upper()
        for name, member in Event.__members__.items():
            if name.startswith(upper):
                ev = member
                logger.debug(f"[EVENT_WINDOW] Partial match '{event_type}' → '{name}'")
                break

    if ev is None:
        logger.warning(f"[EVENT_WINDOW] Unknown event type '{event_type}', using defaults.")
        return DEFAULT_BEFORE, DEFAULT_AFTER

    before, after = ev.value
    before = 0             if before is None else int(before)
    after  = DEFAULT_AFTER if after  is None else int(after)
    return before, after


# ──────────────────────────────────────────────
# DB HELPERS (event_videos table)
# ──────────────────────────────────────────────

def _db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def insert_event_video(file_path: str, camera_type: str, device_dt: str, global_event_id: str):
    with _db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO event_videos
                (file_path, camera_type, deviceDateTime, globalEventId, uploaded)
            VALUES (?, ?, ?, ?, 0)
        """, (file_path, camera_type, device_dt, global_event_id))
        conn.commit()


def get_pending_event_groups(limit: int = 10):
    """
    Return groups of event_videos rows keyed by globalEventId
    where the event itself has been fully processed (both inner + front clips exist)
    but not yet uploaded.
    Returns list of dicts: {globalEventId, inner_video, front_video, deviceDateTime}
    """
    with _db() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # Fetch distinct globalEventIds that have uploaded=0 clips
        c.execute("""
            SELECT globalEventId, deviceDateTime,
                   GROUP_CONCAT(camera_type) as cam_types,
                   GROUP_CONCAT(file_path)   as file_paths
            FROM event_videos
            WHERE uploaded = 0
            GROUP BY globalEventId
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()

    groups = []
    for row in rows:
        cam_types  = row["cam_types"].split(",")
        file_paths = row["file_paths"].split(",")
        mapping = dict(zip(cam_types, file_paths))
        groups.append({
            "globalEventId":  row["globalEventId"],
            "deviceDateTime": row["deviceDateTime"],
            "inner_video":    mapping.get("inner"),
            "front_video":    mapping.get("front"),
        })
    return groups


def mark_event_video_uploaded(global_event_id: str):
    with _db() as conn:
        conn.execute(
            "UPDATE event_videos SET uploaded=1 WHERE globalEventId=?",
            (global_event_id,)
        )
        conn.commit()


def increment_event_video_retry(global_event_id: str):
    now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    with _db() as conn:
        conn.execute("""
            UPDATE event_videos
            SET retries = retries + 1, last_try = ?
            WHERE globalEventId = ?
        """, (now, global_event_id))
        conn.commit()


# ──────────────────────────────────────────────
# VIDEO CLIP CUTTING  (ffmpeg)
# ──────────────────────────────────────────────

def _find_segment_file(camera_type: str, dt: datetime) -> str | None:
    """
    Find the 10-second segment file that contains `dt`.
    Segments are named like: inner_20250507_153000.mp4  (start time)
    We look in LOCAL_PATH for a segment whose [start, start+10) window covers dt.
    """
    prefix = "inner_" if camera_type == "inner" else "front_"
    best = None
    for fname in os.listdir(LOCAL_PATH):
        if not fname.startswith(prefix) or not fname.endswith(".mp4"):
            continue
        try:
            ts_str = fname[len(prefix):-4]          # "20250507_153000"
            seg_start = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            seg_end   = seg_start + timedelta(seconds=10)
            if seg_start <= dt < seg_end:
                best = os.path.join(LOCAL_PATH, fname)
                break
        except ValueError:
            continue
    return best


def cut_event_clip(
    camera_type: str,
    event_dt: datetime,
    before_sec: int,
    after_sec: int,
    global_event_id: str,
) -> str | None:
    """
    Cut a (before + after) second clip around event_dt from stored segments.
    Uses ffmpeg concat + trim. Returns output file path or None on failure.
    """
    clip_start = event_dt - timedelta(seconds=before_sec)
    clip_end   = event_dt + timedelta(seconds=after_sec)
    total_dur  = before_sec + after_sec

    # Gather all segment files that overlap the clip window
    prefix = "inner_" if camera_type == "inner" else "front_"
    segments = []
    for fname in sorted(os.listdir(LOCAL_PATH)):
        if not fname.startswith(prefix) or not fname.endswith(".mp4"):
            continue
        try:
            ts_str    = fname[len(prefix):-4]
            seg_start = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            seg_end   = seg_start + timedelta(seconds=10)
            if seg_end > clip_start and seg_start < clip_end:
                segments.append((seg_start, os.path.join(LOCAL_PATH, fname)))
        except ValueError:
            continue

    if not segments:
        logger.warning(f"[CLIP] No segments found for {camera_type} around {event_dt}")
        return None

    out_name = f"ev_{camera_type}_{global_event_id}.mp4"
    out_path = os.path.join(CLIP_DIR, out_name)

    if len(segments) == 1:
        # Single segment: just trim with ss + t
        seg_start, seg_file = segments[0]
        offset = max((clip_start - seg_start).total_seconds(), 0)
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(offset),
            "-i", seg_file,
            "-t", str(total_dur),
            "-c", "copy",
            out_path,
        ]
    else:
        # Multiple segments: write concat list then trim
        concat_list = os.path.join(CLIP_DIR, f"concat_{global_event_id}_{camera_type}.txt")
        with open(concat_list, "w") as f:
            for _, seg_file in segments:
                f.write(f"file '{seg_file}'\n")

        first_seg_start = segments[0][0]
        offset = max((clip_start - first_seg_start).total_seconds(), 0)

        concat_tmp = os.path.join(CLIP_DIR, f"concat_tmp_{global_event_id}_{camera_type}.mp4")
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            concat_tmp,
        ]
        ret = subprocess.run(cmd_concat, capture_output=True)
        if ret.returncode != 0:
            logger.error(f"[CLIP] ffmpeg concat failed: {ret.stderr.decode()}")
            return None

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(offset),
            "-i", concat_tmp,
            "-t", str(total_dur),
            "-c", "copy",
            out_path,
        ]

    ret = subprocess.run(cmd, capture_output=True)
    if ret.returncode != 0:
        logger.error(f"[CLIP] ffmpeg trim failed: {ret.stderr.decode()}")
        return None

    logger.info(f"[CLIP] Created {out_path}")
    return out_path


# ──────────────────────────────────────────────
# SCREENSHOT
# ──────────────────────────────────────────────

def extract_first_frame(video_path: str, out_path: str) -> bool:
    """Extract first frame of video as JPEG screenshot using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        out_path,
    ]
    ret = subprocess.run(cmd, capture_output=True)
    if ret.returncode != 0:
        logger.error(f"[SCREENSHOT] ffmpeg failed: {ret.stderr.decode()}")
        return False
    logger.info(f"[SCREENSHOT] Saved {out_path}")
    return True


# ──────────────────────────────────────────────
# GOOGLE STORAGE UPLOAD
# ──────────────────────────────────────────────

async def _get_upload_url(session: aiohttp.ClientSession, token: str, file_name: str, content_type: str) -> str | None:
    """POST to backend to get a signed GCS upload URL."""
    url = f"{API_BASE_EVENT}/google-cloud-storage/upload-url"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"fileName": file_name, "contentType": content_type}
    async with session.post(url, json=payload, headers=headers) as resp:
        if resp.status != 200:
            text = await resp.text()
            logger.error(f"[UPLOAD_URL] Failed {resp.status}: {text}")
            return None
        data = await resp.json()
        # Adjust key based on actual API response shape
        return data.get("uploadUrl") or data.get("url")


async def _put_file_to_gcs(session: aiohttp.ClientSession, upload_url: str, file_path: str, content_type: str) -> bool:
    """PUT file bytes to Google Cloud Storage signed URL."""
    async with aiofiles.open(file_path, "rb") as f:
        data = await f.read()
    headers = {"Content-Type": content_type}
    async with session.put(upload_url, data=data, headers=headers) as resp:
        if resp.status not in (200, 201, 204):
            text = await resp.text()
            logger.error(f"[GCS PUT] Failed {resp.status}: {text}")
            return False
    return True


async def upload_file(session: aiohttp.ClientSession, token: str, local_path: str, is_video: bool) -> str | None:
    """
    Full upload cycle:
      1. POST → get signed URL + storage key
      2. PUT  → upload bytes to GCS
    Returns the storage key (used as insideVideoKey etc.) or None.
    """
    ext          = ".mp4" if is_video else ".jpg"
    content_type = "video/mp4" if is_video else "image/webp"
    file_name    = os.path.basename(local_path)

    # Step 1: get signed URL
    url          = f"{API_BASE_EVENT}/google-cloud-storage/upload-url"
    headers      = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload      = {"fileName": file_name, "contentType": content_type}

    async with session.post(url, json=payload, headers=headers) as resp:
        if resp.status != 200:
            logger.error(f"[UPLOAD] GET signed URL failed {resp.status}: {await resp.text()}")
            return None
        data       = await resp.json()
        upload_url = data.get("uploadUrl") or data.get("url")
        # The key returned by backend to reference this file later
        storage_key = data.get("key") or data.get("fileName") or file_name

    if not upload_url:
        logger.error("[UPLOAD] No uploadUrl in response")
        return None

    # Step 2: PUT to GCS
    async with aiofiles.open(local_path, "rb") as f:
        file_bytes = await f.read()

    async with session.put(upload_url, data=file_bytes, headers={"Content-Type": content_type}) as resp:
        if resp.status not in (200, 201, 204):
            logger.error(f"[GCS PUT] {resp.status}: {await resp.text()}")
            return None

    logger.info(f"[UPLOAD] Uploaded {local_path} → key: {storage_key}")
    return storage_key


# ──────────────────────────────────────────────
# BACKEND NOTIFY
# ──────────────────────────────────────────────

async def notify_backend(
    session: aiohttp.ClientSession,
    token: str,
    global_event_id: str,
    inside_video_key: str,
    outside_video_key: str,
    inside_screenshot_key: str,
    outside_screenshot_key: str,
) -> bool:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "globalEventId":        global_event_id,
        "insideVideoKey":       inside_video_key,
        "outsideVideoKey":      outside_video_key,
        "insideScreenshotKey":  inside_screenshot_key,
        "outsideScreenshotKey": outside_screenshot_key,
    }
    async with session.put(NOTIFY_URL, json=payload, headers=headers) as resp:
        if resp.status not in (200, 201, 204):
            logger.error(f"[NOTIFY] Failed {resp.status}: {await resp.text()}")
            return False
    logger.info(f"[NOTIFY] Backend notified for event {global_event_id}")
    return True


# ──────────────────────────────────────────────
# CLIP CREATION PASS  (called once per new event)
# ──────────────────────────────────────────────

# Max age: if event is older than this, segments are gone — skip it
CLIP_MAX_EVENT_AGE_MINUTES = 90

def create_clips_for_new_events():
    """
    Scan events table for events that don't have event_videos rows yet,
    cut clips for each, and insert into event_videos table.

    Events older than CLIP_MAX_EVENT_AGE_MINUTES are skipped — their
    segments are already gone from disk and will never be found.
    """
    with _db() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT e.id, e.globalEventId, e.eventType, e.deviceDateTime
            FROM events e
            WHERE NOT EXISTS (
                SELECT 1 FROM event_videos ev
                WHERE ev.globalEventId = e.globalEventId
            )
            ORDER BY e.id ASC
            LIMIT 20
        """)
        events = c.fetchall()

    now = datetime.now()

    for ev in events:
        global_event_id = ev["globalEventId"]
        event_type      = ev["eventType"]
        device_dt_str   = ev["deviceDateTime"]

        try:
            # Parse deviceDateTime — handle both with/without timezone
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
                try:
                    event_dt = datetime.strptime(device_dt_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                logger.error(f"[CLIP_CREATE] Cannot parse deviceDateTime: {device_dt_str}")
                continue

            # Remove tz for local file matching
            event_dt_local = event_dt.replace(tzinfo=None) if event_dt.tzinfo else event_dt

            # Skip events older than max age — segments are gone from disk
            age_minutes = (now - event_dt_local).total_seconds() / 60
            if age_minutes > CLIP_MAX_EVENT_AGE_MINUTES:
                logger.warning(
                    f"[CLIP_CREATE] Skipping old event {global_event_id} "
                    f"(age={age_minutes:.1f} min > {CLIP_MAX_EVENT_AGE_MINUTES} min), segments gone."
                )
                # Mark as uploaded=1 directly so this event is never retried
                for cam in ("inner", "front"):
                    with _db() as conn:
                        conn.execute("""
                            INSERT OR IGNORE INTO event_videos
                                (file_path, camera_type, deviceDateTime, globalEventId, uploaded)
                            VALUES (?, ?, ?, ?, 1)
                        """, ("__skipped__", cam, device_dt_str, global_event_id))
                        conn.commit()
                continue

            before_sec, after_sec = _get_event_window(event_type)

            for cam in ("inner", "front"):
                clip_path = cut_event_clip(cam, event_dt_local, before_sec, after_sec, global_event_id)
                if clip_path:
                    insert_event_video(clip_path, cam, device_dt_str, global_event_id)
                    logger.info(f"[CLIP_CREATE] Inserted event_video: {cam} for {global_event_id}")
                else:
                    logger.warning(f"[CLIP_CREATE] Clip not created for {cam} / {global_event_id}")

        except Exception as e:
            logger.exception(f"[CLIP_CREATE] Error processing event {global_event_id}: {e}")


# ──────────────────────────────────────────────
# UPLOAD PASS  (uploads ready clips → notifies backend)
# ──────────────────────────────────────────────

async def upload_event_media_pass():
    """
    For each globalEventId that has BOTH inner + front clips ready,
    upload all 4 files (2 videos + 2 screenshots) then notify backend.
    """
    groups = get_pending_event_groups(limit=5)
    if not groups:
        return

    token = get_valid_token()
    if not token:
        logger.error("[UPLOAD_PASS] No valid token, skipping.")
        return

    async with aiohttp.ClientSession() as session:
        for group in groups:
            geid         = group["globalEventId"]
            inner_video  = group["inner_video"]
            front_video  = group["front_video"]

            # Both clips must exist
            if not inner_video or not front_video:
                logger.info(f"[UPLOAD_PASS] Waiting for both clips: {geid}")
                continue

            if not os.path.exists(inner_video) or not os.path.exists(front_video):
                logger.warning(f"[UPLOAD_PASS] Clip file missing on disk for {geid}")
                increment_event_video_retry(geid)
                continue

            try:
                # ── Screenshots ──────────────────────────────
                inner_ss_path = inner_video.replace(".mp4", "_ss.webp")
                front_ss_path = front_video.replace(".mp4", "_ss.webp")

                inner_ss_ok = extract_first_frame(inner_video, inner_ss_path)
                front_ss_ok = extract_first_frame(front_video, front_ss_path)

                if not inner_ss_ok or not front_ss_ok:
                    logger.error(f"[UPLOAD_PASS] Screenshot failed for {geid}")
                    increment_event_video_retry(geid)
                    continue

                # ── Upload all 4 ─────────────────────────────
                inside_video_key       = await upload_file(session, token, inner_video,  is_video=True)
                outside_video_key      = await upload_file(session, token, front_video,  is_video=True)
                inside_screenshot_key  = await upload_file(session, token, inner_ss_path, is_video=False)
                outside_screenshot_key = await upload_file(session, token, front_ss_path, is_video=False)

                if not all([inside_video_key, outside_video_key,
                            inside_screenshot_key, outside_screenshot_key]):
                    logger.error(f"[UPLOAD_PASS] One or more uploads failed for {geid}")
                    increment_event_video_retry(geid)
                    continue

                # ── Notify backend ────────────────────────────
                ok = await notify_backend(
                    session, token, geid,
                    inside_video_key, outside_video_key,
                    inside_screenshot_key, outside_screenshot_key,
                )

                if ok:
                    mark_event_video_uploaded(geid)
                    logger.info(f"[UPLOAD_PASS] Done: {geid}")
                    # Optional: delete local clip + screenshot files to save space
                    for p in [inner_video, front_video, inner_ss_path, front_ss_path]:
                        try:
                            os.remove(p)
                        except Exception:
                            pass
                else:
                    increment_event_video_retry(geid)

            except Exception as e:
                logger.exception(f"[UPLOAD_PASS] Unexpected error for {geid}: {e}")
                increment_event_video_retry(geid)

async def event_video_uploader_loop():
    """Main loop: runs forever, polls for new events and uploads ready clips."""
    logger.info("[EVENT_VIDEO_UPLOADER] Starting loop...")
    while True:
        try:
            create_clips_for_new_events()

            # Phase 2: upload clips that are ready
            await upload_event_media_pass()

        except Exception as e:
            logger.exception(f"[EVENT_VIDEO_UPLOADER] Loop error: {e}")

        await asyncio.sleep(POLL_INTERVAL)
