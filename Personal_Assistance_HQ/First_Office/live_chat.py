import os
import sys
import asyncio
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
load_dotenv(os.path.join(project_root, ".env"))

API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("Error: ไม่พบ GOOGLE_API_KEY ใน .env")
    sys.exit(1)

# Initialize GenAI Client with v1alpha version for Live API support
client = genai.Client(api_key=API_KEY, http_options={"api_version": "v1alpha"})

# Model for Real-time WebSocket connection
MODEL = "gemini-2.5-flash-native-audio-latest"

async def audio_input_task(session, mic_queue):
    """Pulls recorded mic chunks from mic_queue and streams them to Gemini Live API"""
    while True:
        try:
            data = await mic_queue.get()
            audio_bytes = data.tobytes()
            await session.send_realtime_input(
                media=types.Blob(
                    data=audio_bytes,
                    mime_type="audio/pcm;rate=16000"
                )
            )
            mic_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"\n[ระบบ]: เกิดข้อผิดพลาดในการส่งเสียง: {e}")
            await asyncio.sleep(0.1)

async def audio_output_task(session, audio_stream):
    """Receives responses from Gemini Live API and plays the audio chunks through speakers"""
    async for response in session.receive():
        try:
            server_content = response.server_content
            if server_content and server_content.model_turn:
                for part in server_content.model_turn.parts:
                    if part.inline_data:
                        audio_data = np.frombuffer(part.inline_data.data, dtype="int16")
                        # Write raw PCM chunk directly to sounddevice OutputStream
                        audio_stream.write(audio_data)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"\n[ระบบ]: เกิดข้อผิดพลาดในการรับ/เล่นเสียง: {e}")

async def main():
    print("==================================================")
    print("🎙️  First's Real-time Live Voice Chat (สายตรงเฟิส)")
    print("คำแนะนำ: กรุณาใส่หูฟัง 🎧 เพื่อป้องกันเสียงสะท้อนป้อนกลับไมโครโฟน")
    print("กด Ctrl+C เพื่อวางสาย")
    print("==================================================")

    # 1st Agent Persona Instruction
    instruction = "คุณคือ First (เฟิส) เลขาส่วนตัวและเพื่อนซี้ของคุณเก่ง คุยแบบเป็นกันเองวัยรุ่น สรรพนาม 'ฉัน' และ 'แก' ห้ามใช้ครับ/ค่ะ/ผม/บอส/จ๊ะ เด็ดขาด"
    
    manual_path = os.path.join(current_dir, "first_manual.md")
    pref_path = os.path.join(project_root, "preferences.md")
    
    if os.path.exists(manual_path):
        with open(manual_path, "r", encoding="utf-8") as f:
            instruction += "\n" + f.read()
    if os.path.exists(pref_path):
        with open(pref_path, "r", encoding="utf-8") as f:
            instruction += "\n" + f.read()

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Leda"
                )
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part(text=instruction)]
        )
    )

    mic_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    # Callback function for sounddevice InputStream
    def mic_callback(indata, frames, time, status):
        if status:
            print(f"[สถานะไมค์]: {status}", file=sys.stderr)
        loop.call_soon_threadsafe(mic_queue.put_nowait, indata.copy())

    try:
        # Input Stream: 16kHz, mono, int16 PCM (Required for Gemini Input)
        input_stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="int16",
            callback=mic_callback,
            blocksize=1024
        )
        # Output Stream: 24kHz, mono, int16 PCM (Returned by Gemini Output)
        output_stream = sd.OutputStream(
            samplerate=24000,
            channels=1,
            dtype="int16"
        )
        
        with input_stream, output_stream:
            print("\n📶 กำลังเชื่อมต่อสายตรงหาเฟิส...")
            async with client.aio.live.connect(model=MODEL, config=config) as session:
                print("🎙️ เชื่อมต่อสำเร็จ! คุยกับเฟิสได้เลยแก...")
                
                in_task = asyncio.create_task(audio_input_task(session, mic_queue))
                out_task = asyncio.create_task(audio_output_task(session, output_stream))
                
                await asyncio.gather(in_task, out_task)

    except KeyboardInterrupt:
        print("\n👋 วางสายเรียบร้อยแล้วนะแก เจอกันรอบหน้า!")
    except Exception as e:
        print(f"\n[ระบบ]: เกิดข้อผิดพลาดในเซสชัน: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 วางสายเรียบร้อยแล้วนะแก เจอกันรอบหน้า!")
