import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # استيراد موديول قراءة الملفات الثابتة
from pydantic import BaseModel
import edge_tts

app = FastAPI(title="AI Content Creator SaaS - Live Backend")

# 1. تفعيل الـ CORS لتسمح لواجهة موقعك (index.html) بالاتصال بالسيرفر دون قيود الأمنية للمتصفح
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # السماح لجميع النطاقات بالاتصال
    allow_credentials=True,
    allow_methods=["*"],  # السماح بجميع العمليات (POST, GET, etc)
    allow_headers=["*"],
)

# 2. إتاحة الملفات الثابتة (للسماح برابط المخرجات مثل ملفات الـ mp3 الموّلدة في الخادم)
app.mount("/static", StaticFiles(directory="."), name="static")

# رابط قاعدة البيانات الخاص بك على رندر
DATABASE_URL = "postgresql://tayyibat_db_user:qE1UqVkJpOnk8gvcCftPykiQc2IeU3LN@dpg-d8ipe4ernols73c06spg-a.ohio-postgres.render.com/tayyibat_db"

# مفتاح SiliconFlow الخاص بك المستدعى عبر متغيرات البيئة (أو القيمة الافتراضية)
SILICONFLOW_API_KEY = os.getenv("SILICON_KEY", "sk-ytqtkfauygoxfdrlvkbatjetpuxbdgogvebbolxdvgsbvdll")


# دالة الاتصال بقاعدة بيانات رندر
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print("خطأ في الاتصال بقاعدة البيانات:", e)
        return None


# تهيئة وإنشاء الجداول تلقائياً في قاعدة بياناتك عند بدء التشغيل
@app.on_event("startup")
def startup_db_init():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # إنشاء جدول حسابات المستخدمين والنقاط
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users_profile (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                credits INT DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # إنشاء جدول لتخزين روابط المحتوى المولد وتتبعه لكل مستخدم
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_content (
                id SERIAL PRIMARY KEY,
                user_email TEXT NOT NULL,
                content_type TEXT NOT NULL,
                prompt TEXT NOT NULL,
                output_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("🚀 تم الاتصال بقاعدة بياناتك وتهيئة الجداول بنجاح هائل!")


# النماذج البرمجية لاستقبال طلبات الويب (Data Models)
class UserRegister(BaseModel):
    username: str
    email: str


class ContentRequest(BaseModel):
    email: str
    prompt: str
    voice_name: str = "ar-EG-ShakirNeural"


# --- 1. API تسجيل مستخدم جديد في قاعدة البيانات ---
@app.post("/api/register/")
async def register_user(user: UserRegister):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="قاعدة البيانات غير متصلة")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users_profile (username, email) VALUES (%s, %s) RETURNING *;",
            (user.username, user.email),
        )
        new_user = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return {
            "status": "success",
            "user": new_user,
            "message": "تم حفظ المستخدم بنجاح!",
        }
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="المستخدم مسجل بالفعل")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. API توليد الصوت المجاني وحفظ العملية ---
@app.post("/api/generate-audio/")
async def generate_audio(request: ContentRequest):
    file_id = request.email.split("@")[0]
    output_filename = f"audio_{file_id}.mp3"
    try:
        # توليد الصوت عبر محرك مايكروسوفت إيدج المجاني
        communicate = edge_tts.Communicate(request.prompt, request.voice_name)
        await communicate.save(output_filename)

        # حفظ السجل في قاعدة بيانات رندر الخاصة بك
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO generated_content (user_email, content_type, prompt, output_url) VALUES (%s, %s, %s, %s);",
                (request.email, "audio", request.prompt, f"/static/{output_filename}"),
            )
            conn.commit()
            cursor.close()
            conn.close()

        # إرجاع مسار الملف الثابت الصحيح لتشغيله في المتصفح
        return {
            "status": "success",
            "file_name": f"static/{output_filename}",
            "message": "تم توليد الصوت بنجاح",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 3. API توليد الصور الاحترافية عبر SiliconFlow وحفظ الرابط ---
@app.post("/api/generate-image/")
async def generate_image(request: ContentRequest):
    url = "https://api.siliconflow.cn/v1/images/generations"

    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "black-forest-labs/FLUX.1-schnell",
        "prompt": request.prompt,
        "image_size": "768x1344",  # أبعاد فيديوهات الـ Shorts المثالية
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="فشل سيرفر SiliconFlow، تحقق من الـ Token"
            )

        result = response.json()
        image_url = result["data"][0]["url"]

        # حفظ الرابط فوراً في قاعدة بياناتك ليراها المستخدم في لوحة تحكمه
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO generated_content (user_email, content_type, prompt, output_url) VALUES (%s, %s, %s, %s);",
                (request.email, "image", request.prompt, image_url),
            )
            conn.commit()
            cursor.close()
            conn.close()

        return {"status": "success", "image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
