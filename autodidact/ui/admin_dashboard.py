import sys
import os
import streamlit as st
import pandas as pd
import chromadb
import warnings
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Suppress pandas SQLAlchemy warning (we're using psycopg2 directly)
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autodidact.database import database_utils

# --- Page Configuration ---
st.set_page_config(
    page_title="Autodidact AI - Admin Dashboard",
    page_icon="🎓",
    layout="wide"
)

# --- Sidebar Navigation ---
st.sidebar.title("🎓 Autodidact AI")

# Cache clearing button
if st.sidebar.button("🔄 Clear Cache", help="Clear cached data and refresh queries"):
    st.cache_data.clear()
    st.sidebar.success("✅ Cache cleared!")
    st.rerun()

st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["🔍 ChromaDB Explorer", "📋 Video Review Queue"],
    index=0
)
st.sidebar.markdown("---")
st.sidebar.caption("Admin Dashboard v1.0")

# ============================================================================
# PAGE 1: ChromaDB Explorer
# ============================================================================
if page == "🔍 ChromaDB Explorer":
    st.title("🔬 ChromaDB Content Explorer")
    st.caption("An interface to search and analyze the contents of your vector database.")

    @st.cache_resource
    def get_chroma_client():
        """Get a cached ChromaDB client."""
        try:
            client = chromadb.HttpClient(
                host=os.getenv("CHROMADB_HOST", "localhost"), 
                port=int(os.getenv("CHROMADB_PORT", 8000))
            )
            client.heartbeat()
            return client
        except Exception as e:
            st.error(f"Failed to connect to ChromaDB: {e}")
            st.info("Please ensure ChromaDB is running and accessible at the configured host and port.")
            return None

    client = get_chroma_client()

    if client:
        try:
            collections = client.list_collections()
            collection_names = [c.name for c in collections]
            
            if not collection_names:
                st.warning("No collections found in ChromaDB.")
            else:
                selected_collection_name = st.selectbox("Select a Collection", collection_names)
                
                if selected_collection_name:
                    collection = client.get_collection(selected_collection_name)

                    tab1, tab2 = st.tabs(["🔍 Semantic Search", "📊 Database Analytics"])

                    # --- Search Tab ---
                    with tab1:
                        st.header("Search for Content")
                        query_text = st.text_input("Enter a search query:", placeholder="e.g., 'advanced techniques for machine learning'")
                        n_results = st.slider("Number of results to retrieve", 1, 50, 10)

                        if st.button("Search", use_container_width=True):
                            if query_text:
                                with st.spinner("Searching..."):
                                    results = collection.query(
                                        query_texts=[query_text],
                                        n_results=n_results,
                                        include=["metadatas", "documents", "distances"]
                                    )
                                    
                                    st.subheader(f"Found {len(results['documents'][0])} results")
                                    for i, doc in enumerate(results['documents'][0]):
                                        with st.container(border=True):
                                            st.markdown(f"**Result {i+1}** | **Distance:** `{results['distances'][0][i]:.4f}`")
                                            st.info(doc)
                                            st.write("**Metadata:**")
                                            st.json(results['metadatas'][0][i], expanded=False)
                            else:
                                st.warning("Please enter a query.")

                    # --- Analytics Tab ---
                    with tab2:
                        st.header("Collection Analytics")
                        with st.spinner("Loading analytics..."):
                            all_data = collection.get(include=["metadatas"])
                            
                            if not all_data['ids']:
                                st.warning("The selected collection is empty.")
                            else:
                                df = pd.DataFrame(all_data['metadatas'])
                                
                                st.metric("Total Documents in Collection", len(df))
                                
                                if 'domain_id' in df.columns:
                                    st.write("#### Documents per Domain")
                                    st.bar_chart(df['domain_id'].value_counts())
                                
                                if 'platform' in df.columns:
                                    st.write("#### Documents by Source Platform")
                                    st.bar_chart(df['platform'].value_counts())

                                st.write("---")
                                st.write("#### Raw Metadata Explorer")
                                st.dataframe(df)

        except Exception as e:
            st.error(f"An error occurred while interacting with the collection: {e}")

# ============================================================================
# PAGE 2: Video Review Queue
# ============================================================================
elif page == "📋 Video Review Queue":
    st.title("🎬 Video Manual Review Queue")
    st.caption("Review and approve videos that were flagged by the quality scorer.")

    @st.cache_data(ttl=300)
    def get_pending_videos():
        """Fetches videos with 'pending_review' status along with channel info and metadata."""
        query = """
            SELECT 
                v.video_id,
                v.video_url,
                v.title,
                v.status,
                v.quality_score,
                v.rejection_reason,
                c.channel_name,
                c.channel_url
            FROM videos v
            LEFT JOIN channels c ON v.channel_id = c.id
            WHERE v.status = 'pending_review'
            ORDER BY v.retrieval_date DESC;
        """
        conn = database_utils.get_db_connection()
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    def get_video_metadata(video_id: str) -> dict:
        """Fetch additional metadata for a video from GCS (fast) or database."""
        # Try GCS first (instant, no API calls)
        try:
            from src.storage.gcs_manager import retrieve_video_from_gcs
            
            transcript, metadata = retrieve_video_from_gcs(video_id)
            if metadata:
                # GCS has full metadata from scraping
                # Handle both old and new field names
                return {
                    'upload_date': metadata.get('upload_date') or metadata.get('published_at'),
                    'retrieval_date': metadata.get('retrieval_date'),
                    'view_count': metadata.get('view_count') or metadata.get('views', 0) or 0,
                    'like_count': metadata.get('like_count') or metadata.get('likes', 0) or 0,
                    'comment_count': metadata.get('comment_count') or metadata.get('comments', 0) or 0,
                    'duration_seconds': metadata.get('duration_seconds') or metadata.get('video_length_seconds', 0) or 0,
                    'subscriber_count': metadata.get('subscriber_count', 0) or 0,
                    'is_verified': metadata.get('is_verified', False),
                    'from_gcs': True  # Flag to show we used cache
                }
        except Exception as e:
            st.caption(f"⚠️ GCS not available: {e}")
        
        # Fallback: get from database
        conn = database_utils.get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        v.upload_date,
                        v.retrieval_date
                    FROM videos v
                    WHERE v.video_id = %s
                """, (video_id,))
                
                row = cur.fetchone()
                if row:
                    return {
                        'upload_date': row[0],
                        'retrieval_date': row[1],
                        'view_count': 0,
                        'like_count': 0,
                        'comment_count': 0,
                        'duration_seconds': 0,
                        'subscriber_count': 0,
                        'is_verified': False,
                        'from_gcs': False
                    }
                return {
                    'from_gcs': False
                }
        finally:
            conn.close()

    def update_status_callback(video_id, new_status, notes=""):
        """Callback to update video status in the database and queue for ingestion if approved."""
        conn = database_utils.get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE videos SET status = %s, reviewer_notes = %s WHERE video_id = %s",
                    (new_status, notes, video_id)
                )
            conn.commit()
            st.toast(f"Video {video_id} status updated to '{new_status}'!", icon="🎉")
            
            # 🚀 NEW: Auto-queue approved videos for ingestion
            if new_status == 'approved':
                try:
                    queue_approved_video_for_ingestion(video_id)
                    st.toast(f"Video {video_id} queued for ingestion!", icon="✅")
                except Exception as e:
                    st.error(f"Failed to queue video for ingestion: {e}")
                    st.info("You can manually queue it with: `python scripts/queue_approved_video.py {video_id}`")
        finally:
            conn.close()
        st.cache_data.clear()
    
    def queue_approved_video_for_ingestion(video_id: str):
        """Queue an approved video for ingestion into ChromaDB."""
        import json
        import pika
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Get video data from database
        conn = database_utils.get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        v.video_id, 
                        v.video_url, 
                        v.title, 
                        v.quality_score,
                        c.channel_name,
                        c.channel_url
                    FROM videos v
                    JOIN channels c ON v.channel_id = c.id
                    WHERE v.video_id = %s AND v.status = 'approved'
                """, (video_id,))
                
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Video {video_id} not found or not approved")
                
                video_data = {
                    'video_id': row[0],
                    'video_url': row[1],
                    'title': row[2],
                    'quality_score': float(row[3]) if row[3] else None,
                    'channel_name': row[4],
                    'channel_url': row[5],
                }
        finally:
            conn.close()
        
        # Get transcript using Apify
        from src.scrapers.youtube_transcript_fetcher import get_youtube_transcript
        
        content, metadata = get_youtube_transcript(video_data['video_url'], scraper='apify')
        
        if not content:
            raise ValueError(f"Could not fetch transcript for {video_id}")
        
        # Enrich metadata
        enriched_metadata = {
            'quality_score': video_data['quality_score'],
            'domain_id': 'UNCATEGORIZED',
            'subdomain_id': None,
            'source': video_data['video_url'],
            'platform': 'youtube',
            'content_type': 'video',
            'difficulty': 'intermediate',
            'helpfulness_score': video_data['quality_score'] or 0.5,
            'text_length': len(content),
            'title': metadata.get('title'),
            'author': metadata.get('channel_name'),
            'channel_id': metadata.get('channel_id'),
            'channel_url': metadata.get('channel_url'),
            'video_id': metadata.get('video_id'),
            'views': metadata.get('views', 0),
            'video_length_seconds': metadata.get('video_length_seconds', 0),
            'language': metadata.get('language', 'en'),
        }
        
        # Prepare message for ingestion queue
        message = {
            'youtube_url': video_data['video_url'],
            'content': content,
            'metadata': enriched_metadata,
            'video_id': video_id,
        }
        
        # Connect to RabbitMQ
        credentials = pika.PlainCredentials(
            os.getenv('RABBITMQ_USER', 'autodidact'),
            os.getenv('RABBITMQ_PASSWORD', 'rabbitmq_password')
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                os.getenv('RABBITMQ_HOST', 'localhost'),
                credentials=credentials
            )
        )
        channel = connection.channel()
        
        # Publish to validation queue (which feeds into embedding)
        channel.basic_publish(
            exchange='',
            routing_key='tasks.video.validated',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json',
            )
        )
        
        connection.close()

    # Main review interface
    st.header("Videos Awaiting Manual Approval")

    pending_videos_df = get_pending_videos()

    if pending_videos_df.empty:
        st.success("No videos are currently pending review. Great job! ✨")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"Found **{len(pending_videos_df)}** videos to review.")
        with col2:
            if st.button("🚀 Approve & Queue All", use_container_width=True, type="primary"):
                with st.spinner("Approving and queueing all videos..."):
                    success_count = 0
                    fail_count = 0
                    for _, video in pending_videos_df.iterrows():
                        try:
                            update_status_callback(video['video_id'], 'approved', "Batch approved")
                            success_count += 1
                        except Exception as e:
                            fail_count += 1
                            st.error(f"Failed to process {video['video_id']}: {e}")
                    
                    if success_count > 0:
                        st.success(f"✅ Successfully approved and queued {success_count} videos!")
                    if fail_count > 0:
                        st.warning(f"⚠️ Failed to process {fail_count} videos.")
                    st.rerun()

        for index, video in pending_videos_df.iterrows():
            # Get additional metadata (including fresh YouTube data)
            metadata = get_video_metadata(video['video_id'])
            
            # Extract metadata values
            subscriber_count = metadata.get('subscriber_count', 0)
            is_verified = metadata.get('is_verified', False)
            view_count = metadata.get('view_count', 0)
            like_count = metadata.get('like_count', 0)
            comment_count = metadata.get('comment_count', 0)
            duration_seconds = metadata.get('duration_seconds', 0)
            upload_date = metadata.get('upload_date')
            retrieval_date = metadata.get('retrieval_date')
            
            with st.container(border=True):
                # Header with title and channel
                st.subheader(f"📹 {video['title']}")
                
                # Channel info with verification badge
                channel_text = f"[{video['channel_name']}]({video['channel_url']})"
                if is_verified:
                    channel_text += " ✓"
                st.caption(f"Channel: {channel_text}")
                
                # Create tabs for better organization
                tab1, tab2, tab3 = st.tabs(["📹 Video", "📊 Quality Analysis", "🔍 Metadata"])
                
                # TAB 1: Video Player
                with tab1:
                    st.video(video['video_url'])
                
                # TAB 2: Quality Analysis
                with tab2:
                    # Overall score with color coding
                    score = video['quality_score']
                    if score:
                        if score >= 0.8:
                            score_color = "🌟"
                            score_label = "Excellent"
                        elif score >= 0.7:
                            score_color = "🟢"
                            score_label = "Good"
                        elif score >= 0.5:
                            score_color = "🟡"
                            score_label = "Medium"
                        elif score >= 0.3:
                            score_color = "🟠"
                            score_label = "Low"
                        else:
                            score_color = "🔴"
                            score_label = "Very Low"
                        
                        st.metric(
                            label="Overall Quality Score",
                            value=f"{score:.3f}",
                            delta=f"{score_label} {score_color}"
                        )
                    else:
                        st.metric(label="Overall Quality Score", value="N/A")
                    
                    st.divider()
                    
                    # Rejection reason
                    st.warning("**Why It Was Flagged:**")
                    st.markdown(f"> {video['rejection_reason']}")
                    
                    st.divider()
                    
                    # Estimated quality factors breakdown
                    st.write("**Estimated Quality Factors:**")
                    st.caption("_Based on available metadata. Actual scoring uses more detailed analysis._")
                    
                    # Calculate estimated scores
                    import math
                    
                    # Authority score (based on subscribers)
                    if subscriber_count > 0:
                        authority_score = min(1.0, math.log10(subscriber_count) / 6.5)
                    else:
                        authority_score = 0.0
                    
                    # Engagement score (based on likes/views ratio)
                    if view_count > 0 and like_count > 0:
                        like_ratio = like_count / view_count
                        engagement_score = min(1.0, like_ratio * 50)  # ~2% like ratio = good
                    else:
                        engagement_score = 0.0
                    
                    # Freshness score (based on upload date)
                    if upload_date:
                        from datetime import datetime, timedelta
                        try:
                            if isinstance(upload_date, str):
                                upload_date = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
                            age_days = (datetime.now(upload_date.tzinfo) - upload_date).days
                            if age_days <= 30:
                                freshness_score = 1.0
                            elif age_days <= 180:
                                freshness_score = 0.8
                            elif age_days <= 365:
                                freshness_score = 0.6
                            elif age_days <= 730:
                                freshness_score = 0.4
                            else:
                                freshness_score = 0.2
                        except:
                            freshness_score = 0.5
                    else:
                        freshness_score = 0.5
                    
                    # Display breakdown
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Authority (25%)",
                            f"{authority_score:.2f}",
                            help=f"Based on {subscriber_count:,} subscribers"
                        )
                    
                    with col2:
                        st.metric(
                            "Engagement (20%)",
                            f"{engagement_score:.2f}",
                            help=f"Based on {like_count:,} likes / {view_count:,} views"
                        )
                    
                    with col3:
                        st.metric(
                            "Freshness (15%)",
                            f"{freshness_score:.2f}",
                            help=f"Based on upload date"
                        )
                    
                    st.caption("_Note: Relevance (30%) and Completeness (10%) require transcript analysis._")
                
                # TAB 3: Detailed Metadata
                with tab3:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Channel Metrics:**")
                        st.write(f"• Subscribers: {subscriber_count:,}")
                        st.write(f"• Verified: {'Yes ✓' if is_verified else 'No'}")
                        
                        st.write("")
                        st.write("**Engagement Metrics:**")
                        st.write(f"• Views: {view_count:,}")
                        st.write(f"• Likes: {like_count:,}")
                        st.write(f"• Comments: {comment_count:,}")
                        if view_count > 0:
                            like_ratio = (like_count / view_count * 100) if like_count else 0
                            st.write(f"• Like ratio: {like_ratio:.2f}%")
                    
                    with col2:
                        st.write("**Video Details:**")
                        if duration_seconds:
                            minutes = duration_seconds // 60
                            seconds = duration_seconds % 60
                            st.write(f"• Duration: {minutes}m {seconds}s")
                        else:
                            st.write(f"• Duration: Unknown")
                        
                        if upload_date:
                            st.write(f"• Upload date: {upload_date}")
                        
                        if retrieval_date:
                            st.write(f"• Indexed: {retrieval_date}")
                        
                        st.write(f"• Video ID: `{video['video_id']}`")
                
                # Action section (below tabs)
                st.divider()
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    notes = st.text_area(
                        "Reviewer Notes",
                        key=f"notes_{video['video_id']}",
                        height=80,
                        placeholder="Optional notes about your decision..."
                    )
                
                with col2:
                    st.button(
                        "✅ Approve & Queue",
                        key=f"approve_{video['video_id']}",
                        on_click=update_status_callback,
                        args=(video['video_id'], 'approved', notes),
                        use_container_width=True,
                        type="primary"
                    )
                
                with col3:
                    st.button(
                        "❌ Reject",
                        key=f"reject_{video['video_id']}",
                        on_click=update_status_callback,
                        args=(video['video_id'], 'rejected', notes),
                        use_container_width=True
                    )
            
            st.divider()
