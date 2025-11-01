import sys
import os
import streamlit as st
import pandas as pd
import chromadb

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
        """Fetches videos with 'pending_review' status along with channel info."""
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

    def update_status_callback(video_id, new_status, notes=""):
        """Callback to update video status in the database."""
        conn = database_utils.get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE videos SET status = %s, reviewer_notes = %s WHERE video_id = %s",
                    (new_status, notes, video_id)
                )
            conn.commit()
            st.toast(f"Video {video_id} status updated to '{new_status}'!", icon="🎉")
        finally:
            conn.close()
        st.cache_data.clear()

    # Main review interface
    st.header("Videos Awaiting Manual Approval")

    pending_videos_df = get_pending_videos()

    if pending_videos_df.empty:
        st.success("No videos are currently pending review. Great job! ✨")
    else:
        st.info(f"Found **{len(pending_videos_df)}** videos to review.")

        for index, video in pending_videos_df.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader(video['title'])
                    st.caption(f"Channel: [{video['channel_name']}]({video['channel_url']})")
                    st.video(video['video_url'])

                with col2:
                    st.warning(f"**Automated Rejection Reason:**")
                    st.markdown(f"> {video['rejection_reason']}")
                    st.metric(label="Quality Score", value=f"{video['quality_score']:.2f}" if video['quality_score'] else "N/A")
                    
                    notes = st.text_area("Reviewer Notes", key=f"notes_{video['video_id']}", height=100)

                    action_col1, action_col2 = st.columns(2)
                    with action_col1:
                        st.button(
                            "✅ Approve", 
                            key=f"approve_{video['video_id']}", 
                            on_click=update_status_callback, 
                            args=(video['video_id'], 'approved', notes),
                            use_container_width=True
                        )
                    with action_col2:
                        st.button(
                            "❌ Reject", 
                            key=f"reject_{video['video_id']}", 
                            on_click=update_status_callback, 
                            args=(video['video_id'], 'rejected', notes),
                            use_container_width=True
                        )
            st.divider()
