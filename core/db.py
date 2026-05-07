import os, sqlite3
from core.config import DB_PATH
from datetime import datetime, timedelta, timezone

def init_db():
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            camera_type TEXT,
            start_time TEXT,
            end_time TEXT,
            globalVideoId TEXT,
            uploaded INTEGER DEFAULT 0,
            retries INTEGER DEFAULT 0,
            last_try TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            globalEventId TEXT NOT NULL,
            event TEXT NOT NULL,
            eventType TEXT NOT NULL,
            status TEXT,
            deviceDateTime TEXT,
            latitude REAL,
            longitude REAL,
            distance REAL,
            state TEXT,
            location TEXT,
            direction TEXT,
            fuelLevelPercent INTEGER,
            defLevelPercent INTEGER,
            speed INTEGER,
            detectedCameraType TEXT,
            uploaded INTEGER DEFAULT 0,
            retries INTEGER DEFAULT 0,
            last_try TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS event_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            camera_type TEXT,
            deviceDateTime TEXT,
            globalEventId TEXT,
            uploaded INTEGER DEFAULT 0,
            retries INTEGER DEFAULT 0,
            last_try TIMESTAMP
        )
        """)

        c.execute("PRAGMA table_info(videos)")
        video_columns = {row[1] for row in c.fetchall()}
        if "last_try" not in video_columns:
            c.execute("ALTER TABLE videos ADD COLUMN last_try TIMESTAMP")

        c.execute("PRAGMA table_info(events)")
        event_columns = {row[1] for row in c.fetchall()}
        if "last_try" not in event_columns:
            c.execute("ALTER TABLE events ADD COLUMN last_try TIMESTAMP")
        
        c.execute("PRAGMA table_info(event_videos)")
        event_columns = {row[1] for row in c.fetchall()}
        if "last_try" not in event_columns:
            c.execute("ALTER TABLE event_videos ADD COLUMN last_try TIMESTAMP")

        c.execute("CREATE INDEX IF NOT EXISTS idx_videos_uploaded_last_try ON videos(uploaded, last_try, start_time)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_uploaded_last_try ON events(uploaded, last_try, deviceDateTime)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_event_videos_uploaded_last_try ON event_videos(uploaded, last_try, deviceDateTime)")
        c.execute("PRAGMA auto_vacuum = FULL;")
        conn.commit()

# ==================== VIDEO FUNCTIONS ====================

def insert_video(file_path, camera_type, start_time, end_time, globalVideoId):
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO videos
            (file_path, camera_type, start_time, end_time, globalVideoId, uploaded)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (file_path, camera_type, start_time, end_time, globalVideoId))
        conn.commit()
        return c.lastrowid

def video_exists(file_path):
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM videos WHERE file_path = ? LIMIT 1", (file_path,))
        return c.fetchone() is not None

def get_unuploaded_videos(limit=10, min_age_seconds=2, retry_interval=15, newest_first=True):
    """
    Fetch unuploaded videos from DB.

    newest_first=True  → upload recent videos first (default).
                         When internet was lost for hours, this keeps
                         the live feed as up-to-date as possible while
                         older videos are caught up in the background.
    newest_first=False → oldest-first (FIFO) order.

    No video is ever dropped: every row will eventually be retried
    until uploaded=1 or retries exceed the cleanup threshold.
    """
    order = "DESC" if newest_first else "ASC"
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        # Use naive local time to match start_time format in DB (no timezone suffix)
        threshold_time = (datetime.now() - timedelta(seconds=min_age_seconds)).strftime('%Y-%m-%dT%H:%M:%S')
        retry_threshold = (datetime.now() - timedelta(seconds=retry_interval)).strftime('%Y-%m-%dT%H:%M:%S')
        c.execute(f"""
            SELECT id, file_path, camera_type, start_time, end_time, globalVideoId
            FROM videos
            WHERE uploaded = 0
              AND start_time < ?
              AND (last_try IS NULL OR last_try < ?)
            ORDER BY start_time {order}
            LIMIT ?
        """, (threshold_time, retry_threshold, limit))
        return c.fetchall()

def mark_uploaded(video_id):
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        conn.execute("UPDATE videos SET uploaded=1 WHERE id=?", (video_id,))
        conn.commit()

def increment_retry(video_id):
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        conn.execute("""
            UPDATE videos
            SET retries = retries + 1,
                last_try = ?
            WHERE id=?
        """, (datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), video_id))
        conn.commit()

# ==================== EVENT FUNCTIONS ====================

def insert_event(event_data: dict):
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO events (
                globalEventId, event, eventType, status, deviceDateTime,
                latitude, longitude, distance, state, location,
                direction, fuelLevelPercent, defLevelPercent, speed,
                detectedCameraType, uploaded, retries
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
        """, (
            event_data["globalEventId"],
            event_data["event"],
            event_data["eventType"],
            event_data["status"],
            event_data["deviceDateTime"],
            event_data["latitude"],
            event_data["longitude"],
            event_data["distance"],
            event_data["state"],
            event_data["location"],
            event_data["direction"],
            event_data["fuelLevelPercent"],
            event_data["defLevelPercent"],
            event_data["speed"],
            event_data["detectedCameraType"],
        ))
        conn.commit()
        return c.lastrowid

def get_unuploaded_events(limit=20, min_age_seconds=2, retry_interval=15):
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        threshold_time = (datetime.now(timezone.utc) - timedelta(seconds=min_age_seconds)).isoformat()
        retry_threshold = (datetime.now(timezone.utc) - timedelta(seconds=retry_interval)).isoformat()
        c.execute("""
            SELECT *
            FROM events
            WHERE uploaded = 0
              AND deviceDateTime < ?
              AND (last_try IS NULL OR last_try < ?)
            ORDER BY id ASC
            LIMIT ?
        """, (threshold_time, retry_threshold, limit))
        return c.fetchall()

def mark_event_uploaded(event_id):
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        conn.execute("UPDATE events SET uploaded=1 WHERE id=?", (event_id,))
        conn.commit()

def increment_event_retry(event_id):
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        conn.execute("""
            UPDATE events
            SET retries = retries + 1,
                last_try = ?
            WHERE id=?
        """, (datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), event_id))
        conn.commit()

def get_upload_backlog_counts():
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM videos WHERE uploaded = 0")
        pending_videos = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM events WHERE uploaded = 0")
        pending_events = c.fetchone()[0]
        return {
            "pending_videos": pending_videos,
            "pending_events": pending_events,
        }

def delete_old_videos(MAX_VIDEO_AGE_HOURS):
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=MAX_VIDEO_AGE_HOURS)
    cutoff_iso = cutoff_time.isoformat()

    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, file_path FROM videos
            WHERE datetime(start_time) < ?
            AND (
                uploaded = 1
                OR (uploaded = 0 AND retries > 50)
            )
        """, (cutoff_iso,))
        old_videos = c.fetchall()

        for vid_id, file_path in old_videos:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"[CLEANUP] Deleted old video file: {file_path}")
                c.execute("DELETE FROM videos WHERE id=?", (vid_id,))
                print(f"[CLEANUP] Removed from DB: video_id={vid_id}")
            except Exception as e:
                print(f"[CLEANUP ERROR] {e}")

        conn.commit()

def delete_old_events(MAX_EVENT_AGE_HOURS):
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=MAX_EVENT_AGE_HOURS)
    cutoff_iso = cutoff_time.isoformat()

    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("""
            DELETE FROM events
            WHERE datetime(deviceDateTime) < ?
            AND (
                uploaded = 1
                OR (uploaded = 0 AND retries > 50)
            )
        """, (cutoff_iso,))
        deleted = c.rowcount
        conn.commit()

    if deleted:
        print(f"[EVENT CLEANUP] {deleted} old events deleted from DB.")
