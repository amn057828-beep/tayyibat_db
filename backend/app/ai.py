import os
import uuid
import textwrap
import subprocess
import requests

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
import edge_tts

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Script, User, Audio, Video
from app.schemas import (
    ScriptGenerateRequest,
    ScriptResponse,
    VoiceGenerateRequest,
    AudioResponse,
    VideoRenderRequest,
    VideoResponse,
)
from app.dependencies import get_current_user


router = APIRouter(prefix="/ai", tags=["AI"])


def generate_script_template(topic: str, language: str, style: str, duration: int):
    if language == "en":
        title = f"How to understand {topic} in a simple way"
        hook = f"Have you ever wondered why {topic} matters today?"
        content = f"""
Have you ever wondered why {topic} has become so important?

In this short video, we will explain the idea in a simple and practical way.

First, {topic} is not just a trend. It is a real opportunity for people who want to learn, grow, and create value.

Second, the best way to benefit from it is to start small. Learn the basics, test simple ideas, and improve step by step.

Third, avoid copying others blindly. Focus on your audience, your message, and the problem you are solving.

In conclusion, {topic} can become a powerful tool if you use it with clarity, patience, and consistency.

Follow for more practical content.
""".strip()
        hashtags = "#content #business #creator #ai"
    else:
        title = f"كيف تفهم {topic} بطريقة بسيطة"
        hook = f"هل تساءلت يوماً لماذا أصبح موضوع {topic} مهماً لهذه الدرجة؟"
        content = f"""
هل تساءلت يوماً لماذا أصبح موضوع {topic} مهماً لهذه الدرجة؟

في هذا الفيديو القصير، سنشرح الفكرة بطريقة بسيطة وعملية.

أولاً، {topic} ليس مجرد ترند عابر، بل فرصة حقيقية لكل شخص يريد أن يتعلم أو يطور نفسه أو يصنع محتوى مفيداً.

ثانياً، أفضل طريقة للاستفادة من {topic} هي أن تبدأ بخطوات صغيرة. لا تنتظر أن تعرف كل شيء، ابدأ بالتجربة، ثم طوّر نفسك مع الوقت.

ثالثاً، لا تقلد الآخرين بشكل أعمى. حاول أن تفهم جمهورك، وتعرف ما المشكلة التي تريد حلها، وما القيمة التي ستقدمها لهم.

وفي النهاية، تذكر أن النجاح لا يأتي من الفكرة وحدها، بل من الاستمرار، والتجربة، وتحسين المحتوى يوماً بعد يوم.

تابعنا للمزيد من الأفكار العملية.
""".strip()
        hashtags = "#صناعة_المحتوى #ذكاء_اصطناعي #تسويق #مشاريع"

    return {
        "title": title,
        "hook": hook,
        "content": content,
        "hashtags": hashtags,
    }


@router.post("/script", response_model=ScriptResponse)
def generate_script(
    payload: ScriptGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    generated = generate_script_template(
        topic=payload.topic,
        language=payload.language,
        style=payload.style,
        duration=payload.duration,
    )

    project_id = getattr(payload, "project_id", None)

    if project_id:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.user_id == current_user.id)
            .first()
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project.status = "COMPLETED"
    else:
        project = Project(
            user_id=current_user.id,
            title=generated["title"],
            type="SCRIPT",
            status="COMPLETED",
            description=f"AI generated script about {payload.topic}",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

    script = Script(
        project_id=project.id,
        user_id=current_user.id,
        title=generated["title"],
        hook=generated["hook"],
        content=generated["content"],
        language=payload.language,
        hashtags=generated["hashtags"],
    )

    db.add(script)
    db.commit()
    db.refresh(script)

    return script


@router.post("/voice/mock", response_model=AudioResponse)
async def generate_mock_voice(
    payload: VoiceGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.user_id == current_user.id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    credits_needed = max(1, len(payload.text) // 500)

    if current_user.credits < credits_needed:
        raise HTTPException(status_code=402, detail="Not enough credits")

    os.makedirs("generated", exist_ok=True)

    file_id = str(uuid.uuid4())
    audio_path = f"generated/{file_id}.mp3"

    voice_map = {
        "arabic_default": "ar-SA-HamedNeural",
        "arabic_male": "ar-SA-HamedNeural",
        "arabic_female": "ar-SA-ZariyahNeural",
        "english_male": "en-US-GuyNeural",
        "english_female": "en-US-JennyNeural",
    }

    selected_voice = voice_map.get(payload.voice_name, "ar-SA-HamedNeural")

    communicate = edge_tts.Communicate(
        text=payload.text,
        voice=selected_voice,
    )

    await communicate.save(audio_path)

    audio_url = f"/generated/{file_id}.mp3"

    audio = Audio(
        project_id=payload.project_id,
        user_id=current_user.id,
        script_id=payload.script_id,
        text=payload.text,
        voice_name=payload.voice_name,
        audio_url=audio_url,
        credits_used=credits_needed,
        duration_seconds=30,
    )

    current_user.credits -= credits_needed

    db.add(audio)
    db.commit()
    db.refresh(audio)

    return audio


@router.post("/video/render", response_model=VideoResponse)
def render_video(
    payload: VideoRenderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.user_id == current_user.id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    credits_needed = 2

    if current_user.credits < credits_needed:
        raise HTTPException(status_code=402, detail="Not enough credits")

    os.makedirs("generated", exist_ok=True)

    file_id = str(uuid.uuid4())
    image_path = f"generated/{file_id}.png"
    downloaded_audio_path = f"generated/{file_id}.mp3"
    video_path = f"generated/{file_id}.mp4"

    # Resolve audio source
    if payload.audio_url.startswith("/generated/"):
        local_audio_path = payload.audio_url.replace("/generated/", "generated/", 1)
    elif "/generated/" in payload.audio_url:
        local_audio_path = "generated/" + payload.audio_url.split("/generated/")[-1]
    else:
        audio_response = requests.get(payload.audio_url, timeout=30)
        if audio_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download audio")

        with open(downloaded_audio_path, "wb") as f:
            f.write(audio_response.content)

        local_audio_path = downloaded_audio_path

    if not os.path.exists(local_audio_path):
        raise HTTPException(status_code=400, detail="Audio file not found on server")

    width, height = 1280, 720
    image = Image.new("RGB", (width, height), color=(15, 23, 42))
    draw = ImageDraw.Draw(image)

    try:
        font_title = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            56,
        )
        font_text = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            34,
        )
    except Exception:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    title = payload.title[:80]
    wrapped_text = "\n".join(textwrap.wrap(payload.text[:500], width=45))

    draw.text((80, 80), title, fill=(255, 255, 255), font=font_title)
    draw.text((80, 200), wrapped_text, fill=(203, 213, 225), font=font_text)

    image.save(image_path)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    command = [
        ffmpeg,
        "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", local_audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        video_path,
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"FFmpeg failed: {exc.stderr[-1000:]}",
        )

    public_url = f"/generated/{file_id}.mp4"

    video = Video(
        project_id=payload.project_id,
        user_id=current_user.id,
        script_id=payload.script_id,
        audio_id=payload.audio_id,
        title=payload.title,
        video_url=public_url,
        credits_used=credits_needed,
        duration_seconds=30,
    )

    current_user.credits -= credits_needed

    db.add(video)
    db.commit()
    db.refresh(video)

    return video
