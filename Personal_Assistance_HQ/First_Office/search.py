"""
🔍 Knowledge Base Search — ระบบค้นหาของทีม 1st Agent (Google Embedding Edition)
วิธีใช้: python search.py "คำถามที่อยากรู้"
ตัวอย่าง: python search.py "ถ้า Token หมดอายุต้องทำอะไร"
"""

import sys
import os
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'db')

load_dotenv(os.path.join(BASE_DIR, '.env'))
API_KEY = os.getenv('GOOGLE_API_KEY')

class GoogleEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, model: str = "models/gemini-embedding-2"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            result = self.client.models.embed_content(
                model=self.model,
                contents=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
            )
            embeddings.append(result.embeddings[0].values)
        return embeddings

def search(query: str, n_results: int = 3):
    if not API_KEY:
        print("❌ ไม่พบ GOOGLE_API_KEY ใน .env นะแก!")
        return

    if not os.path.exists(DB_PATH):
        print("❌ ยังไม่มี Knowledge Base! ให้เอ็มรัน index_knowledge.py ก่อนนะแก")
        return

    embed_fn = GoogleEmbeddingFunction(api_key=API_KEY)
    client = chromadb.PersistentClient(path=DB_PATH)

    try:
        collection = client.get_collection("1st_agent_kb", embedding_function=embed_fn)
    except Exception:
        print("❌ ไม่พบ Collection! ให้เอ็มรัน index_knowledge.py ก่อนนะแก")
        return

    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    docs = results['documents'][0]
    metas = results['metadatas'][0]
    distances = results['distances'][0]

    print(f"\n🔍 ค้นหา: \"{query}\"")
    print("=" * 60)

    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
        relevance = round((1 - dist) * 100, 1)
        print(f"\n📌 ผลลัพธ์ #{i+1}  |  ความเกี่ยวข้อง: {relevance}%")
        print(f"📁 แหล่งที่มา: {meta['source_file']}")
        print("-" * 40)
        preview = doc[:300] + "..." if len(doc) > 300 else doc
        print(preview)

    print("\n" + "=" * 60)

def main():
    if len(sys.argv) < 2:
        print("🔍 วิธีใช้: python search.py 'คำถามของแก'")
        print("ตัวอย่าง:")
        print("  python search.py 'วินต้องทำอะไรถ้า token หมดอายุ'")
        print("  python search.py 'เจนต้องทำอะไรตอนขึ้นเดือนใหม่'")
        print("  python search.py 'เอ็มมีหน้าที่อะไรบ้าง'")
        return

    query = ' '.join(sys.argv[1:])
    search(query)

if __name__ == "__main__":
    main()
