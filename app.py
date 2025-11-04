import streamlit as st
from openai import OpenAI

OPENAI_API_KEY = "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"
client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="🧠 LifePlanner AI", layout="centered")
st.title("🧠 LifePlanner — ваш интеллектуальный планировщик")
st.write("Введите список задач на день, а AI поможет расставить приоритеты ✨")

tasks_input = st.text_area("📝 Ваши задачи (по одной в строке):", height=150)

if st.button("🤖 Составить план"):
    if not tasks_input.strip():
        st.warning("⚠️ Введите хотя бы одну задачу.")
    else:
        # Отправляем запрос в GPT
        prompt = f"""
        Пользователь дал список задач:
        {tasks_input}

        Отсортируй задачи по приоритету (от самых важных к менее важным)
        и добавь короткий совет, как лучше распределить время.
        Ответь в формате:
        1️⃣ Задача — приоритет
        💡 Совет:
        """

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            st.subheader("📋 Умный план на день:")
            st.write(response.choices[0].message.content.strip())
        except Exception as e:
            st.error(f"Ошибка при обращении к OpenAI: {e}")
