import os
import sys
import warnings
import asyncio
import threading
import queue
from dotenv import load_dotenv

# Silence legacy deprecation warnings from Google Generative AI
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Ensure environment variables are loaded from the project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Import API Clients
HAS_GEMINI = False
try:
    import google.generativeai as legacy_genai
    legacy_genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    HAS_GEMINI = True
except ImportError:
    pass

HAS_ANTIGRAVITY = False
# try:
#     import google.antigravity
#     from google.antigravity import Agent as AgtAgent, LocalAgentConfig as AgtLocalAgentConfig
#     HAS_ANTIGRAVITY = True
# except ImportError:
#     pass

HAS_ANTHROPIC = False
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    pass

# Default Model configurations (Can be overridden in .env)
GEMINI_PRO_MODEL = os.environ.get("GEMINI_PRO_MODEL_NAME", "gemini-2.5-pro")
GEMINI_FLASH_MODEL = os.environ.get("GEMINI_FLASH_MODEL_NAME", "gemini-2.5-flash")
CLAUDE_SONNET_MODEL = os.environ.get("CLAUDE_SONNET_MODEL_NAME", "claude-3-5-sonnet-latest")
CLAUDE_OPUS_MODEL = os.environ.get("CLAUDE_OPUS_MODEL_NAME", "claude-3-opus-latest")

# Model routing rules mapping agent names to target brains
# Format: {agent_name: (model_type, model_name)}
# model_type: 'gemini_pro', 'claude_sonnet', 'claude_opus'
AGENT_ROUTING = {
    # 1. สแกนเอกสาร / วิเคราะห์ข้อมูลยาว (Gemini Pro)
    "cream": "gemini_pro",
    "น้องครีม": "gemini_pro",
    "researcher": "gemini_pro",
    "pie": "gemini_pro",
    "น้องปาย": "gemini_pro",
    "analyst": "gemini_pro",
    "or": "gemini_pro",
    "น้องออ": "gemini_pro",
    "auditor": "gemini_pro",
    
    # 2. เขียนบทความ / เขียนโค้ด UI (Claude Sonnet)
    "ray": "claude_sonnet",
    "น้องเรย์": "claude_sonnet",
    "writer": "claude_sonnet",
    "m": "claude_sonnet",
    "น้องเอ็ม": "claude_sonnet",
    "d": "claude_sonnet",
    "น้องดี": "claude_sonnet",
    "designer": "claude_sonnet",
    "nam": "claude_sonnet",
    "น้องน้ำ": "claude_sonnet",
    "creative": "claude_sonnet",
    "music": "claude_sonnet",
    "น้องมิวสิค": "claude_sonnet",
    "marketer": "claude_sonnet",
    "deer": "claude_sonnet",
    "น้องเดียร์": "claude_sonnet",
    "cri": "claude_sonnet",
    "น้องคริ": "claude_sonnet",
    "critic": "claude_sonnet",
    "q": "claude_sonnet",
    "น้องคิว": "claude_sonnet",
    "backend": "claude_sonnet",
    "win": "claude_sonnet",
    "น้องวิน": "claude_sonnet",
    
    # 3. วิเคราะห์นโยบายตัดสินใจหลัก (Claude Opus)
    "first": "claude_opus",
    "เฟิส": "claude_opus",
    "chris": "claude_opus",
    "พี่คริส": "claude_opus",
    "director": "claude_opus",
    "storyboard": "claude_opus"
}

def get_routing_info(agent_name):
    """
    Determines model type and exact model name for a given agent.
    Falls back to Gemini Flash if keys or libs are missing.
    """
    agent_key = str(agent_name).lower().strip()
    target_type = AGENT_ROUTING.get(agent_key, "claude_sonnet") # default to Sonnet if unknown
    
    google_key = os.environ.get("GOOGLE_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    # Check if we should use Claude and if we have the key & library
    if "claude" in target_type:
        if HAS_ANTHROPIC and anthropic_key:
            if target_type == "claude_opus":
                return "anthropic", CLAUDE_OPUS_MODEL
            else:
                return "anthropic", CLAUDE_SONNET_MODEL
        else:
            # Fallback to Gemini if Anthropic key/lib is missing
            fallback_model = GEMINI_PRO_MODEL if target_type == "claude_opus" else GEMINI_FLASH_MODEL
            # Print warning to stderr so it doesn't pollute standard text streams but stays visible in console
            print(f"[ModelRouter Warning]: คีย์ ANTHROPIC_API_KEY หรือไลบรารีไม่พร้อมใช้งานสำหรับ '{agent_name}'. สลับไปใช้ Gemini ({fallback_model}) อัตโนมัติ", file=sys.stderr)
            return "gemini", fallback_model
            
    # For Gemini Pro
    if target_type == "gemini_pro":
        if HAS_GEMINI and google_key:
            return "gemini", GEMINI_PRO_MODEL
        else:
            print(f"[ModelRouter Warning]: ไม่พบคีย์ Google API หรือไลบรารีสำหรับ '{agent_name}'. สลับไปใช้โมเดลพื้นฐาน", file=sys.stderr)
            return "gemini", GEMINI_FLASH_MODEL
            
    return "gemini", GEMINI_FLASH_MODEL


def run_async_sync(coro):
    """Runs an async coroutine synchronously, even if called from a running event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, we can just run it
        return asyncio.run(coro)
    
    # A loop is running, run the coroutine in a separate thread and wait for result
    q = queue.Queue()
    
    def worker():
        try:
            result = asyncio.run(coro)
            q.put((True, result))
        except Exception as ex:
            q.put((False, ex))
            
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    
    success, val = q.get()
    if success:
        return val
    else:
        raise val


class ModelResponse:
    """Wrapper to mimic the Gemini API response structure (.text)"""
    def __init__(self, text):
        self.text = text


class UnifiedChatSession:
    """Wrapper to provide a unified chat session API across Gemini and Claude"""
    def __init__(self, agent_name, system_instruction=""):
        self.agent_name = agent_name
        self.system_instruction = system_instruction
        self.history = []  # format: [{"role": "user"|"assistant", "content": "..."}]
        
        self.model_type, self.model_name = get_routing_info(agent_name)
        self.gemini_chat = None
        self.anthropic_client = None
        
        # Antigravity SDK
        self.agt_agent = None
        
        self._init_session()
        
    def _init_session(self):
        if self.model_type == "gemini":
            if HAS_ANTIGRAVITY:
                # We will initialize it lazily or here. Let's do it lazily in _send_agt_message
                pass
            elif HAS_GEMINI:
                model = legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.system_instruction
                )
                self.gemini_chat = model.start_chat()
            else:
                raise RuntimeError("ไม่สามารถเริ่มการเชื่อมต่อกับ Gemini ได้เนื่องจากไลบรารีไม่ถูกติดตั้ง")
        elif self.model_type == "anthropic":
            if HAS_ANTHROPIC:
                self.anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            else:
                raise RuntimeError("ไม่สามารถเริ่มการเชื่อมต่อกับ Anthropic ได้เนื่องจากไลบรารีไม่ถูกติดตั้ง")

    async def _init_agt_agent(self):
        # Determine skills paths based on agent name or load globally
        skills_paths = []
        
        # Ensure GEMINI_API_KEY is populated
        if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
            os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
            
        # Register Coder Studio skills
        q_skills = os.path.join(PROJECT_ROOT, "Coder_Studio", "Q", "skills")
        if os.path.isdir(q_skills):
            skills_paths.append(q_skills)
            
        # Register Win skills if they exist
        win_skills = os.path.join(PROJECT_ROOT, "Personal_Assistance_HQ", "Personal_Assistance_Team", "Team_Desks", "Win", "skills")
        if os.path.isdir(win_skills):
            skills_paths.append(win_skills)
            
        config = AgtLocalAgentConfig(
            model=self.model_name,
            system_instructions=self.system_instruction,
            skills_paths=skills_paths if skills_paths else None
        )
        
        self.agt_agent = AgtAgent(config=config)
        await self.agt_agent.__aenter__()

    async def _send_agt_message(self, message_text):
        if not self.agt_agent:
            await self._init_agt_agent()
        response = await self.agt_agent.chat(message_text)
        return await response.text()

    def send_message(self, message_text):
        if self.model_type == "gemini":
            if HAS_ANTIGRAVITY:
                try:
                    res_text = run_async_sync(self._send_agt_message(message_text))
                    return ModelResponse(res_text)
                except Exception as e:
                    print(f"[ModelRouter Warning]: Antigravity Agent error: {e}. Fallback to legacy gemini", file=sys.stderr)
            
            # Legacy Gemini or Fallback
            if not self.gemini_chat and HAS_GEMINI:
                model = legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.system_instruction
                )
                self.gemini_chat = model.start_chat()
            
            try:
                response = self.gemini_chat.send_message(message_text)
                return ModelResponse(response.text)
            except Exception as e:
                # Fallback to flash if Pro fails
                if self.model_name != GEMINI_FLASH_MODEL:
                    print(f"[ModelRouter Fallback]: Gemini Pro เกิดข้อผิดพลาด: {e}. สลับไปใช้ Flash", file=sys.stderr)
                    self.model_name = GEMINI_FLASH_MODEL
                    model = legacy_genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=self.system_instruction
                    )
                    self.gemini_chat = model.start_chat()
                    response = self.gemini_chat.send_message(message_text)
                    return ModelResponse(response.text)
                else:
                    raise e
        else:
            # Anthropic Chat
            self.history.append({"role": "user", "content": message_text})
            try:
                kwargs = {
                    "model": self.model_name,
                    "max_tokens": 4000,
                    "messages": self.history
                }
                if self.system_instruction:
                    kwargs["system"] = self.system_instruction
                
                if "sonnet" in self.model_name and ("3-7" in self.model_name or "latest" in self.model_name):
                    kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2048}
                    kwargs["max_tokens"] = 8000
                
                message = self.anthropic_client.messages.create(**kwargs)
                response_text = ""
                for content_block in message.content:
                    if content_block.type == "text":
                        response_text += content_block.text
                
                self.history.append({"role": "assistant", "content": response_text})
                return ModelResponse(response_text)
            except Exception as e:
                print(f"[ModelRouter Fallback]: Claude API เกิดข้อผิดพลาด: {e}. สลับไปใช้งาน Gemini อัตโนมัติ", file=sys.stderr)
                self.model_type = "gemini"
                self.model_name = GEMINI_FLASH_MODEL
                
                if HAS_ANTIGRAVITY:
                    try:
                        res_text = run_async_sync(self._send_agt_message(message_text))
                        return ModelResponse(res_text)
                    except Exception as agt_err:
                        print(f"[ModelRouter Fallback Warning]: Antigravity fallback error: {agt_err}", file=sys.stderr)
                
                if HAS_GEMINI:
                    model = legacy_genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=self.system_instruction
                    )
                    self.gemini_chat = model.start_chat()
                    response = self.gemini_chat.send_message(message_text)
                    return ModelResponse(response.text)
                else:
                    raise e

    def __del__(self):
        # Clean up agent session on delete
        if self.agt_agent:
            try:
                run_async_sync(self.agt_agent.__aexit__(None, None, None))
            except Exception:
                pass


class UnifiedModel:
    """Wrapper to provide a unified model interface for single-turn generation"""
    def __init__(self, agent_name, system_instruction=""):
        self.agent_name = agent_name
        self.system_instruction = system_instruction
        self.model_type, self.model_name = get_routing_info(agent_name)

    async def _generate_agt_content(self, prompt):
        # Ensure GEMINI_API_KEY is populated
        if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
            os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
            
        config = AgtLocalAgentConfig(
            model=self.model_name,
            system_instructions=self.system_instruction
        )
        async with AgtAgent(config=config) as agent:
            response = await agent.chat(prompt)
            return await response.text()

    def generate_content(self, prompt):
        if self.model_type == "gemini":
            if HAS_ANTIGRAVITY:
                try:
                    res_text = run_async_sync(self._generate_agt_content(prompt))
                    return ModelResponse(res_text)
                except Exception as e:
                    print(f"[ModelRouter Warning]: Antigravity Agent error: {e}. Fallback to legacy gemini", file=sys.stderr)
            
            try:
                model = legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.system_instruction
                )
                response = model.generate_content(prompt)
                return ModelResponse(response.text)
            except Exception as e:
                if self.model_name != GEMINI_FLASH_MODEL:
                    print(f"[ModelRouter Fallback]: Gemini Pro เกิดข้อผิดพลาด: {e}. สลับไปใช้ Flash", file=sys.stderr)
                    model = legacy_genai.GenerativeModel(
                        model_name=GEMINI_FLASH_MODEL,
                        system_instruction=self.system_instruction
                    )
                    response = model.generate_content(prompt)
                    return ModelResponse(response.text)
                else:
                    raise e
        else:
            # Anthropic single turn
            if not HAS_ANTHROPIC:
                raise RuntimeError("ไม่สามารถเชื่อมต่อ Anthropic ได้เนื่องจากไลบรารีไม่ถูกติดตั้ง")
            
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            try:
                messages = [{"role": "user", "content": prompt}]
                kwargs = {
                    "model": self.model_name,
                    "max_tokens": 4000,
                    "messages": messages
                }
                if self.system_instruction:
                    kwargs["system"] = self.system_instruction
                    
                if "sonnet" in self.model_name and ("3-7" in self.model_name or "latest" in self.model_name):
                    kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2048}
                    kwargs["max_tokens"] = 8000
                    
                message = client.messages.create(**kwargs)
                response_text = ""
                for content_block in message.content:
                    if content_block.type == "text":
                        response_text += content_block.text
                return ModelResponse(response_text)
            except Exception as e:
                print(f"[ModelRouter Fallback]: Claude API เกิดข้อผิดพลาด: {e}. สลับไปใช้งาน Gemini อัตโนมัติ", file=sys.stderr)
                
                if HAS_ANTIGRAVITY:
                    try:
                        res_text = run_async_sync(self._generate_agt_content(prompt))
                        return ModelResponse(res_text)
                    except Exception as agt_err:
                        print(f"[ModelRouter Fallback Warning]: Antigravity fallback error: {agt_err}", file=sys.stderr)
                
                model = legacy_genai.GenerativeModel(
                    model_name=GEMINI_FLASH_MODEL,
                    system_instruction=self.system_instruction
                )
                response = model.generate_content(prompt)
                return ModelResponse(response.text)


# Convenience functions for quick access
def get_chat_session(agent_name, system_instruction=""):
    return UnifiedChatSession(agent_name, system_instruction)

def get_model(agent_name, system_instruction=""):
    return UnifiedModel(agent_name, system_instruction)
