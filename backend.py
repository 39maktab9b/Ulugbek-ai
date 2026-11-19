import os
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic

app = FastAPI()

# Render -> Environment Variables bo'limiga ANTHROPIC_API_KEY nomi bilan kalitni qo'ying
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


def init_db():
    conn = sqlite3.connect("ulugbek_ai_backend.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            name TEXT,
            role TEXT,
            age TEXT,
            interests TEXT,
            goals TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, name, role, age, interests, goals)
        VALUES ('student1', '1234', 'Mirzo', 'oquvchi', '16', 'Astronomiya, Fizika, Python', 'SAT va Olimpiada')
    """)
    conn.commit()
    conn.close()


init_db()


class ChatRequest(BaseModel):
    username: str
    prompt: str


class ProfileModel(BaseModel):
    old_username: str
    new_username: str
    password: str
    name: str
    role: str
    age: str
    interests: str
    goals: str


@app.post("/api/profile/update")
def update_profile(data: ProfileModel):
    conn = sqlite3.connect("ulugbek_ai_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO users (username, password, name, role, age, interests, goals)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.new_username,
            data.password,
            data.name,
            data.role,
            data.age,
            data.interests,
            data.goals,
        ))

        if data.old_username != data.new_username:
            cursor.execute("DELETE FROM users WHERE username = ?", (data.old_username,))

        conn.commit()
        conn.close()
        return {"status": "success", "message": "Profil muvaffaqiyatli saqlandi!"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/chat")
def chat_with_ai(data: ChatRequest):
    if not client or not ANTHROPIC_API_KEY:
        return {
            "response": "AI bilan bog'lanishda xatolik yuz berdi: ANTHROPIC_API_KEY sozlanmagan."
        }

    conn = sqlite3.connect("ulugbek_ai_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, role, age, interests, goals FROM users WHERE username = ?",
        (data.username,),
    )
    user = cursor.fetchone()
    conn.close()

    if user:
        name, role, age, interests, goals = user
    else:
        name, role, age, interests, goals = "O'quvchi", "O'quvchi", "16", "Ilm-fan", "Talim"

    system_instruction = f"""
    Siz Mirzo Ulug'bek nomidagi AI va Muhandislik maktabining bosh intellektual yordamchisisiz.
    Foydalanuvchi ma'lumotlari:
- Ismi: {name}
- Roli: {role}
- Yoshi: {age}
- Qiziqishlari: {interests}
- Maqsadi: {goals}

    Qoidalaringiz:
1. Har doim foydalanuvchining yoshi, roli va qiziqishlariga moslab chuqur, ilmiy va tushunarli javob bering.
2. O'zbek tilida samimiy va Mirzo Ulug'bek merosiga mos tarzda javob qaytaring.
    """

    try:
        message = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=1024,
            temperature=0.6,
            system=system_instruction,
            messages=[
                {"role": "user", "content": data.prompt}
            ],
        )
        text_parts = [
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ]
        reply_text = "\n".join(text_parts).strip()
        return {"response": reply_text}
    except Exception as e:
        return {"response": f"AI bilan bog'lanishda xatolik yuz berdi: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
