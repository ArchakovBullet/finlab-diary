# FinLab Diary

**Дневник проекта FinLabPy.**

## Назначение

Репозиторий `finlab-diary` — **зеркало** основного репозитория `supercandles-data`.
Используется для:
- Дублирования WORK_LOG (страховка от потери).
- Хранения истории коммитов (push в 2 remote).
- Независимого доступа к контексту проекта.

## Связь с основным репозиторием

- **Основной:** `supercandles-data` (origin).
- **Зеркало:** `finlab-diary` (diary).
- **Push:** после каждого WORK_LOG — в **оба** remote.

## Структура

- `WORK_LOG.md` — дневник разработки (копия из supercandles-data).
- `README.md` — этот файл.

## Ссылки

- Сервер: 159.194.219.117, `/root/finlab`.
- Дашборд: http://159.194.219.117:8501 (Streamlit).
- WORK_LOG (raw): https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/master/WORK_LOG.md

## Правила

1. **WORK_LOG** — в `.gitignore` → `git add -f`.
2. **Запись** — через `cat >>` (В КОНЕЦ).
3. **После WORK_LOG** — commit + push в **2 remote** (origin + diary).
4. **Не патчить Python** через sed — только `text.replace`.

## Актуально на

06.10.2026, commit `1b47bdf`.

## Идеология

Джим Саймонс (Renaissance Technologies):
- Данные — прежде всего.
- Статистика, а не интуиция.
- Walk-forward обязателен.
- Много маленьких ставок.
- Контроль риска.
- Наука, а не религия.
