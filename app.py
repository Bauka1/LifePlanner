import streamlit as st
import re
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

# 🔹 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ

def extract_tasks(text):
    """Извлекаем задачи из текста по запятым и разделителям."""
    tasks = re.split(r'[.,;]\s*', text)
    tasks = [t.strip().capitalize() for t in tasks if t.strip()]
    return tasks


def find_main_goal(tasks):
    """Определяем основную цель (задача с профессиональным или учебным контекстом)."""
    goal_keywords = ["проект", "отчёт", "работа", "учёба", "презентация", "экзамен", "дедлайн"]
    for task in tasks:
        if any(word in task.lower() for word in goal_keywords):
            return task
    return None


def define_priority(task, goal):
    """Определяем приоритет на основе связи с целью."""
    if goal and task == goal:
        return "Высокий", "Напрямую связано с основной целью"
    elif any(word in task.lower() for word in ["кушать", "поесть", "еда", "магазин", "сон", "отдохнуть"]):
        return "Средний", "Косвенно влияет на энергию и продуктивность"
    elif any(word in task.lower() for word in ["позвонить", "друзья", "погулять", "отдых"]):
        return "Низкий", "Личная задача, не влияет на основную цель"
    else:
        return "Средний", "Второстепенная, но полезная задача"


def recommend_time(priority):
    """Рекомендуем время выполнения по приоритету."""
    if priority == "Высокий":
        return "09:00–11:00"
    elif priority == "Средний":
        return "12:00–15:00"
    else:
        return "16:00–19:00"


def generate_schedule(tasks_with_meta):
    """Создаём расписание на день."""
    start_time = datetime.strptime("09:00", "%H:%M")
    schedule = []
    for t in tasks_with_meta:
        end_time = start_time + timedelta(minutes=60)
        schedule.append({
            "Время": f"{start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}",
            "Задача": t["Задача"],
            "Приоритет": t["Приоритет"]
        })
        start_time = end_time
    return pd.DataFrame(schedule)


def get_recommendation(text):
    """Совет по концентрации или отдыху."""
    if "устал" in text.lower():
        return "😴 Похоже, вы устали — сделайте короткий перерыв перед выполнением задач."
    elif "хочу" in text.lower():
        return "💡 Начните с выполнения самой важной задачи — это придаст мотивацию."
    else:
        return "✅ Сфокусируйтесь на приоритетных задачах, делайте короткие паузы каждые 2 часа."


# 🔹 Streamlit UI

st.set_page_config(page_title="Smart Planner AI", page_icon="🧠", layout="centered")

st.title("🧠 Интеллектуальный планировщик задач")
st.write("Введите список дел, целей или описание своего состояния:")

user_input = st.text_area("📝 Пример: подготовить проект, хочу кушать, сходить в магазин, позвонить маме", height=120)

if st.button("🔍 Проанализировать"):
    if not user_input.strip():
        st.warning("Введите текст для анализа.")
    else:
        # === 1. Извлекаем и анализируем задачи ===
        tasks = extract_tasks(user_input)
        main_goal = find_main_goal(tasks)
        tasks_meta = []

        for t in tasks:
            priority, reason = define_priority(t, main_goal)
            time_slot = recommend_time(priority)
            tasks_meta.append({
                "Задача": t,
                "Приоритет": priority,
                "Обоснование": reason,
                "Рекомендованное время": time_slot
            })

        df = pd.DataFrame(tasks_meta)

        # === 2. Таблица с приоритетами ===
        st.subheader("📋 Структурированный список задач")
        st.dataframe(df, use_container_width=True)

        # === 3. Основная цель ===
        st.subheader("🎯 Основная цель:")
        st.success(main_goal if main_goal else "Цель не определена (возможно, задачи бытового характера).")

        # === 4. Расписание (цветная таблица) ===
        st.subheader("🕒 Визуализация расписания")

        schedule_df = generate_schedule(tasks_meta)
        colors = {"Высокий": "#ff4b4b", "Средний": "#ffb84d", "Низкий": "#d5fc23"}
        schedule_df["Цвет"] = schedule_df["Приоритет"].map(colors)

        st.markdown("#### Таймлайн:")
        for _, row in schedule_df.iterrows():
            st.markdown(
                f"<div style='background-color:{row['Цвет']}; padding:8px; border-radius:8px; margin-bottom:4px;'>"
                f"<b>{row['Время']}</b> — {row['Задача']} ({row['Приоритет']})"
                f"</div>", unsafe_allow_html=True
            )

        # === 5. Диаграмма распределения времени ===
        st.subheader("📊 Распределение времени по приоритетам")

        priority_counts = df["Приоритет"].value_counts()
        fig, ax = plt.subplots()
        ax.pie(priority_counts, labels=priority_counts.index, autopct="%1.1f%%", startangle=90,
               colors=["#ff4b4b", "#ffb84d", "#d5fc23"])
        ax.axis("equal")
        st.pyplot(fig)

        # === 6. Совет от AI ===
        st.subheader("💡 Совет дня:")
        st.info(get_recommendation(user_input))
