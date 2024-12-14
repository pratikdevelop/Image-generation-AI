import subprocess
import ffmpeg
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging
import uuid
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from gtts import gTTS
import instaloader

# Import helper functions and configurations
from helpers import upload_to_s3, download_social_video, get_video_duration, download_video, generate_script, process_AI_video
import instaloader

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')
AWS_S3_REGION = os.getenv('AWS_S3_REGION')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# Endpoint: Process video into segments and upload
@app.route('/process-video', methods=['POST'])
def process_video():
    data = request.json
    video_url = data.get('url')
    segment_length = data.get('segment_length')

    if not video_url or not segment_length:
        return jsonify({'error': 'Missing video URL or segment length.'}), 400

    video_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.mp4")
    try:
        # Download video
        download_social_video(video_url, video_file)

        # Get video duration
        video_duration = get_video_duration(video_file)
        segment_urls = []

        # Split and upload video segments
        for start_time in range(0, int(video_duration), int(segment_length)):
            end_time = min(start_time + int(segment_length), video_duration)
            segment_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_segment.mp4")
            subprocess.run([
                'ffmpeg', '-i', video_file, '-ss', str(start_time), '-to', str(end_time), '-c', 'copy', segment_file
            ], check=True)

            s3_url = upload_to_s3(segment_file, os.path.basename(segment_file))
            if s3_url:
                segment_urls.append(s3_url)

            os.remove(segment_file)

        os.remove(video_file)

        return jsonify({'videoSegments': segment_urls})

    except Exception as e:
        logging.error(f"Error processing video: {e}")
        return jsonify({'error': 'Failed to process video', 'details': str(e)}), 500

@app.route('/download-instagram', methods=['POST'])
def download_instagram():
    data = request.json
    post_url = data.get('url')

    if not post_url:
        return jsonify({'error': 'Missing Instagram post URL.'}), 400

    try:
        # Download Instagram post
        instaloader_instance = instaloader.Instaloader()
        shortcode = post_url.split('/')[-2]
        post = instaloader.Post.from_shortcode(instaloader_instance.context, shortcode)
        download_folder = os.path.join(UPLOAD_FOLDER, "instagram")
        os.makedirs(download_folder, exist_ok=True)
        instaloader_instance.download_post(post, target=download_folder)

        # Find and upload the video
        video_file = next(
            (file for file in os.listdir(download_folder) if file.endswith('.mp4')), None)
        if video_file:
            video_path = os.path.join(download_folder, video_file)
            s3_url = upload_to_s3(video_path, video_file)
            os.remove(video_path)
            return jsonify({'videoUrl': s3_url})
        else:
            return jsonify({'error': 'No video found in post.'}), 500
    except Exception as e:
        logging.error(f"Error downloading Instagram post: {e}")
        return jsonify({'error': 'Failed to download Instagram post', 'details': str(e)}), 500

@app.route('/download-facebook', methods=['POST'])
def download_facebook():
    """
    Endpoint to download Facebook videos, reels, or posts.
    """
    data = request.json
    video_url = data.get('url')

    if not video_url:
        return jsonify({'error': 'Missing Facebook video URL.'}), 400

    try:
        # Generate a unique filename for the downloaded video
        video_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.mp4")

        # Download the Facebook video using yt-dlp
        download_social_video(video_url, video_file)

        # Verify the file was downloaded
        if not os.path.exists(video_file):
            return jsonify({'error': 'Failed to download Facebook video.'}), 500

        # Upload the video to AWS S3
        s3_url = upload_to_s3(video_file, os.path.basename(video_file))

        # Remove the local file after upload
        if os.path.exists(video_file):
            os.remove(video_file)

        return jsonify({'videoUrl': s3_url, 'message': 'Facebook video downloaded and uploaded successfully.'})

    except Exception as e:
        logging.error(f"Error downloading Facebook video: {e}")
        return jsonify({'error': 'Unexpected error occurred', 'details': str(e)}), 500

# Endpoint to generate video from any website URL
@app.route('/generate-ai-video', methods=['POST'])
def generate_video():
    data = request.json
    video_url = data.get('script')
    segment_length = 60

    print(video_url)
    if not video_url or not segment_length:
        return jsonify({'error': 'Missing video URL or segment length.'}), 400

    try:
        # Download video
        video_file = download_video(video_url)

        if not video_file:
            return jsonify({'error': 'Failed to download video.'}), 500

        # Generate AI script (from template or basic logic)
        script = generate_script(video_url)

        # Process video segments with audio
        processed_video_file = process_AI_video(video_file, segment_length, script)

        if not processed_video_file:
            return jsonify({'error': 'Failed to process video.'}), 500

        # Upload to S3
        s3_url = upload_to_s3(processed_video_file, os.path.basename(processed_video_file))

        # Clean up local files
        os.remove(video_file)
        os.remove(processed_video_file)

        return jsonify({'videoUrl': s3_url, 'message': 'Video generated and uploaded successfully.'})
    except Exception as e:
        logging.error(f"Error generating video: {e}")
        return jsonify({'error': 'Failed to generate video', 'details': str(e)}), 500


def generate_audio_from_script(script_text):
    try:
        tts = gTTS(script_text, lang='en')
        audio_filename = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_audio.mp3")
        tts.save(audio_filename)
        return audio_filename
    except Exception as e:
        logging.error(f"Error generating audio: {e}")
        return None
    

def get_audio_duration(audio_file):
    try:
        # Probe the audio file using ffmpeg to get detailed information
        audio_info = ffmpeg.probe(audio_file,cmd='ffprobe', v='error', select_streams='a:0', show_entries='stream=duration')
        
        # Extract the duration from the probe output
        audio_duration = float(audio_info['streams'][0]['duration'])
        
        return audio_duration
    except ffmpeg.Error as e:
        # Handle any error related to ffmpeg
        print(f"Error getting audio duration: {e.stderr.decode()}")
        return None
    except Exception as e:
        # Catch any other exceptions
        print(f"Unexpected error: {e}")
        return None


# Function to create a black screen video
def create_video_from_audio(audio_file):
    try:
        # Step 1: Get the audio duration
        audio_duration = get_audio_duration(audio_file)
        if not audio_duration:
            raise ValueError("Failed to retrieve audio duration.")
        
        # Step 2: Create a video filename using UUID
        video_filename = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_video.mp4")
        
        # Step 3: Create a black screen video with the same duration as the audio
        ffmpeg_command = [
            'ffmpeg', '-f', 'lavfi', '-t', str(audio_duration),
            '-i', 'color=c=black:s=1280x720', '-vcodec', 'libx264', '-an', video_filename
        ]
        
        # Execute the ffmpeg command to create the video
        subprocess.run(ffmpeg_command, check=True)

        return video_filename

    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating video: {e.stderr}")
        return None
    except ValueError as e:
        logging.error(f"ValueError: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error creating video: {e}")
        return None


# Function to combine the video and audio
def combine_audio_and_video(video_file, audio_file):
    try:
        # Generate the final video filename using UUID
        final_video_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_final_video.mp4")
        
        video_clip = VideoFileClip(video_file)
        audio_clip = AudioFileClip(audio_file)
        
        # Set the duration of the video clip to match the audio
        # video_clip = video_clip.subclip(0, audio_clip.duration)
        
        # # Combine audio and video
        # final_video = video_clip.set_audio(audio_clip)
        
        # # Write the final output
        # final_video.write_videofile(final_video_file, codec='libx264', audio_codec='aac')
        final_clip = video_clip.with_audio(audio_clip)
        final_clip.write_videofile(final_video_file)		

        return final_video_file

    except Exception as e:
        logging.error(f"Error combining audio and video: {e}")
        return None

# Main function to handle the full process
@app.route('/generate-test-to-video', methods=['POST'])
def generate_video_from_script():
    try:
        data = request.json
        script_text = data.get('script')
        # Step 1: Generate the audio from the script
        audio_file = generate_audio_from_script(script_text)
        if not audio_file or not os.path.exists(audio_file):
            return jsonify({
                'error': 'Audio file is missing or invalid.'
            }), 400  # Return a 400 Bad Request status if the audio file is missing or invalid

        # Step 2: Create a video from the audio
        video_file = create_video_from_audio(audio_file)
        if not video_file:
            return jsonify({
                'error': 'Failed to create video from audio.'
            }), 500  # Return a 500 Internal Server Error if video creation fails

        # Step 3: Combine the video and audio into the final video
        final_video_file = combine_audio_and_video(video_file, audio_file)
        if not final_video_file:
            return jsonify({
                'error': 'Failed to combine video and audio.'
            }), 500  # Return a 500 Internal Server Error if combining video and audio fails
        
        # If everything is successful, return the final video file path
        return jsonify({
            'message': 'Video successfully created.',
            'final_video': final_video_file
        }), 200  # Return a 200 OK status with the final video file path

    
        
        # return jsonify(final_video_file)
    except Exception as e:
        logging.error(f"Error generating video: {e}")
        return None
    

#   video_data = save_video(
#             video_url=video_url,
#             segment_length=segment_length,
#             file_urls=json.dumps(segment_urls),
#             status="completed"
#         )


if __name__ == "__main__":
    app.run(debug=True)
