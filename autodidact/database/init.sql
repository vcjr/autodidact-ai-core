-- Create a table for YouTube channels to avoid data duplication
CREATE TABLE channels (
    id SERIAL PRIMARY KEY,
    channel_id VARCHAR(255) UNIQUE NOT NULL,
    channel_name VARCHAR(255),
    channel_url TEXT,
    -- You can add more channel-specific metadata here later, like subscriber count
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create a table for YouTube playlists
CREATE TABLE playlists (
    id SERIAL PRIMARY KEY,
    playlist_id VARCHAR(255) UNIQUE NOT NULL,
    playlist_title TEXT,
    playlist_url TEXT,
    channel_id INTEGER REFERENCES channels(id) ON DELETE SET NULL,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Update the videos table to link to a channel
CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(255) UNIQUE NOT NULL,
    video_url TEXT NOT NULL,
    title TEXT,
    -- Link to the channels table
    channel_id INTEGER REFERENCES channels(id) ON DELETE CASCADE,
    upload_date TIMESTAMP,
    retrieval_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'scraped', -- e.g., 'scraped', 'pending_review', 'approved', 'ingested', 'rejected'
    quality_score FLOAT,
    rejection_reason TEXT,
    reviewer_notes TEXT
);

-- Create a join table for the many-to-many relationship between playlists and videos
CREATE TABLE playlist_videos (
    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
    video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
    position_in_playlist INTEGER, -- The video's position in the playlist
    PRIMARY KEY (playlist_id, video_id)
);

-- Create indexes for faster queries
CREATE INDEX idx_videos_status ON videos (status);
CREATE INDEX idx_videos_channel_id ON videos (channel_id);
CREATE INDEX idx_playlists_channel_id ON playlists (channel_id);
