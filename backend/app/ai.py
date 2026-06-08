import os
import uuid
import json
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
        content = f"Have you ever wondered why {topic} has become so important?\n\nIn this short video, we will explain the idea in a simple and practical way.\n\nFirst, {topic} is not just a trend. It is a real opportunity.\n\nSecond, start small and improve step by step.\n\nThird, focus on your unique value.\n\nFollow for more."
        hashtags = "#content #business #creator #ai"
    else:
        title = f"كيف تفهم {topic} بطريقة بسيطة"
        hook = f"هل تساءلت يوماً لماذا أصبح موضوع {topic} مهماً لهذه الدرجة؟"
        content = f"هل تساءلت يوماً لماذا أصبح موضوع {topic} مهماً لهذه الدرجة؟\n\nفي هذا الفيديو القصير، سنشرح الفكرة بطريقة بسيطة وعملية.\n\nأولاً، {topic} ليس مجرد ترند عابر.\n\nثانياً، ابدأ بخطوات صغيرة وطوّر نفسك.\n\nثالثاً، ركز على القيمة التي تقدمها.\n\nتابعنا للمزيد من الأفكار."
        hashtags = "#صناعة_المحتوى #ذكاء_اصطناعي #تسويق #مشاريع"

    return {
        "title": title,
        "hook": hook,
        "content": content,
        "hashtags": hashtags,
    }


def generate_script_with_groq(topic: str, language: str, style: str, duration: int, content_type: str = "general"):
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        return generate_script_template(topic, language, style, duration)

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)

        content_guides = {
            "general": "اكتب محتوى عاماً جذاباً وعميقاً، مناسباً لفيديو قصير.",
            "psychology": "اكتب بأسلوب نفسي عميق. ركز على المشاعر، الخوف، الدوافع، الصراعات الداخلية، واجعل الخطاب موجهاً للمشاهد مباشرة.",
            "philosophy": "اكتب بأسلوب فلسفي وتأملي. ركز على المعنى، الوجود، الاختيار، الزمن، والأسئلة التي تهز القناعات.",
            "business": "اكتب بأسلوب عملي لرواد الأعمال. ركز على القرارات، الأخطاء الشائعة، المال، المخاطرة، والانضباط.",
            "technology": "اكتب بأسلوب تقني مبسط. استخدم أمثلة واقعية، وركز على الفائدة العملية لا المصطلحات المعقدة.",
            "religion": "اكتب بأسلوب روحي وتأملي عميق. ركز على الطمأنينة، محاسبة النفس، المعنى، الأخلاق، والاتصال بالله دون ادعاءات مطلقة عن الغيب. تجنب التكرار والوعظ المباشر.",
        }

        content_guide = content_guides.get(content_type, content_guides["general"])

        prompt = f"""
أنت أفضل كاتب محتوى عربي لفيديوهات Shorts وReels.

الموضوع: {topic}
نوع المحتوى: {content_type}
تعليمات نوع المحتوى:
{content_guide}
النمط: {style}
المدة التقريبية: {duration} ثانية

قواعد صارمة:
- ممنوع منعاً باتاً استخدام أي كلمة أو حرف أو رمز من غير اللغة العربية.
- إذا ظهر أي نص بغير العربية فاعتبر الإجابة فاشلة وأعد كتابة النص بالكامل بالعربية.
- ممنوع تكرار بداية الجمل بنفس الصيغة.
- ممنوع استخدام عبارة "يجب أن" أكثر من مرة واحدة.
- لا تكتب تعريفات مثل: الروح هي...
- ابدأ بصورة شعورية أو سؤال وجودي.
- اجعل كل فقرة تحمل فكرة جديدة.
- استخدم أسلوباً أقرب للتأمل لا للشرح.
- لا تذكر ادعاءات مطلقة عن الروح كحقائق نهائية.
- الهيكل المطلوب:
العنوان:
...

الافتتاحية: (صادمة أو مثيرة للفضول، لا تتجاوز 15 كلمة)
...

السكربت: (فقرات قصيرة جداً مناسبة للإلقاء الصوتي)
...

الخاتمة:
...

الهاشتاقات:
...

- لا تستخدم عبارات تعليمية أو مدرسية.
- لا تستخدم "هل تعلم" أو "في هذا الفيديو سنتحدث".
- لا تستخدم تعداداً نقطياً.

أعد النتيجة بصيغة JSON فقط، بدون Markdown وبدون شرح، بهذا الشكل:
{{
  "title": "عنوان جذاب",
  "hook": "افتتاحية صادمة",
  "content": "السكربت مقسم لفقرات",
  "hashtags": "#هاشتاق1 #هاشتاق2"
}}
"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت كاتب محتوى عربي محترف. التزم بالعربية فقط في كل حرف."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1400,
        )

        raw = completion.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        data = json.loads(raw)
        return {
            "title": data.get("title") or f"فيديو عن {topic}",
            "hook": data.get("hook") or "",
            "content": data.get("content") or "",
            "hashtags": data.get("hashtags") or "",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"GROQ ERROR: {str(e)}"
        )

@router.post("/script", response_model=ScriptResponse)
def generate_script(
    payload: ScriptGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content_type = getattr(payload, "content_type", "general")
    generated = generate_script_with_groq(
        topic=payload.topic,
        language=payload.language,
        style=payload.style,
        duration=payload.duration,
        content_type=content_type
    )

    project_id = getattr(payload, "project_id", None)
    if project_id:
        project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
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
    project = db.query(Project).filter(Project.id == payload.project_id, Project.user_id == current_user.id).first()
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
    communicate = edge_tts.Communicate(text=payload.text, voice=selected_voice)
    await communicate.save(audio_path)

    audio = Audio(
        project_id=payload.project_id,
        user_id=current_user.id,
        script_id=payload.script_id,
        text=payload.text,
        voice_name=payload.voice_name,
        audio_url=f"/generated/{file_id}.mp3",
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
    project = db.query(Project).filter(Project.id == payload.project_id, Project.user_id == current_user.id).first()
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

    if payload.audio_url.startswith("/generated/"):
        local_audio_path = payload.audio_url.replace("/generated/", "generated/", 1)
    else:
        audio_response = requests.get(payload.audio_url, timeout=30)
        if audio_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download audio")
        with open(downloaded_audio_path, "wb") as f:
            f.write(audio_response.content)
        local_audio_path = downloaded_audio_path

    image = Image.new("RGB", (854, 480), color=(15, 23, 42))
    draw = ImageDraw.Draw(image)
    wrapped_text = "\n".join(textwrap.wrap(payload.text[:500], width=45))
    draw.text((80, 80), payload.title[:80], fill=(255, 255, 255))
    draw.text((80, 200), wrapped_text, fill=(203, 213, 225))
    image.save(image_path)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-y", "-loop", "1", "-framerate", "1", "-i", image_path, "-i", local_audio_path, "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-c:a", "aac", "-b:a", "96k", "-pix_fmt", "yuv420p", "-shortest", "-movflags", "+faststart", video_path]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=f"FFmpeg failed: {exc.stderr[-1000:]}")

    video = Video(
        project_id=payload.project_id,
        user_id=current_user.id,
        script_id=payload.script_id,
        audio_id=payload.audio_id,
        title=payload.title,
        video_url=f"/generated/{file_id}.mp4",
        credits_used=credits_needed,
        duration_seconds=30,
    )
    current_user.credits -= credits_needed
    db.add(video)
    db.commit()
    db.refresh(video)
    return video
