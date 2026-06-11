import os
import sys
import re
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url):
    """Extracts the video ID from various forms of YouTube URLs."""
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def transcribe_video(url):
    """
    Skill: YouTube Transcriber
    Purpose: Fetches the transcript for a given YouTube video URL.
    """
    print(f"🎧 ครีมกำลังเริ่มถอดเทปจากวิดีโอ: {url}")
    
    video_id = extract_video_id(url)
    if not video_id:
        print("❌ ข้อผิดพลาด: ไม่พบ Video ID ใน URL กรุณาตรวจสอบลิงก์อีกครั้ง")
        return
    try:
        # Initialize API
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['th']).fetch()
            print("✅ พบซับไตเติ้ลภาษาไทย!")
        except:
            print("⚠️ ไม่พบซับไตเติ้ลภาษาไทย กำลังพยายามแปลอัตโนมัติ...")
            # If no Thai, try to find any available and translate to Thai
            transcript = transcript_list.find_transcript(['en']).translate('th').fetch()
            print("✅ ดึงซับไตเติ้ลภาษาอังกฤษและแปลเป็นไทยแล้ว!")
            
        # Combine the text
        full_text = " ".join([entry.text for entry in transcript])
        
        # Save to raw_materials
        output_filename = f"transcript_{video_id}.md"
        output_path = os.path.join("workspace", "1_raw_materials", output_filename)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# 📝 Transcript for Video ID: {video_id}\n")
            f.write(f"**URL:** {url}\n")
            f.write(f"**Status:** Raw Transcript\n\n")
            f.write(f"--- \n\n")
            f.write(full_text)
            
        print(f"✅ ถอดเทปเสร็จสิ้น! บันทึกไว้ที่: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการดึงซับไตเติ้ล: {e}")
        print("วิดีโอนี้อาจไม่มีซับไตเติ้ล (CC) หรือถูกปิดกั้นไว้จ้า")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        transcribe_video(sys.argv[1])
    else:
        print("💡 กรุณาระบุ Link YouTube ที่ต้องการถอดเทป เช่น: python skills/youtube_transcriber.py 'https://www.youtube.com/watch?v=...'")
