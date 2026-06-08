import os
import uuid
import textwrap
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

from app.models import Video
from app.schemas import VideoRenderRequest, VideoResponse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Script, User, Audio
from app.schemas import (
    ScriptGenerateRequest,
    ScriptResponse,
    VoiceGenerateRequest,
    AudioResponse,
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
def generate_mock_voice(
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

    if payload.script_id:
        script = (
            db.query(Script)
            .filter(
                Script.id == payload.script_id,
                Script.project_id == payload.project_id,
                Script.user_id == current_user.id,
            )
            .first()
        )

        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

    credits_needed = max(1, len(payload.text) // 500)

    if current_user.credits < credits_needed:
        raise HTTPException(status_code=402, detail="Not enough credits")

    mock_audio_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

    audio = Audio(
        project_id=payload.project_id,
        user_id=current_user.id,
        script_id=payload.script_id,
        text=payload.text,
        voice_name=payload.voice_name,
        audio_url=mock_audio_url,
        credits_used=credits_needed,
        duration_seconds=30,
    )

    current_user.credits -= credits_needed

    db.add(audio)
    db.commit()
    db.refresh(audio)

    return audio
