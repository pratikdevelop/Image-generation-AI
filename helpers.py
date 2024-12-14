# helpers.py
import os
import subprocess
import uuid
import boto3
import yt_dlp as youtube_dl
from gtts import gTTS
import pyttsx3
import ffmpeg
import logging

# Configuration
UPLOAD_FOLDER = 'uploads'
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')
AWS_S3_REGION = os.getenv('AWS_S3_REGION')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

# AWS S3 upload helper function
def upload_to_s3(file_path, file_name):
    try:
        s3_client = boto3.client('s3',
                                 region_name=os.getenv('AWS_S3_REGION'),
                                 aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
                                 aws_secret_access_key=os.getenv('AWS_SECRET_KEY'))
        s3_client.upload_file(file_path, os.getenv('AWS_S3_BUCKET'), file_name)
        file_url = f"https://{os.getenv('AWS_S3_BUCKET')}.s3.{os.getenv('AWS_S3_REGION')}.amazonaws.com/{file_name}"
        return file_url
    except Exception as e:
        logging.error(f"Error uploading to S3: {e}")
        return None

# Download a video from a URL (social media support via yt-dlp)
def download_social_video(video_url, output_path):
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo+bestaudio/best', 
        'quiet': False,
        'verbose': True,
        'continuedl': True
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except youtube_dl.utils.DownloadError as e:
        logging.error(f"Download error: {e}")
        raise

# Get video duration
def get_video_duration(video_file):
    command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_file
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout.strip())

# Download video helper
def download_video(video_url):
    try:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4().hex}.mp4'),
            'quiet': False,
            'verbose': True
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            video_file = ydl.prepare_filename(info_dict)
        return video_file
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        return None

# Generate a basic script for the video
def generate_script(video_url):
    script = f"""
    Welcome to our video! In today's video, we will discuss some interesting topics.
    Based on the video you provided ({video_url}), here's what we'll cover:
    1. Introduction to the content
    2. Main discussion points
    3. Conclusion and key takeaways
    """
    return script


def generate_audio_from_script(script):
    try:
        # You can choose either pyttsx3 or gTTS. Here is an example of pyttsx3:
        engine = pyttsx3.init()
        audio_file = os.path.join(UPLOAD_FOLDER, f"audio_{uuid.uuid4().hex}.mp3")
        engine.save_to_file(script, audio_file)
        engine.runAndWait()
        return audio_file
    except Exception as e:
        logging.error(f"Error generating audio: {e}")
        return None


# Process AI video with text-to-speech and video segmentation
# def process_AI_video(video_file, segment_length, script):
#     try:
#         # Generate audio from the script
#         audio_file = generate_audio_from_script(script)
#         if not audio_file:
#             raise ValueError("Failed to generate audio from script.")

#         # Get the video duration
#         video_info = ffmpeg.probe(video_file, v='error', select_streams='v:0', show_entries='stream=duration')
#         video_duration = float(video_info['streams'][0]['duration'])

#         segments = []
#         for start_time in range(0, int(video_duration), int(segment_length)):
#             end_time = min(start_time + int(segment_length), video_duration)

#             # Extract the segment using ffmpeg
#             segment_output = os.path.join(UPLOAD_FOLDER, f"segment_{uuid.uuid4().hex}.mp4")
#             ffmpeg.input(video_file, ss=start_time, t=end_time-start_time).output(segment_output).run()

#             segments.append(segment_output)

#         # Concatenate the video segments
#         concat_file = os.path.join(UPLOAD_FOLDER, f"concat_list_{uuid.uuid4().hex}.txt")
#         with open(concat_file, 'w') as f:
#             for segment in segments:
#                 f.write(f"file '{segment}'\n")

#         final_video_output = os.path.join(UPLOAD_FOLDER, f"final_video_{uuid.uuid4().hex}.mp4")
        
#         # Concatenate video segments using ffmpeg
#         ffmpeg.input(concat_file, format='concat', safe=0).output(final_video_output).run()

#         # Add the generated audio to the final video
#         final_video_with_audio = os.path.join(UPLOAD_FOLDER, f"final_video_with_audio_{uuid.uuid4().hex}.mp4")
#         ffmpeg.input(final_video_output).input(audio_file).output(final_video_with_audio, vcodec='libx264', acodec='aac').run()

#         # Clean up temporary files
#         os.remove(concat_file)
#         for segment in segments:
#             os.remove(segment)
#         os.remove(final_video_output)
#         os.remove(audio_file)

#         return final_video_with_audio
#     except Exception as e:
#         logging.error(f"Error processing video: {e}")
#         return None


# Function to convert video to MP4 using ffmpeg
def convert_video_to_mp4(input_file, output_file):
    try:
        # Running the ffmpeg command to convert the video
        subprocess.run([
            'ffmpeg', '-i', input_file, '-vcodec', 'libx264', '-acodec', 'aac', '-strict', 'experimental', output_file
        ], check=True)
        logging.info(f"Video successfully converted: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        logging.error(f"Error converting video: {e.stderr}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error during video conversion: {e}")
        return None

# Function to process video with AI script and generate the final output
def process_AI_video(video_file, segment_length, script):
    try:
        # Generate audio from the script
        audio_file = generate_audio_from_script(script)
        if not audio_file:
            raise ValueError("Failed to generate audio from script.")

        # Get the video duration using ffprobe and capture detailed errors
        try:
            video_info = ffmpeg.probe(video_file, cmd='ffprobe',  v='error', select_streams='v:0', show_entries='stream=duration')
            video_duration = float(video_info['streams'][0]['duration'])
        except subprocess.CalledProcessError as e:
            logging.error(f"ffprobe error while fetching video duration: {e.stderr.decode('utf-8')}")
            logging.error(f"ffprobe error: {e.stderr}")
            return None
        except Exception as e:
            logging.error(f"Error getting video duration: {str(e)}")
            return None

        # Split video into segments
        segments = []
        for start_time in range(0, int(video_duration), int(segment_length)):
            end_time = min(start_time + int(segment_length), video_duration)

            # Extract the segment using ffmpeg and handle errors
            try:
                segment_output = os.path.join(UPLOAD_FOLDER, f"segment_{uuid.uuid4().hex}.mp4")
                ffmpeg.input(video_file, ss=start_time, t=end_time-start_time).output(segment_output).run()
                segments.append(segment_output)
            except ffmpeg.Error as e:
                logging.error(f"Error extracting video segment from {start_time} to {end_time}: {e.stderr}")
                return None
            except Exception as e:
                logging.error(f"Error processing video segment: {e}")
                return None

        # Concatenate the video segments
        concat_file = os.path.join(UPLOAD_FOLDER, f"concat_list_{uuid.uuid4().hex}.txt")
        try:
            with open(concat_file, 'w') as f:
                for segment in segments:
                    f.write(f"file '{segment}'\n")
        except Exception as e:
            logging.error(f"Error creating concat file: {e}")
            return None

        final_video_output = os.path.join(UPLOAD_FOLDER, f"final_video_{uuid.uuid4().hex}.mp4")
        
        # Concatenate video segments using ffmpeg and handle errors
        try:
            ffmpeg.input(concat_file, format='concat', safe=0).output(final_video_output).run()
        except ffmpeg.Error as e:
            logging.error(f"Error concatenating video segments: {e.stderr}")
            return None
        except Exception as e:
            logging.error(f"Error processing concatenation: {e}")
            return None

        # Add the generated audio to the final video
        final_video_with_audio = os.path.join(UPLOAD_FOLDER, f"final_video_with_audio_{uuid.uuid4().hex}.mp4")
        try:
            ffmpeg.input(final_video_output).input(audio_file).output(final_video_with_audio, vcodec='libx264', acodec='aac').run()
        except ffmpeg.Error as e:
            logging.error(f"Error adding audio to video: {e.stderr}")
            return None
        except Exception as e:
            logging.error(f"Error processing audio addition: {e}")
            return None

        # Clean up temporary files
        try:
            os.remove(concat_file)
            for segment in segments:
                os.remove(segment)
            os.remove(final_video_output)
            os.remove(audio_file)
        except Exception as e:
            logging.error(f"Error cleaning up temporary files: {e}")

        return final_video_with_audio

    except Exception as e:
        logging.error(f"Error processing video: {e}")
        return None

# Main function that integrates both video conversion and processing
def main(input_video, segment_length, script):
    # Convert video to MP4 format before processing
    output_video = os.path.join(UPLOAD_FOLDER, f"converted_video_{uuid.uuid4().hex}.mp4")
    converted_video = convert_video_to_mp4(input_video, output_video)
    if not converted_video:
        logging.error("Video conversion failed.")
        return None
    
    # Process the AI video with the script and generate the final output
    final_video = process_AI_video(converted_video, segment_length, script)
    if not final_video:
        logging.error("Error during video processing.")
        return None

    return final_video
