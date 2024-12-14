from flask_pymongo import PyMongo
from datetime import datetime
import json
import logging
import uuid

# Initialize PyMongo (MongoDB client)
mongo = None

def init_db(app):
    global mongo
    mongo = PyMongo(app)  # Initialize PyMongo with the app
    # Ensure the video collection is available in MongoDB
    mongo.db.videos.create_index([('video_url', 1)], unique=True)


# Video class with new fields
class Video:
    def __init__(self, video_url, segment_length, file_urls, processed_video_url=None, segments=None, script=None, status="processing"):
        # Constructor to initialize the video object with video_url, segment_length, and file_urls
        self.video_url = video_url  # URL or path to the generated video
        self.segment_length = segment_length  # Length of each segment in seconds
        self.file_urls = file_urls  # JSON list of file URLs of video segments
        self.processed_video_url = processed_video_url  # URL of the processed video
        self.segments = segments if segments else []  # List of segments (URLs or metadata)
        self.script = script  # Script or description of the video
        self.video_length = segment_length  # Video length in seconds
        self.status = status  # Video status, default is "processing"
        self.created_at = datetime.utcnow()  # Timestamp of video creation

    def to_dict(self):
        """Helper method to convert Video object to dictionary"""
        return {
            'video_url': self.video_url,
            'segment_length': self.segment_length,
            'file_urls': json.loads(self.file_urls) if isinstance(self.file_urls, str) else self.file_urls,
            'processed_video_url': self.processed_video_url,
            'segments': self.segments,
            'script': self.script,
            'video_length': self.video_length,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

# Function to save the video to MongoDB
def save_video(video_url, segment_length, file_urls, processed_video_url=None, segments=None, script=None, status="processing"):
    video = Video(video_url, segment_length, file_urls, processed_video_url, segments, script, status)
    video_data = video.to_dict()

    # Insert the video data into the MongoDB 'videos' collection
    try:
        mongo.db.videos.insert_one(video_data)
        logging.info(f"Video saved to MongoDB with URL: {video_url}")
    except Exception as e:
        logging.error(f"Error inserting video into MongoDB: {str(e)}")
        return None

    return video_data

# Function to get all videos from MongoDB
def get_all_videos():
    videos = mongo.db.videos.find()
    video_list = []
    for video in videos:
        video_list.append({
            'video_url': video['video_url'],
            'segment_length': video['segment_length'],
            'file_urls': video['file_urls'],
            'processed_video_url': video.get('processed_video_url'),
            'segments': video.get('segments'),
            'script': video.get('script'),
            'video_length': video['video_length'],
            'status': video['status'],
            'created_at': video['created_at']
        })
    return video_list

# Function to update a video URL if needed
def update_video_url(video_id, new_video_url):
    try:
        mongo.db.videos.update_one(
            {'_id': video_id},
            {'$set': {'video_url': new_video_url}}
        )
        logging.info(f"Video URL updated for video ID: {video_id}")
    except Exception as e:
        logging.error(f"Error updating video URL: {str(e)}")
        return None