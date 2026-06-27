from pydantic import BaseModel, Field
from typing import Optional, List, Any, Union


class ConversationCreate(BaseModel):
    title: str = "新对话"
    model: str = "agnes-2.0-flash"


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None


class MessageCreate(BaseModel):
    content: Union[str, List[Any]]
    role: str = "user"


class ChatRequest(BaseModel):
    content: Union[str, List[Any]]
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = True
    enable_thinking: Optional[bool] = None


class RegenerateRequest(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = True
    enable_thinking: Optional[bool] = None


class ImageGenerateRequest(BaseModel):
    model: str = "agnes-image-2.1-flash"
    prompt: str
    size: str = "1024x768"
    mode: str = "text2img"
    images: Optional[List[str]] = None
    return_base64: bool = False
    response_format: str = "url"


class AgnesBaseUrlUpdate(BaseModel):
    base_url: str


class ApiKeyCreate(BaseModel):
    name: str
    api_key: str
    activate: bool = True


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None


class VideoGenerateRequest(BaseModel):
    model: str = "agnes-video-v2.0"
    prompt: str
    mode: str = "text2video"
    negative_prompt: Optional[str] = None
    image: Optional[Union[str, List[str]]] = None
    images: Optional[List[str]] = None
    width: int = 1280
    height: int = 720
    num_frames: int = 121
    frame_rate: float = 24
    num_inference_steps: Optional[int] = None
    seed: Optional[int] = None
