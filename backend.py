import os
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI()

# Google GenAI Klienti (v1beta versiyasi bilan AQ. kalitini to'liq qo'llab-quvvatlaydi)
client = genai.Client(
    api_key="AQ.Ab8RN6L3uDpYee7j933yMI1tSsUtDzsE0E-YpjS90_N2asiwug",
    http_options={'api_version': 'v1beta'}
)

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
        """, (data.new_username, data.password, data.name, data.role, data.age, data.interests, data.goals))
        
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
    conn = sqlite3.connect("ulugbek_ai_backend.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, role, age, interests, goals FROM users WHERE username = ?", (data.username,))
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
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=data.prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.6
            ),
        )
        return {"response": response.text}
    except Exception as e:
        return {"response": f"AI bilan bog'lanishda xatolik yuz berdi: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
