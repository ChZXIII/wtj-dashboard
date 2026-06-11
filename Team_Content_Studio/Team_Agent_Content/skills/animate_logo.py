import os
import sys
import wave
import struct
import math
import subprocess
import shutil

def get_ffmpeg_path():
    """ค้นหาพาร์ทของ FFmpeg บน macOS"""
    common_paths = [
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "ffmpeg" # fall back to system path
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    return "ffmpeg"

# ยืนยันว่ามีการติดตั้ง Pillow สำหรับจัดการรูปภาพ
try:
    from PIL import Image
except ImportError:
    print("⏳ ไม่พบ Pillow กำลังดำเนินการติดตั้งให้อัตโนมัติ...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image

def get_audio_amplitude(wav_path, fps):
    """อ่านไฟล์ WAV และคำนวณระดับความดังในแต่ละเฟรมเพื่อใช้เป็นค่าความต่างขนาด"""
    with wave.open(wav_path, 'rb') as w:
        n_channels = w.getnchannels()
        samp_width = w.getsampwidth()
        framerate = w.getframerate()
        n_frames = w.getnframes()
        
        raw_data = w.readframes(n_frames)
        
    # แปลงข้อมูลดิบตามความกว้างแซมเปิล
    if samp_width == 1:
        fmt = f"{n_frames * n_channels}B"
        samples = [s - 128 for s in struct.unpack(fmt, raw_data)]
    elif samp_width == 2:
        fmt = f"<{n_frames * n_channels}h"
        samples = struct.unpack(fmt, raw_data)
    else:
        raise ValueError("รองรับเฉพาะ WAV 8-bit หรือ 16-bit เท่านั้น")
        
    # แปลงเป็น Mono
    if n_channels > 1:
        mono_samples = []
        for i in range(0, len(samples), n_channels):
            mono_samples.append(sum(samples[i:i+n_channels]) // n_channels)
        samples = mono_samples
        
    # คำนวณข้อมูลเสียงต่อเฟรมวิดีโอ
    samples_per_frame = framerate / fps
    total_frames = int(n_frames / samples_per_frame)
    
    amplitudes = []
    for f in range(total_frames):
        start_idx = int(f * samples_per_frame)
        end_idx = int((f + 1) * samples_per_frame)
        chunk = samples[start_idx:end_idx]
        
        if not chunk:
            amplitudes.append(0)
            continue
            
        # คำนวณค่า RMS (Root Mean Square) เพื่อวัดพลังความดัง
        rms = math.sqrt(sum(s**2 for s in chunk) / len(chunk))
        amplitudes.append(rms)
        
    # ปรับสเกลให้อยู่ระหว่าง 0.0 - 1.0
    max_amp = max(amplitudes) if amplitudes else 1
    if max_amp == 0:
        max_amp = 1
    normalized = [amp / max_amp for amp in amplitudes]
    
    # เกลี่ยระดับเสียง (Smooth Moving Average) ให้ภาพขยับสมูทขึ้น
    smoothed = []
    window_size = 5
    for i in range(len(normalized)):
        start = max(0, i - window_size // 2)
        end = min(len(normalized), i + window_size // 2 + 1)
        smoothed.append(sum(normalized[start:end]) / (end - start))
        
    return smoothed

def animate_logo(image_path, audio_path, output_path, fps=30, max_scale=1.12):
    print("🎬 เริ่มต้นโปรแกรมสร้างโลโก้ขยับตามเสียงพูด...")
    
    temp_wav = "temp_mono_audio.wav"
    ffmpeg_path = get_ffmpeg_path()
    process = None
    
    try:
        # 1. แปลงเสียงเป็น Mono 16kHz WAV เพื่อวิเคราะห์ความดัง
        print("🎵 1. กำลังสกัดคลื่นเสียงด้วย FFmpeg...")
        conv_cmd = [
            ffmpeg_path, "-y",
            "-i", audio_path,
            "-ac", "1",
            "-ar", "16000",
            temp_wav
        ]
        subprocess.run(conv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # 2. คำนวณพลังระดับความดังในแต่ละเฟรม
        print("📊 2. กำลังคำนวณไดนามิกของจังหวะเสียง...")
        amplitudes = get_audio_amplitude(temp_wav, fps)
        total_frames = len(amplitudes)
        
        # 3. โหลดภาพต้นฉบับ
        img = Image.open(image_path).convert("RGBA")
        orig_w, orig_h = img.size
        
        # ทำให้ขนาดภาพเป็นเลขคู่ (divisible by 2) เสมอ เพื่อให้ H.264 เข้ารหัสได้สำเร็จ 100%
        orig_w = (orig_w // 2) * 2
        orig_h = (orig_h // 2) * 2
        
        # จัดการสีพื้นหลัง: ดึงสีพิกเซลมุมซ้ายบน
        # หากภาพโปร่งแสง (Alpha = 0) ให้เปลี่ยนเป็นสีขาวนวลพรีเมียม #f8f7f5 เสมอ
        bg_color = img.getpixel((0, 0))
        if img.mode == "RGBA" and len(bg_color) == 4 and bg_color[3] == 0:
            bg_color = (248, 247, 245, 255)
            print("🎨 ตรวจพบภาพโปร่งแสง! ปรับพื้นหลังเป็นสีขาวนวลพรีเมียม (#f8f7f5) อัตโนมัติ")
        else:
            print(f"🎨 ดึงสีพื้นหลังจากรูปภาพโดยตรง: {bg_color}")
            
        print(f"🖼️ ตรวจพบรูปภาพขนาด: {orig_w}x{orig_h}")
        
        # 4. ตั้งค่า FFmpeg pipeline สำหรับรับภาพดิบ (rawvideo) จาก RAM เข้าสู่การเข้ารหัสโดยตรง
        print("⚡ 3. เปิดท่อส่งข้อมูลด่วนเข้า FFmpeg (High-Speed Memory Pipe)...")
        render_cmd = [
            ffmpeg_path, "-y",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{orig_w}x{orig_h}",
            "-r", str(fps),
            "-i", "-", # อ่านภาพจาก stdin (RAM)
            "-i", audio_path,
            "-map", "0:v", # บังคับเอาวิดีโอจากท่อ RAM (Input 0) เท่านั้น
            "-map", "1:a", # บังคับเอาเสียงจากไฟล์เสียง/วิดีโอ (Input 1) เท่านั้น
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ]
        
        # เปิดโปรเซสแปลงวิดีโอแบบเรียลไทม์
        process = subprocess.Popen(
            render_cmd, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE # จับข้อผิดพลาดมาวิเคราะห์
        )
        
        # 5. วาดเฟรมและยิงตรงเข้าท่อความเร็วสูง
        print(f"🚀 4. กำลังเรนเดอร์และประกอบร่างวิดีโอสด (ทั้งหมด {total_frames} เฟรม)...")
        
        for idx, amp in enumerate(amplitudes):
            # คำนวณขนาดภาพในเฟรมนั้นๆ
            scale = 1.0 + (amp * (max_scale - 1.0))
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            
            # ย่อ/ขยายรูปโลโก้ตามเสียงพูดด้วยฟิลเตอร์คุณภาพสูง
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # สร้างเฟรมหลักพื้นหลัง
            frame = Image.new("RGBA", (orig_w, orig_h), bg_color)
            
            # วางรูปโลโก้ที่ขยายแล้วให้อยู่กึ่งกลางของเฟรม
            paste_x = (orig_w - new_w) // 2
            paste_y = (orig_h - new_h) // 2
            
            frame.paste(resized_img, (paste_x, paste_y), resized_img)
            
            # ดึงข้อมูลพิกเซลดิบ RGB และยิงเข้าท่อ FFmpeg ทันที
            rgb_data = frame.convert("RGB").tobytes()
            process.stdin.write(rgb_data)
            
            # อัปเดตความคืบหน้าให้ผู้ใช้เห็นสดๆ ทุกๆ 10%
            if (idx + 1) % max(1, total_frames // 10) == 0 or idx == total_frames - 1:
                progress = int((idx + 1) / total_frames * 100)
                print(f"   ⚡ เรนเดอร์คืบหน้า: {progress}% ({idx+1}/{total_frames} เฟรม)")
                
        # ปิดท่อส่งข้อมูลและรอให้ FFmpeg ทำงานส่วนสุดท้ายเสร็จ
        process.stdin.close()
        process.wait()
        
        print(f"🏆 สำเร็จแล้วแก! ได้วิดีโอสวยกริ๊บที่: {output_path}")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในระบบ: {e}")
        if process:
            try:
                process.stdin.close()
            except:
                pass
            try:
                stderr_data = process.stderr.read()
                if stderr_data:
                    print("--- FFmpeg Error Log ---")
                    print(stderr_data.decode('utf-8', errors='ignore'))
            except:
                pass
            if process.poll() is None:
                process.kill()
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("วิธีใช้: python3 skills/animate_logo.py <ภาพโลโก้> <ไฟล์เสียง> <ไฟล์วิดีโอผลลัพธ์>")
        sys.exit(1)
    
    # ปรับจูนระดับการขยายภาพสูงสุดจาก args ได้ (ตัวเลือกที่ 4 เป็น float)
    max_scale_val = 1.12
    if len(sys.argv) >= 5:
        try:
            max_scale_val = float(sys.argv[4])
        except ValueError:
            pass
            
    animate_logo(sys.argv[1], sys.argv[2], sys.argv[3], max_scale=max_scale_val)
