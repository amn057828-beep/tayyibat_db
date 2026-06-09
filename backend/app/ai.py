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
    return {
        "title": f"تأملات في {topic}",
        "hook": f"ما الذي يربطنا بـ {topic} في لحظات صمتنا؟",
        "content": "هل تساءلت يوماً عن أثر هذا الأمر في أعماقك؟\n\nالحياة تجري بنا ونحن نبحث عن إجابات.\n\nربما تكمن الحقيقة في السؤال ذاته.",
        "hashtags": "#تأمل #عمق #فكر"
    }


def generate_script_with_groq(topic: str, language: str, style: str, duration: int, content_type: str = "general"):
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        return generate_script_template(topic, language, style, duration)

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)

        content_guides = {
            "general": "اكتب محتوى جذاباً وعميقاً بأسلوب سينمائي.",
            "psychology": "اكتب بأسلوب نفسي عميق. ركز على المشاعر، الخوف، الدوافع، الصراعات الداخلية، واجعل الخطاب موجهاً للمشاهد مباشرة.",
            "philosophy": "اكتب بأسلوب فلسفي وتأملي. ركز على المعنى، الوجود، الاختيار، الزمن، والأسئلة التي تهز القناعات.",
            "business": "اكتب بأسلوب عملي لرواد الأعمال. ركز على القرارات، الأخطاء الشائعة، المال، المخاطرة، والانضباط.",
            "technology": "اكتب بأسلوب تقني مبسط. استخدم أمثلة واقعية، وركز على الفائدة العملية لا المصطلحات المعقدة.",
            "religion": "اكتب بأسلوب روحي وتأملي عميق. ركز على الطمأنينة، محاسبة النفس، المعنى، الأخلاق، والاتصال بالله دون ادعاءات مطلقة عن الغيب. تجنب التكرار والوعظ المباشر.",
        }

        content_guide = content_guides.get(content_type, content_guides["general"])

        prompt = f"""
أنت كاتب محتوى عربي من الطراز الأول ومتخصص في كتابة سكربتات الفيديو الطويلة والاحترافية لليوتيوب والمنصات التعليمية والثقافية والفكرية. 
مهمتك ليست تلخيص الموضوع أو تعريفه، بل بناء رحلة فكرية متكاملة تجعل المشاهد يستمر حتى نهاية الفيديو.

الموضوع: {topic}
نوع المحتوى: {content_type}
النمط: {style}
المدة المستهدفة: {duration} ثانية
تعليمات خاصة بنوع المحتوى: {content_guide}

القواعد الإلزامية:
- اكتب بالعربية الفصحى السليمة فقط.
- ممنوع استخدام أي كلمة أو حرف أو رمز من أي لغة أخرى.
- إذا ظهر أي حرف غير عربي فأعد كتابة النص بالكامل.
- لا تستخدم أسلوب المقالات المدرسية.
- لا تستخدم عبارات مثل: "في هذا الفيديو سنتحدث"، "اليوم سوف نتحدث"، "هل تعلم"، "يجب علينا"، "ينبغي علينا".
- لا تقدم تعريفات مباشرة ومملة.
- ابدأ بسؤال عميق أو مفارقة فكرية أو حقيقة تثير الفضول.
- اجعل المشاهد يشعر أن الحديث موجه إليه شخصياً.
- اجعل كل فقرة تضيف فكرة جديدة.
- استخدم أمثلة واقعية وتشبيهات وصوراً ذهنية.
- انتقل بين الأفكار بشكل طبيعي ومتدرج.
- اجعل النص مناسباً للإلقاء الصوتي الاحترافي.
- لا تكتب كمقال.
- اكتب كسيناريو صوتي يُسمع لا كنص يُقرأ.
- اجعل الانتقال بين الفقرات طبيعياً وسلساً.
- اجعل النهاية أقوى فقرة في السكربت.

هيكل السكربت:
1- عنوان جذاب وقوي.
2- افتتاحية تشد الانتباه خلال أول 20 ثانية.
3- تمهيد للفكرة الرئيسية.
4- عرض الأفكار الأساسية بعمق وتسلسل منطقي.
5- أمثلة أو إسقاطات واقعية.
6- استنتاج أو رؤية أعمق للموضوع.
7- خاتمة مؤثرة تترك أثراً فكرياً أو شعورياً.
8- هاشتاقات مناسبة.

أعد النتيجة بصيغة JSON فقط:
{{
"title": "عنوان الفيديو",
"hook": "الافتتاحية",
"content": "السكربت الكامل",
"hashtags": "#هاشتاق1 #هاشتاق2 #هاشتاق3"
}}
"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت كاتب محتوى عربي مبدع. التزم بالعربية الفصحى في كل حرف."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.85,
            top_p=0.9,
            max_tokens=2500,
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
