import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

import model_router

def test_routing():
    print("=== Testing Model Router Routing Logic ===")
    
    # Test Cream (Gemini Pro)
    cream_type, cream_name = model_router.get_routing_info("cream")
    print(f"Cream routing: type={cream_type}, model_name={cream_name}")
    
    # Test Ray (Claude Sonnet)
    ray_type, ray_name = model_router.get_routing_info("ray")
    print(f"Ray routing: type={ray_type}, model_name={ray_name}")
    
    # Test Q (Claude Sonnet)
    q_type, q_name = model_router.get_routing_info("q")
    print(f"Q routing: type={q_type}, model_name={q_name}")
    
    # Test Chris (Claude Opus)
    chris_type, chris_name = model_router.get_routing_info("chris")
    print(f"Chris routing: type={chris_type}, model_name={chris_name}")
    
    print("\n=== Testing Chat Session (Fallback Mode) ===")
    try:
        chat = model_router.get_chat_session("q", "คุณคือคิว คุยสั้นๆ ทักทายพี่เก่ง")
        res = chat.send_message("ทดสอบระบบนำร่องของคิวหน่อยครับ")
        print(f"Response: {res.text[:100]}...")
    except Exception as e:
        print(f"Failed chat: {e}")

if __name__ == "__main__":
    test_routing()
