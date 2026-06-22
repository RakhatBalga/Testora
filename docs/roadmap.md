# ТЗ: Полная версия Testora

Документ — единый план доработки Testora от текущего состояния (auth + Reading/Listening
со стандартным редизайном) до полноценного продукта: реальные тесты, IELTS band score,
Writing и Speaking с AI-проверкой.

**Ключевой принцип (бюджет):** AI-код для Writing/Speaking пишем полностью, но НЕ подключаем.
Работает через абстракцию `AI_PROVIDER=mock|claude`. Сейчас — бесплатные заглушки (`mock`).
Появятся деньги → ставим `ANTHROPIC_API_KEY`, меняем env на `claude`, код не трогаем.

**Дизайн-ориентир (ielts.gg):** чистый белый фон, одна центральная колонка, много воздуха,
крупные цветные графики прогресса по band score, заметные синие CTA, дружелюбный тон,
band score (0–9) на первом месте, а не сырые баллы.

---

## 0. Срочно — безопасность (до всего остального)

- [ ] `git rm --cached backend/.env`, закоммитить (файл уже в `.gitignore`, но был запушен).
- [ ] Сменить пароль PostgreSQL и `SECRET_KEY` (старые утекли на GitHub).
- [ ] Создать `backend/.env.example` с пустыми ключами как шаблон.

---

## 1. Дизайн (статус: в основном готово)

Сделано в редизайне: дизайн-система (`components/ui/`: Button, Card, Badge, Input, Skeleton),
лендинг, дашборд со статистикой, обновлённые страницы теста/результата/профиля.

Осталось доработать под ielts.gg-стиль:
- **График прогресса band score** на дашборде (линия по последним попыткам, градиент).
- Карточка «следующий шаг» (рекомендованный тест).
- Мелкая полировка: пустые состояния, мобильная вёрстка.

---

## 2. Реальные тесты + IELTS Band Score

Сейчас модель умеет только `single_choice`. Расширяем под настоящий IELTS.

### 2.1 Модель данных
- `Section` (новая сущность): `id`, `test_id`, `order`, `title`, `passage` (текст для Reading),
  `audio_url` (для Listening). Вопросы привязаны к секции.
- `Question`: добавить `question_type` (enum):
  `single_choice | multiple_choice | true_false_notgiven | matching | fill_blank | short_answer`.
- `correct_answer` → хранить как JSON (список допустимых вариантов для `short_answer`/`fill_blank`).
- IELTS Reading = 3 секции, 40 вопросов; Listening = 4 секции, 40 вопросов.

### 2.2 Band score
- Таблица raw (0–40) → band (0–9) как конфиг/функция (`services/band.py`).
- На результате показывать **band крупно**, raw — мелко рядом.
- В `Attempt` хранить `band` (Float).

### 2.3 Контент
- JSON-схема теста: `backend/data/reading/*.json`, `backend/data/listening/*.json`
  (секции → вопросы → тип → варианты → ответ).
- `seed.py` читает файлы и заливает.
- Аудио Listening: `backend/static/audio/`, отдавать через `StaticFiles`.

### 2.4 Frontend
- Страница теста рендерит разные типы вопросов (компонент на каждый `question_type`).
- Результат: band-score крупно + разбор по секциям.

---

## 3. AI-слой (фундамент для Writing/Speaking)

Делается ДО модулей Writing/Speaking, т.к. они на него опираются.

### `backend/app/services/ai/`
- `base.py` — абстрактные `WritingGrader`, `SpeakingGrader` с методом `grade(...) -> Feedback`.
  `Feedback` = `{ band: float, criteria: dict, summary: str, suggestions: list }`.
- `mock.py` — бесплатные заглушки:
  - Writing: считает слова, проверяет минимум, отдаёт шаблонный фидбек и грубый band по длине/структуре.
  - Speaking: возвращает «требуется ручная проверка» / mock-band.
- `claude.py` — **полная реализация на Anthropic API** (4 критерия IELTS: Task Achievement,
  Coherence, Lexical Resource, Grammar). Вызывается только при наличии ключа.
- `factory.py` — выбирает реализацию по `AI_PROVIDER`.

### Env
```
AI_PROVIDER=mock        # mock | claude
ANTHROPIC_API_KEY=      # пусто пока нет денег
```

---

## 4. Writing-модуль (AI-ready, заглушка)

### 4.1 Модель
- `WritingTask`: `id`, `task_type` (1/2), `prompt`, `image_url` (графики Task 1), `min_words`, `duration_minutes`.
- `WritingSubmission`: `id`, `user_id`, `task_id`, `text`, `word_count`,
  `status` (`pending`/`graded`), `band` (nullable), `feedback` (nullable JSON), `created_at`.

### 4.2 Эндпоинты
- `GET /writing/tasks`, `GET /writing/tasks/{id}`
- `POST /writing/submit` — сохраняет текст, считает слова, статус `pending`, дёргает AI-слой
  (mock сразу отдаёт band/фидбек → статус `graded`).
- `GET /writing/submissions`, `GET /writing/submissions/{id}`

### 4.3 Frontend
- Страница задания: prompt + (картинка для Task 1) + textarea + счётчик слов + таймер.
- Результат: band по 4 критериям + текстовый фидбек (или «На проверке» если `pending`).

---

## 5. Speaking-модуль (AI-ready, заглушка)

### 5.1 Модель
- `SpeakingTask`: `id`, `part` (1/2/3), `questions` (JSON), `prep_seconds`, `speak_seconds`.
- `SpeakingSubmission`: `id`, `user_id`, `task_id`, `audio_url`, `transcript` (nullable),
  `band` (nullable), `feedback` (nullable JSON), `created_at`.

### 5.2 Запись
- Браузер: **MediaRecorder API** → запись голоса → загрузка файла.
- `POST /speaking/submit` — приём аудио, сохранение в `static/audio_submissions/`.
- AI (заглушка): транскрипция (позже Whisper) + оценка за интерфейсом, пока mock.

### 5.3 Frontend
- Страница: вопрос + таймер подготовки → таймер ответа → запись → загрузка.
- Результат: band + фидбек (или «На проверке»).

---

## 6. Дашборд v2 (объединяет всё)
- Прогресс band score по 4 секциям (Reading/Listening/Writing/Speaking) + общий.
- График динамики по времени (ielts.gg-стиль).
- Рекомендация следующего теста.

---

## Технический долг
- `requirements.txt`: добавить `bcrypt`, убрать `passlib`.
- `backend/.env.example` (см. этап 0).
- StaticFiles для аудио.
- Опционально: pytest на бэкенд (auth, scoring, band, mock-grader).

---

## Порядок сборки (предлагаемый)
1. Этап 0 (безопасность) — 10 минут.
2. Этап 3 (AI-слой) — фундамент, без него Writing/Speaking не собрать.
3. Этап 2 (реальные тесты + band) — расширение того, что уже работает.
4. Этап 4 (Writing) → Этап 5 (Speaking).
5. Этап 6 (дашборд v2) + полировка дизайна.

## Что уже готово
- Auth (JWT), Reading/Listening (таймер, подсчёт, разбор, история).
- Frontend Next.js + TS + Tailwind, дизайн-система, лендинг, дашборд.
- Alembic-миграции, seed с демо-данными.
