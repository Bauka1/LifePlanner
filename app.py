import streamlit as st
import re
import json
from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from deep_translator import GoogleTranslator
from openai import OpenAI

OPENAI_API_KEY = "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"
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

COLORS = {"высокий": "#ff4d4d", "средний": "#ffa64d", "низкий": "#ffd966"}
EMOJIS = {"высокий": "🟥", "средний": "🟧", "низкий": "🟨"}

# Ключевые слова для локального (fallback) анализа
HIGH_KEYWORDS = {"проект", "экзамен", "отчёт", "работа", "дедлайн", "важно", "срочно", "защит"}
MEDIUM_KEYWORDS = {"кушать", "поесть", "магазин", "купить", "сон", "отдохнуть", "здоровье", "продукт"}
LOW_KEYWORDS = {"погулять", "развлечения", "хобби", "кино", "позвонить", "встреча", "чтение", "спорт"}

# Правила автодекомпозиции (шаблоны)
DECOMPOSE_RULES = {
    "проект": [
        "Определить цели и требования",
        "Сделать исследование / собрать материалы",
        "Составить структуру / план",
        "Написать черновую версию",
        "Проверить и внести правки",
        "Подготовить финальную версию / презентацию"
    ],
    "отчёт": [
        "Собрать данные",
        "Проанализировать данные",
        "Составить черновой отчёт",
        "Редактировать и доработать",
        "Подготовить финал"
    ],
    "презентация": [
        "Собрать материал",
        "Сделать макет слайдов",
        "Заполнить слайды",
        "Отрепетировать"
    ],
    "default_business": [
        "Планирование шага",
        "Выполнение шага",
        "Проверка/корректировка",
        "Завершение"
    ]
}

# ===================== Вспомогательные функции =====================

def clean_text(text: str) -> str:
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text).strip()

def split_tasks(text: str) -> list:
    parts = re.split(r'[;\n•\-—]+|,|\.', text)
    tasks = [p.strip() for p in parts if p.strip()]
    return tasks

def safe_gpt_call(prompt: str, client_obj) -> str or None:
    if client_obj is None:
        return None
    try:
        # используем chat.completions API интерфейс (OpenAI python client)
        resp = client_obj.chat.completions.create(
            model="gpt-4o-mini",  # если нет доступа — замените на gpt-3.5-turbo
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800
        )
        return resp.choices[0].message.content
    except Exception as e:
        st.warning("⚠️ GPT недоступен или возникла ошибка при вызове API. Переключаюсь на локальный анализ.")
        return None

def local_analyze_tasks(text: str) -> list:
    """Локальная (fallback) обработка: возвращаем список словарей {'task','priority'}"""
    tasks = split_tasks(text)
    analyzed = []
    for t in tasks:
        tl = t.lower()
        # высокий
        if any(k in tl for k in HIGH_KEYWORDS):
            analyzed.append({"task": t, "priority": "высокий"})
            continue
        # средний
        if any(k in tl for k in MEDIUM_KEYWORDS):
            analyzed.append({"task": t, "priority": "средний"})
            continue
        # низкий
        if any(k in tl for k in LOW_KEYWORDS):
            analyzed.append({"task": t, "priority": "низкий"})
            continue
        # default: низкий
        analyzed.append({"task": t, "priority": "низкий"})
    return analyzed

def analyze_with_gpt_or_local(user_text: str):
    prompt = f"""
    Пользователь ввёл текст с задачами/целями: \"{user_text}\".
    Задача: 1) Раздели текст на отдельные задачи. 2) Определи основную цель (short). 
    3) Для каждой задачи определи категорию (деловое/личное/бытовое/здоровье) и приоритет (высокий/средний/низкий), 
       учитывая основную цель. 4) Если задач мало для длинного периода (неделя/месяц/год), предложи подзадачи или разбивку.
    Верни JSON в формате:
    {{
      "leading_goal": "...",
      "tasks": [
        {{"task":"...", "category":"...", "priority":"...", "note":"..."}},
        ...
      ]
    }}
    """
    gpt_out = safe_gpt_call(prompt, client)
    if gpt_out:
        try:
            first = gpt_out.find('{')
            last = gpt_out.rfind('}')
            json_text = gpt_out[first:last+1]
            data = json.loads(json_text)
            tasks = data.get("tasks", [])
            normalized = []
            for t in tasks:
                task_text = t.get("task") if isinstance(t, dict) else str(t)
                pr = t.get("priority", "").lower() if isinstance(t, dict) else ""
                if pr not in ("высокий","средний","низкий"):
                    pr = local_analyze_tasks(task_text)[0]["priority"]
                cat = t.get("category", "другое") if isinstance(t, dict) else "другое"
                note = t.get("note", "") if isinstance(t, dict) else ""
                normalized.append({"task": task_text, "priority": pr, "category": cat, "note": note})
            leading = data.get("leading_goal") or ""
            return {"leading_goal": leading, "tasks": normalized}
        except Exception:
            return {"leading_goal": "", "tasks": local_analyze_tasks(user_text)}
    else:
        return {"leading_goal": "", "tasks": local_analyze_tasks(user_text)}

def expand_task_by_rules(task: str, period: str) -> list:
    t_lower = task.lower()
    # найти правило по ключевому слову
    for key in DECOMPOSE_RULES:
        if key in t_lower and key != "default_business":
            template = DECOMPOSE_RULES[key]
            break
    else:
        if any(k in t_lower for k in HIGH_KEYWORDS):
            template = DECOMPOSE_RULES["default_business"]
        else:
            template = None

    if template:
        if period == "день":
            return [template[-1]]
        if period == "неделя":
            return template[-3:] if len(template) >=3 else template
        if period == "месяц":
            return template
        if period == "год":
            # сгруппировать по кварталам
            size = max(1, int(len(template)//4))
            groups = []
            for i in range(0, len(template), size):
                groups.append(" / ".join(template[i:i+size]))
            return groups
    # fallback generic microtasks
    if period == "день":
        return [f"Начать: {task}", f"Завершить: {task}"][:1]
    if period == "неделя":
        return [f"Планирование: {task}", f"Выполнение: {task}"]
    if period == "месяц":
        return [f"Разбить {task} на подзадачи", f"Выполнить первую часть {task}", f"Доделать {task}"]
    if period == "год":
        return [f"Запланировать этапы (квартал 1) для {task}", f"Реализовать этапы {task} (квартал 2-4)"]
    return [task]

def auto_expand_all(tasks_list: list, period: str):
    """Расширяет каждую задачу в набор подзадач."""
    new_tasks = []
    mapping = {}
    for t in tasks_list:
        sub = expand_task_by_rules(t, period)
        if sub:
            mapping[t] = sub
            new_tasks.extend(sub)
        else:
            mapping[t] = [t]
            new_tasks.append(t)
    return new_tasks, mapping

def distribute_for_period(tasks_meta: list, period: str):
    """Распределяет задачи по выбранному периоду."""
    if not tasks_meta:
        return {}
    n = len(tasks_meta)
    if period == "день":
        # последовательные часовые слоты
        schedule = []
        start = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)
        slot = timedelta(hours=1)
        for t in tasks_meta:
            schedule.append({"start": start, "end": start+slot, "task": t})
            start += slot
        return schedule
    if period == "неделя":
        days = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
        week = {d: [] for d in days}
        for i, t in enumerate(tasks_meta):
            day = days[i % 7]
            week[day].append(t)
        return week
    if period == "месяц":
        weeks = {f"Неделя {i}": [] for i in range(1,6)}
        for i, t in enumerate(tasks_meta):
            wk = f"Неделя {(i % 5) + 1}"
            weeks[wk].append(t)
        return weeks
    if period == "год":
        quarters = {f"Q{q}": [] for q in range(1,5)}
        for i, t in enumerate(tasks_meta):
            q = (i % 4) + 1
            quarters[f"Q{q}"].append(t)
        return quarters
    return tasks_meta

# ===================== Визуализации =====================

def plot_day_visual(tasks_meta):
    n = len(tasks_meta) or 1
    fig, axs = plt.subplots(1,2, figsize=(12, max(3, n*0.6)))


    for i, t in enumerate(tasks_meta):
        axs[0].barh(i, 1, color=COLORS[t['priority']])
        axs[0].text(0.5, i, f"{t['task']} ({t['priority']})", va='center', ha='center', color='black', fontsize=10)
    axs[0].set_yticks([])
    axs[0].set_xticks([])
    axs[0].set_xlim(0,1)
    axs[0].set_title("🕒 Тайм-блокинг на день")


    counts = {"высокий":0,"средний":0,"низкий":0}
    for t in tasks_meta:
        counts[t['priority']] += 1
    labels = []
    sizes = []
    colors = []
    for k in ["высокий","средний","низкий"]:
        labels.append(f"{k} ({counts[k]})")
        sizes.append(counts[k])
        colors.append(COLORS[k])
    if sum(sizes) == 0:
        labels = ["нет задач"]
        sizes = [1]
        colors = ["#cccccc"]
    axs[1].pie(sizes, labels=labels, autopct='%1.0f%%', colors=colors)
    axs[1].set_title("⏳ Распределение задач по приоритету")
    plt.tight_layout()
    return fig

def plot_week_table(week_dict):
    """Показываем таблицу с задачами по дням (week_dict: day -> list of tasks)"""
    # представим в DataFrame постолбцово; используем эмодзи для цветов
    df = pd.DataFrame(dict([(d, pd.Series([f"{EMOJIS[t['priority']]} {t['task']}" for t in week_dict[d]])) for d in week_dict]))
    st.table(df)

def plot_month_table(weeks_dict):
    df = pd.DataFrame(dict([(w, pd.Series([f"{EMOJIS[t['priority']]} {t['task']}" for t in weeks_dict[w]])) for w in weeks_dict]))
    st.table(df)

def plot_year_table(quarters_dict):
    df = pd.DataFrame(dict([(q, pd.Series([f"{EMOJIS[t['priority']]} {t['task']}" for t in quarters_dict[q]])) for q in quarters_dict]))
    st.table(df)
    labels = []
    values = []
    for q in sorted(quarters_dict.keys()):
        prio_score = 0
        for t in quarters_dict[q]:
            if t['priority']=="высокий":
                prio_score = max(prio_score,3)
            elif t['priority']=="средний":
                prio_score = max(prio_score,2)
            else:
                prio_score = max(prio_score,1)
        labels.append(q)
        values.append(prio_score)
    fig, ax = plt.subplots(figsize=(6,3))
    colors = [COLORS["высокий"] if v==3 else COLORS["средний"] if v==2 else COLORS["низкий"] for v in values]
    ax.bar(labels, values, color=colors)
    ax.set_ylabel("Уровень приоритета (1-низкий .. 3-высокий)")
    ax.set_title("Приоритеты по кварталам")
    st.pyplot(fig)

# ===================== Streamlit UI =====================

st.set_page_config(page_title="LifePlanner — финал", layout="wide")
st.title("🧠 LifePlanner — умный помощник планирования (финальная версия)")
st.write("Ввод: опишите свои дела, цели или состояние. Приложение автоматически выдаст план, приоритеты, рекомендации и визуализацию.")

with st.sidebar:
    st.header("Настройки")
    plan_type = st.selectbox("Тип планирования", ["деловое","личное/бытовое","смешанное"])
    period = st.selectbox("Период планирования", ["день","неделя","месяц","год"])
    min_tasks_day = st.number_input("Мин. задач для дня", min_value=1, max_value=10, value=1)
    min_tasks_week = st.number_input("Мин. задач для недели", min_value=1, max_value=20, value=3)
    min_tasks_month = st.number_input("Мин. задач для месяца", min_value=1, max_value=50, value=4)
    min_tasks_year = st.number_input("Мин. задач для года", min_value=1, max_value=200, value=6)
    st.markdown("---")
    st.info("Если GPT (OpenAI) недоступен, приложение переработает текст локально и продолжит работу (fallback).")

st.subheader("Ввод задач и состояния")
user_text = st.text_area("Опишите задачи/цели/состояние (одной строкой через запятую или многострочно):", height=160)

if st.button("Анализ и планирование"):
    if not user_text.strip():
        st.warning("Введите текст с задачами и/или состоянием.")
        st.stop()

    cleaned = clean_text(user_text)
    # Перевод (необязательно). GPT понимает русский; перевод сделан если вы хотите отправлять на английский.
    # translated = GoogleTranslator(source='auto', target='en').translate(cleaned)

    # Попытка анализа через GPT с fallback
    analysis = analyze_with_gpt_or_local(cleaned)
    leading_goal = analysis.get("leading_goal", "") or ""
    tasks_raw = analysis.get("tasks", [])

    st.info(f"🎯 Определённая цель: **{leading_goal or 'не определена'}**")

    # если GPT вернул мало задач и период большой — предложим автодекомпозицию
    tasks_texts = [t['task'] for t in tasks_raw]
    threshold_map = {"день": min_tasks_day, "неделя": min_tasks_week, "месяц": min_tasks_month, "год": min_tasks_year}
    threshold = threshold_map.get(period, 1)

    if len(tasks_texts) < threshold:
        st.warning(f"Для периода «{period}» указано мало задач ({len(tasks_texts)} < {threshold}).")
        choice = st.radio("Что сделать?", ("Оставить как есть", "Авто-расширить задачи (рекомендуется)", "Добавить типовые области жизни"))
        if choice == "Оставить как есть":
            final_tasks_list = tasks_raw
        elif choice == "Авто-расширить задачи (рекомендуется)":
            expanded, mapping = auto_expand_all(tasks_texts, period)
            st.success(f"Авто-расширение добавило {len(expanded)-len(tasks_texts)} задач.")
            # Преобразуем в структуру tasks_meta с priority (локально определим приоритеты для расширенных)
            final_tasks_list = []
            for t in expanded:
                # если GPT дал priority для original tasks — попробуем сохранить, иначе локально
                pr = None
                # попытаемся найти priority из original mapping
                # простой поиск: если подзадача содержит слово из исходной задачи — скопируем приоритет
                for orig in tasks_raw:
                    if orig['task'].lower() in t.lower():
                        pr = orig.get('priority')
                        break
                if not pr:
                    # локальное определение
                    pr = local_analyze_tasks(t)[0]['priority']
                final_tasks_list.append({"task": t, "priority": pr})
            # показ mapping
            st.subheader("Добавленные подзадачи:")
            for i, t in enumerate(final_tasks_list, start=1):
                st.write(f"{i}. {EMOJIS[t['priority']]} {t['task']}")
        else:
            # Добавление областей жизни
            areas = st.multiselect("Выберите области для добавления", ["Здоровье","Саморазвитие","Дом/Быт","Отношения"])
            extra = []
            if "Здоровье" in areas:
                extra += ["Занятие спортом 3 раза в неделю", "Прогулка 30 минут", "Сон 7-8 часов"]
            if "Саморазвитие" in areas:
                extra += ["Чтение 30 минут", "Онлайн-курс 1 модуль"]
            if "Дом/Быт" in areas:
                extra += ["Покупка продуктов", "Уборка 1 час"]
            if "Отношения" in areas:
                extra += ["Позвонить родственникам", "Встреча с другом"]
            final_tasks_list = tasks_raw + [{"task": e, "priority": local_analyze_tasks(e)[0]['priority']} for e in extra]
            st.success(f"Добавлено {len(extra)} задач из выбранных областей.")
    else:
        final_tasks_list = tasks_raw

    # Нормализация: если элементы — строки (в случаях локального анализа) конвертируем
    normalized = []
    for t in final_tasks_list:
        if isinstance(t, dict):
            task_text = t.get("task", str(t))
            pr = t.get("priority") or local_analyze_tasks(task_text)[0]['priority']
            cat = t.get("category", "другое")
            normalized.append({"task": task_text, "priority": pr, "category": cat})
        else:
            normalized.append({"task": str(t), "priority": local_analyze_tasks(str(t))[0]['priority'], "category": "другое"})
    tasks_meta = normalized

    # Вывод таблицы задач
    st.subheader("📋 Структурированный список задач")
    df = pd.DataFrame(tasks_meta)
    # упорядочим по приоритету (High -> Medium -> Low)
    pr_order = {"высокий": 0, "средний": 1, "низкий": 2}
    df["sort_key"] = df["priority"].map(pr_order)
    df = df.sort_values(by=["sort_key"]).drop(columns=["sort_key"])
    st.dataframe(df.reset_index(drop=True))

    # Экспорт CSV
    csv = df.to_csv(index=False)
    st.download_button("⬇ Скачать CSV", data=csv, file_name="lifeplan_tasks.csv", mime="text/csv")

    # Визуализация по периодам
    st.subheader("📊 Визуализация")
    if period == "день":
        fig = plot_day_visual(tasks_meta)
        st.pyplot(fig)
    elif period == "неделя":
        # распределение по дням (повторяем/распределяем если нужно)
        week_struct = distribute_for_period(tasks_meta, "неделя")
        st.write("📅 Таблица задач на неделю (эмодзи = приоритет)")
        plot_week_table(week_struct)
    elif period == "месяц":
        # распределение по неделям
        month_struct = distribute_for_period(tasks_meta, "месяц")
        st.write("📆 План на месяц (по неделям)")
        plot_month_table(month_struct)
    elif period == "год":
        year_struct = distribute_for_period(tasks_meta, "год")
        st.write("📈 План на год (по кварталам)")
        plot_year_table(year_struct)

    # Рекомендации
    st.subheader("💡 Рекомендации")
    # Если в тексте есть слова усталости — дать совет на отдых
    if any(x in cleaned.lower() for x in ["устал", "выгорел", "нет сил", "уже не могу"]):
        st.info("Похоже, вы устали — рекомендую сделать перерыв/перекус перед выполнением сложных задач.")
    else:
        st.info("Начните с задач высокого приоритета. Используйте техники Pomodoro (25/5) для концентрации.")

    st.markdown("---")
    st.caption("Примечание: если OpenAI GPT доступен (API ключ указан в настройках), то анализ выполняется через GPT; при недоступности — используется локальная логика (fallback).")
