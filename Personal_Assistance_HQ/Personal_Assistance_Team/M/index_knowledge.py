"""
🧑‍🎨 เอ็ม (M) — Knowledge Base Indexer (Google Embedding Edition)
หน้าที่: สแกนไฟล์ .md ทั้งหมดในโปรเจกต์แล้ว Index เข้า ChromaDB
ใช้ Google text-embedding-004 ซึ่งรองรับภาษาไทยได้ดีเยี่ยม!
วิธีรัน: python Personal_Assistance_Team/M/index_knowledge.py
"""

import os
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'db')
IGNORE_DIRS = {'.git', 'venv', '__pycache__', '.gemini', 'knowledge_base'}

load_dotenv(os.path.join(BASE_DIR, '.env'))
API_KEY = os.getenv('GOOGLE_API_KEY')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Custom Google Embedding Function
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class GoogleEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, model: str = "models/gemini-embedding-001"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def __call__(self, input: Documents) -> Embeddings:
        import time
        # Try batch embedding first (much faster and saves API calls)
        try:
            result = self.client.models.embed_content(
                model=self.model,
                contents=input,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            return [emb.values for emb in result.embeddings]
        except Exception as e:
            print(f"⚠️ Batch embedding failed or rate limited ({e}). Falling back to sequential with rate limiting...")
            
        embeddings = []
        for text in input:
            retries = 5
            while retries > 0:
                try:
                    result = self.client.models.embed_content(
                        model=self.model,
                        contents=text,
                        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
                    )
                    embeddings.append(result.embeddings[0].values)
                    time.sleep(4.5) # sleep 4.5 seconds to respect 15 RPM limit
                    break
                except Exception as ex:
                    if "429" in str(ex) or "RESOURCE_EXHAUSTED" in str(ex):
                        print("⏳ Resource exhausted. Sleeping 30 seconds before retry...")
                        time.sleep(30.0)
                        retries -= 1
                    else:
                        raise ex
            if retries == 0:
                raise Exception("❌ Failed to embed document after multiple retries due to quota limitations.")
        return embeddings


def get_all_md_files():
    """สแกนหาไฟล์ .md ทั้งหมดในโปรเจกต์"""
    md_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith('.md'):
                md_files.append(os.path.join(root, f))
    return md_files

def chunk_text(text, chunk_size=500, overlap=50):
    """ตัดข้อความเป็นชิ้นเล็กๆ เพื่อให้ค้นหาแม่นยำขึ้น"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

def main():
    if not API_KEY:
        print("❌ ไม่พบ GOOGLE_API_KEY ใน .env นะแก!")
        return

    print("🧑‍🎨 เอ็มกำลัง Index ข้อมูลเข้า Knowledge Base (Google Embedding)...")
    os.makedirs(DB_PATH, exist_ok=True)

    embed_fn = GoogleEmbeddingFunction(api_key=API_KEY)

    client = chromadb.PersistentClient(path=DB_PATH)

    # ลบ Collection เก่าทิ้งก่อน (Re-index ใหม่สะอาด)
    try:
        client.delete_collection("1st_agent_kb")
        print("🗑️  ลบ Index เก่าทิ้งแล้ว")
    except:
        pass

    collection = client.create_collection(
        name="1st_agent_kb",
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"}
    )

    md_files = get_all_md_files()
    print(f"📂 พบไฟล์ .md จำนวน {len(md_files)} ไฟล์\n")

    all_docs, all_ids, all_metadatas = [], [], []

    for filepath in md_files:
        relative_path = filepath.replace(BASE_DIR, '').strip(os.sep)
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                doc_id = f"{relative_path}__chunk{i}"
                all_docs.append(chunk)
                all_ids.append(doc_id)
                all_metadatas.append({
                    "source_file": relative_path,
                    "filename": filename,
                    "chunk_index": i
                })
            print(f"  ✅ {relative_path} ({len(chunks)} chunks)")
        except Exception as e:
            print(f"  ❌ Error: {relative_path} — {e}")

    if all_docs:
        print(f"\n⚡ กำลัง Embed {len(all_docs)} chunks ด้วย Google API...")
        batch_size = 20  # Google API limit per batch
        for i in range(0, len(all_docs), batch_size):
            collection.add(
                documents=all_docs[i:i+batch_size],
                ids=all_ids[i:i+batch_size],
                metadatas=all_metadatas[i:i+batch_size]
            )
            print(f"  📦 Batch {i//batch_size + 1}/{(len(all_docs)-1)//batch_size + 1} เสร็จ")

    print(f"\n🏁 Index เสร็จสมบูรณ์! รวม {len(all_docs)} chunks จาก {len(md_files)} ไฟล์")
    print(f"💾 บันทึกไว้ที่: {DB_PATH}")

if __name__ == "__main__":
    main()
