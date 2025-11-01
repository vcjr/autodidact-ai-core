import os
import psycopg2
from psycopg2.extras import DictCursor

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "video_metadata"),
        user=os.getenv("POSTGRES_USER", "autodidact"),
        password=os.getenv("POSTGRES_PASSWORD", "password")
    )
    return conn

def log_channel_and_video(video_data):
    """
    Logs the channel first, then logs the video, linking it with the channel's foreign key.
    This is done in a single transaction to ensure atomicity.
    """
    
    # Handle missing channel_id - use channel_name as fallback or generate one
    channel_id = video_data.get('channel_id')
    if not channel_id:
        channel_name = video_data.get('channel_name', 'Unknown')
        # Generate a channel_id from channel_name
        channel_id = f"channel_{channel_name.replace(' ', '_').lower()}"
    
    channel_sql = """
        INSERT INTO channels (channel_id, channel_name, channel_url)
        VALUES (%s, %s, %s)
        ON CONFLICT (channel_id) DO UPDATE SET channel_name = EXCLUDED.channel_name
        RETURNING id;
    """
    
    video_sql = """
        INSERT INTO videos (video_id, video_url, title, channel_id, upload_date, status)
        VALUES (%s, %s, %s, %s, %s, 'scraped')
        ON CONFLICT (video_id) DO NOTHING;
    """
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Upsert channel and get its ID
            cur.execute(channel_sql, (
                channel_id,
                video_data.get('channel_name'),
                video_data.get('channel_url')
            ))
            channel_db_id_tuple = cur.fetchone()
            if not channel_db_id_tuple:
                # If ON CONFLICT DO UPDATE happened on a concurrent transaction, 
                # the RETURNING clause might not return a value. We fetch the id to be safe.
                cur.execute("SELECT id FROM channels WHERE channel_id = %s", (channel_id,))
                channel_db_id_tuple = cur.fetchone()
            
            channel_db_id = channel_db_id_tuple[0]
            
            # Insert video linked to the channel
            # Try 'source_url' first (from Apify), fallback to 'url' for backward compatibility
            video_url = video_data.get('source_url') or video_data.get('url')
            
            cur.execute(video_sql, (
                video_data['video_id'],
                video_url,
                video_data.get('title'),
                channel_db_id,
                video_data.get('upload_date')
            ))
        conn.commit()
    except (Exception, psycopg2.Error) as e:
        print(f"Database error: {e}")
        conn.rollback()
        raise  # Re-raise to propagate the error
    finally:
        conn.close()


def update_video_status(video_id, status, score=None, reason=None):
    """Updates the status, quality score, and reason for a video."""
    sql = "UPDATE videos SET status = %s, quality_score = %s, rejection_reason = %s WHERE video_id = %s;"
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (status, score, reason, video_id))
        conn.commit()
    finally:
        conn.close()
