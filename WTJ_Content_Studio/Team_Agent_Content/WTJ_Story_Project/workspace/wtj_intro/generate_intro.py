import os
import wave
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

# Paths
WORKSPACE_DIR = "WTJ_Content_Studio/Team_Agent_Content/WTJ_Story_Project/workspace/wtj_intro"
LOGO_SOURCE = os.path.join(WORKSPACE_DIR, "logo_source.png")
OUTPUT_VIDEO = os.path.join(WORKSPACE_DIR, "wtj_intro.mp4")
TEMP_DIR = os.path.join(WORKSPACE_DIR, "temp_frames")
TEMP_AUDIO = os.path.join(WORKSPACE_DIR, "temp_audio.wav")

os.makedirs(TEMP_DIR, exist_ok=True)

print("Starting WTJ Story Intro generation script...")

# ----------------------------------------------------
# 1. SEGMENT LOGO PARTS
# ----------------------------------------------------
print("Segmenting logo source...")
img = Image.open(LOGO_SOURCE)
arr = np.array(img)
r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]

# Define masks based on solid RGB colors of the dots
# Red dot is roughly (236, 26, 34)
red_mask = (r > 150) & (g < 100) & (b < 100) & (a > 0)
# Green dot is roughly (8, 145, 74)
green_mask = (g > 120) & (r < 100) & (b < 120) & (a > 0)
# Blue dot is roughly (8, 100, 171)
blue_mask = (b > 120) & (r < 100) & (g < 150) & (a > 0)
# Text is all other non-transparent pixels
text_mask = (a > 0) & (~red_mask) & (~green_mask) & (~blue_mask)

def extract_part(mask):
    part = np.zeros_like(arr)
    part[mask] = arr[mask]
    return Image.fromarray(part)

red_dot_img = extract_part(red_mask)
green_dot_img = extract_part(green_mask)
blue_dot_img = extract_part(blue_mask)
text_img = extract_part(text_mask)

# Crop dots to their bounding box and find their centers in 1024x1024 canvas space
def get_cropped_dot(dot_img):
    bbox = dot_img.getbbox()
    cropped = dot_img.crop(bbox)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    center_1024 = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
    return cropped, center_1024

red_cropped, red_center_1024 = get_cropped_dot(red_dot_img)
green_cropped, green_center_1024 = get_cropped_dot(green_dot_img)
blue_cropped, blue_center_1024 = get_cropped_dot(blue_dot_img)

# Offset to center 1024x1024 image in 1920x1080 canvas
DX, DY = 448, 28

# Final landing targets of the dots in 1920x1080 space
red_target = np.array([red_center_1024[0] + DX, red_center_1024[1] + DY])
green_target = np.array([green_center_1024[0] + DX, green_center_1024[1] + DY])
blue_target = np.array([blue_center_1024[0] + DX, blue_center_1024[1] + DY])

# Place the entire white text on a 1920x1080 canvas
text_1080 = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
text_1080.paste(text_img, (DX, DY))

# ----------------------------------------------------
# 2. DEFINE ANIMATION PARAMETERS
# ----------------------------------------------------
TOTAL_FRAMES = 120 # 4 seconds @ 30fps

# Start positions for dot entry (flying in from off-screen)
green_start = np.array([2100.0, -100.0])      # Top-right
blue_start = np.array([2100.0, 1180.0])       # Bottom-right
red_start = np.array([-200.0, 1180.0])        # Bottom-left

# Timeline
green_range = (15, 42)
blue_range = (17, 44)
red_range = (19, 45)
reveal_range = (45, 75)
fade_out_start = 105

# Colors (RGB) for glows
RED_RGB = (236, 26, 34)
GREEN_RGB = (8, 145, 74)
BLUE_RGB = (8, 100, 171)

# Easing Function: Cubic Out
def ease_out_cubic(t):
    return 1.0 - (1.0 - t) ** 3

# Easing Function: Quadratic In Out
def ease_in_out_quad(t):
    return 2.0 * t * t if t < 0.5 else 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0

# Easing Function: Cubic In Out
def ease_in_out_cubic(t):
    return 4.0 * t ** 3 if t < 0.5 else 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0

# ----------------------------------------------------
# 3. HELPER RENDERING FUNCTIONS
# ----------------------------------------------------
def create_radial_gradient(width, height, center_color, edge_color):
    y, x = np.ogrid[:height, :width]
    center_y, center_x = height / 2.0, width / 2.0
    dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
    
    # Normalize distance and apply non-linear falloff
    dist_norm = dist / max_dist
    factor = dist_norm ** 1.8 # Soft falloff
    
    r = center_color[0] + (edge_color[0] - center_color[0]) * factor
    g = center_color[1] + (edge_color[1] - center_color[1]) * factor
    b = center_color[2] + (edge_color[2] - center_color[2]) * factor
    
    arr = np.stack([r, g, b], axis=-1).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")

def draw_dot(bg_img, dot_img, center, scale=1.0, alpha=255, glow_radius=15, glow_intensity=0.5):
    w, h = dot_img.size
    new_w, new_h = int(w * scale), int(h * scale)
    dot_resized = dot_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Adjust opacity
    if alpha < 255:
        dot_arr = np.array(dot_resized)
        dot_arr[:, :, 3] = (dot_arr[:, :, 3] * (alpha / 255.0)).astype(np.uint8)
        dot_resized = Image.fromarray(dot_arr)
        
    # Draw neon glow
    if glow_radius > 0:
        glow_w = new_w + glow_radius * 4
        glow_h = new_h + glow_radius * 4
        glow_img = Image.new("RGBA", (glow_w, glow_h), (0, 0, 0, 0))
        glow_img.paste(dot_resized, (glow_radius * 2, glow_radius * 2))
        
        # Blur to create glow
        glow_blurred = glow_img.filter(ImageFilter.GaussianBlur(glow_radius))
        
        # Scale brightness of the glow
        glow_arr = np.array(glow_blurred)
        glow_arr[:, :, 3] = (glow_arr[:, :, 3] * glow_intensity).astype(np.uint8)
        glow_blurred = Image.fromarray(glow_arr)
        
        # Paste glow centered at coordinates
        gx = int(center[0] - glow_w / 2.0)
        gy = int(center[1] - glow_h / 2.0)
        bg_img.paste(glow_blurred, (gx, gy), glow_blurred)
        
    # Paste sharp dot centered
    dx = int(center[0] - new_w / 2.0)
    dy = int(center[1] - new_h / 2.0)
    bg_img.paste(dot_resized, (dx, dy), dot_resized)

def draw_pulse(bg_img, center, frame, start_frame, color_rgb):
    duration = 12
    if start_frame <= frame < start_frame + duration:
        t = (frame - start_frame) / float(duration)
        # Interpolate: size goes from 30 to 180, alpha goes from 0.8 to 0
        size = int(30 + 150 * t)
        alpha = int(255 * (1.0 - t) * 0.7)
        
        pulse_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pulse_img)
        draw.ellipse([0, 0, size, size], fill=color_rgb + (alpha,))
        
        # Blur the pulse
        pulse_img = pulse_img.filter(ImageFilter.GaussianBlur(8))
        
        x = int(center[0] - size / 2.0)
        y = int(center[1] - size / 2.0)
        bg_img.paste(pulse_img, (x, y), pulse_img)

def render_text_reveal(bg_img, text_img, frame):
    # Text is invisible before reveal_range[0]
    if frame < reveal_range[0]:
        return
        
    t_start, t_end = reveal_range
    if frame > t_end:
        u = 1.0
    else:
        u = ease_in_out_quad((frame - t_start) / float(t_end - t_start))
        
    # Text location bounds: x ranges from 550 to 1380
    x_start, x_end = 550, 1380
    x_wipe = x_start + (x_end - x_start) * u
    
    width = 80 # Soft transition width
    
    text_arr = np.array(text_img)
    cols = np.arange(1920)
    
    # Calculate wipe mask for columns
    # c < x_wipe - width/2: 1.0 (visible)
    # c > x_wipe + width/2: 0.0 (invisible)
    mask_vals = np.clip((x_wipe + width/2.0 - cols) / width, 0.0, 1.0)
    # Broadcast to 2D
    mask = np.tile(mask_vals, (1080, 1))
    
    revealed_text_arr = text_arr.copy()
    revealed_text_arr[:, :, 3] = (revealed_text_arr[:, :, 3] * mask).astype(np.uint8)
    revealed_text = Image.fromarray(revealed_text_arr)
    
    # Paste revealed text on background
    bg_img.paste(revealed_text, (0, 0), revealed_text)
    
    # Only draw the sweep beam during the active sweep range
    if frame <= t_end + 5:
        # Create a vertical light sweep glow at x_wipe
        sweep_mask_vals = np.exp(-((cols - x_wipe) / 25.0) ** 2) # Gaussian profile
        sweep_mask_vals = np.clip(sweep_mask_vals * 255.0, 0, 255).astype(np.uint8)
        
        # Light blue / Cyan glow sweep
        sweep_arr = np.zeros((1080, 1920, 4), dtype=np.uint8)
        sweep_arr[:, :, 0] = 135  # R
        sweep_arr[:, :, 1] = 206  # G
        sweep_arr[:, :, 2] = 250  # B (Light Sky Blue)
        sweep_arr[:, :, 3] = np.tile(sweep_mask_vals, (1080, 1))
        
        # Mask the sweep glow by a blurred version of the text alpha so it shines nicely on the letters
        text_alpha = text_arr[:, :, 3]
        text_alpha_img = Image.fromarray(text_alpha)
        text_alpha_blurred = np.array(text_alpha_img.filter(ImageFilter.GaussianBlur(8))) / 255.0
        
        # Apply mask and draw
        sweep_arr[:, :, 3] = (sweep_arr[:, :, 3] * text_alpha_blurred * 1.5).clip(0, 255).astype(np.uint8)
        sweep_glow = Image.fromarray(sweep_arr)
        
        bg_img.paste(sweep_glow, (0, 0), sweep_glow)

# ----------------------------------------------------
# 4. RENDER FRAME BY FRAME
# ----------------------------------------------------
print("Rendering frames...")
base_bg_color = (25, 28, 32)   # Dark slate blue/grey center
edge_bg_color = (5, 5, 6)      # Pure dark edges

for f in range(TOTAL_FRAMES):
    # A. Create background gradient
    frame_img = create_radial_gradient(1920, 1080, base_bg_color, edge_bg_color)
    
    # B. Render Text
    render_text_reveal(frame_img, text_1080, f)
    
    # C. Render landing pulses (if any)
    draw_pulse(frame_img, green_target, f, green_range[1], GREEN_RGB)
    draw_pulse(frame_img, blue_target, f, blue_range[1], BLUE_RGB)
    draw_pulse(frame_img, red_target, f, red_range[1], RED_RGB)
    
    # D. Calculate and Draw Green Dot
    if f >= green_range[0]:
        if f > green_range[1]:
            g_pos = green_target
            g_alpha = 255
        else:
            t = (f - green_range[0]) / float(green_range[1] - green_range[0])
            factor = ease_out_cubic(t)
            g_pos = green_start + (green_target - green_start) * factor
            g_alpha = int(255 * t)
        
        # Draw green dot with soft glow
        draw_dot(frame_img, green_cropped, g_pos, scale=1.0, alpha=g_alpha, glow_radius=10, glow_intensity=0.5)
        
    # E. Calculate and Draw Blue Dot
    if f >= blue_range[0]:
        if f > blue_range[1]:
            b_pos = blue_target
            b_alpha = 255
        else:
            t = (f - blue_range[0]) / float(blue_range[1] - blue_range[0])
            factor = ease_out_cubic(t)
            b_pos = blue_start + (blue_target - blue_start) * factor
            b_alpha = int(255 * t)
            
        draw_dot(frame_img, blue_cropped, b_pos, scale=1.0, alpha=b_alpha, glow_radius=10, glow_intensity=0.5)
        
    # F. Calculate and Draw Red Dot
    if f >= red_range[0]:
        if f > red_range[1]:
            r_pos = red_target
            r_alpha = 255
        else:
            t = (f - red_range[0]) / float(red_range[1] - red_range[0])
            factor = ease_out_cubic(t)
            r_pos = red_start + (red_target - red_start) * factor
            r_alpha = int(255 * t)
            
        draw_dot(frame_img, red_cropped, r_pos, scale=1.0, alpha=r_alpha, glow_radius=10, glow_intensity=0.5)
        
    # G. Apply Camera Push-in (slow scale zoom from 100% to 103%)
    scale_factor = 1.0 + 0.03 * (f / float(TOTAL_FRAMES - 1))
    new_w, new_h = int(1920 * scale_factor), int(1080 * scale_factor)
    frame_scaled = frame_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Crop center back to 1920x1080
    left = (new_w - 1920) // 2
    top = (new_h - 1080) // 2
    frame_cropped = frame_scaled.crop((left, top, left + 1920, top + 1080))
    
    # H. Apply Fade Out at the end (from frame 105 to 119)
    if f >= fade_out_start:
        fade_u = (f - fade_out_start) / float(TOTAL_FRAMES - 1 - fade_out_start)
        # We can fade to black by overlaying a black layer with varying opacity
        black_overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, int(255 * fade_u)))
        frame_cropped = Image.alpha_composite(frame_cropped, black_overlay)
        
    # Save frame
    frame_cropped.convert("RGB").save(os.path.join(TEMP_DIR, f"frame_{f:03d}.png"))

print(f"Frames rendered successfully inside: {TEMP_DIR}")

# ----------------------------------------------------
# 5. SYNTHESIZE CINEMATIC AUDIO SOUND EFFECT
# ----------------------------------------------------
print("Synthesizing audio sound effect...")
fs = 44100
t_audio = np.arange(fs * 4) / float(fs)  # 4 seconds

# Layer 1: Swoosh (rising wind/sub sound that peaks at 1.4s)
swoosh_env = np.exp(-((t_audio - 1.3) / 0.45) ** 2)
swoosh_freq = 35.0 + 150.0 * np.exp(-((t_audio - 1.3) / 0.4) ** 2)
swoosh_phase = 2.0 * np.pi * np.cumsum(swoosh_freq) / float(fs)
swoosh_wave = np.sin(swoosh_phase)
swoosh_wave += 0.3 * np.sin(2.0 * swoosh_phase)  # add 2nd harmonic
swoosh_wave += 0.15 * np.sin(3.0 * swoosh_phase) # add 3rd harmonic
swoosh = swoosh_wave * swoosh_env * 0.12

# Swoosh Noise layer (simulating aerodynamic wind sweep)
np.random.seed(42)
white_noise = np.random.normal(0, 1.0, len(t_audio))
# Simple low-pass filter (moving average) for wind sound
kernel_size = 40
kernel = np.ones(kernel_size) / float(kernel_size)
lowpassed_noise = np.convolve(white_noise, kernel, mode='same')
wind_env = np.exp(-((t_audio - 1.25) / 0.3) ** 2)
wind = lowpassed_noise * wind_env * 0.08

# Layer 2: Sub-bass Drop / Impact (starts at 1.5s - frame 45)
impact = np.zeros_like(t_audio)
impact_idx = t_audio >= 1.5
t_imp = t_audio[impact_idx] - 1.5
# Frequency sweep from 80Hz down to 25Hz
imp_freq = 25.0 + 55.0 * np.exp(-t_imp / 0.35)
imp_phase = 2.0 * np.pi * np.cumsum(imp_freq) / float(fs)
imp_decay = np.exp(-t_imp / 0.6)  # Exponential decay of the hit
impact[impact_idx] = np.sin(imp_phase) * imp_decay * 0.45

# Layer 3: Deep Hum / Drone (starts at 1.5s, decays very slowly to the end)
drone = np.zeros_like(t_audio)
drone_idx = t_audio >= 1.5
t_drone = t_audio[drone_idx] - 1.5
# 55Hz (A1) and 110Hz (A2), with a 5Hz tremolo
tremolo = 1.0 + 0.12 * np.sin(2.0 * np.pi * 5.0 * t_drone)
drone_wave = np.sin(2.0 * np.pi * 55.0 * t_drone) + 0.25 * np.sin(2.0 * np.pi * 110.0 * t_drone)
# Attack and decay envelope
drone_env = np.exp(-t_drone / 1.5) * (1.0 - np.exp(-t_drone / 0.08))
drone[drone_idx] = drone_wave * drone_env * tremolo * 0.18

# Combine all sound layers
full_audio = swoosh + wind + impact + drone

# Normalize to safe levels to avoid clipping
max_val = np.max(np.abs(full_audio))
if max_val > 0:
    full_audio = (full_audio / max_val) * 0.85

# Convert to 16-bit PCM
audio_pcm = (full_audio * 32767).astype(np.int16)

# Save WAV file
print(f"Saving temporary WAV audio to: {TEMP_AUDIO}")
with wave.open(TEMP_AUDIO, 'wb') as w:
    w.setnchannels(1)      # Mono
    w.setsampwidth(2)      # 16-bit
    w.setframerate(fs)     # 44.1kHz
    w.writeframes(audio_pcm.tobytes())

# ----------------------------------------------------
# 6. COMPILE WITH FFMPEG
# ----------------------------------------------------
print("Running FFmpeg to compile video and audio...")
# FFmpeg command:
# -y: overwrite output
# -r 30: input framerate 30fps
# -i temp_frames/frame_%03d.png: input frames
# -i temp_audio.wav: input audio
# -c:v libx264: H.264 video codec
# -pix_fmt yuv420p: standard pixel format for web players
# -c:a aac: AAC audio codec
# -b:a 192k: audio bitrate
# -shortest: end when the shortest input ends (which is 4.0s for both)
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-r", "30",
    "-i", os.path.join(TEMP_DIR, "frame_%03d.png"),
    "-i", TEMP_AUDIO,
    "-c:v", "libx264",
    "-profile:v", "high",
    "-level:v", "4.0",
    "-pix_fmt", "yuv420p",
    "-crf", "18", # visually lossless
    "-c:a", "aac",
    "-b:a", "192k",
    OUTPUT_VIDEO
]

try:
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"SUCCESS! Video intro compiled successfully at: {OUTPUT_VIDEO}")
except subprocess.CalledProcessError as e:
    print(f"Error compiling video with FFmpeg: {e}")

# ----------------------------------------------------
# 7. CLEAN UP TEMPORARY FILES
# ----------------------------------------------------
print("Cleaning up temporary files...")
import shutil
try:
    shutil.rmtree(TEMP_DIR)
    os.remove(TEMP_AUDIO)
    print("Cleanup completed.")
except Exception as e:
    print(f"Error during cleanup: {e}")

print("WTJ Story Video Intro Generation Completed!")
