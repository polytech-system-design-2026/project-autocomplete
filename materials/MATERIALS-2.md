# Материалы к этапу 2. MVP

## Что почитать

- [FastAPI: Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/) — `HTTPException`, коды ответов и формат `{"detail": ...}`, ошибки валидации 422.
- [FastAPI: Query Parameters and String Validations](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/) — обязательные параметры, ограничения длины и диапазона для `q` и `limit`.
- [PostgreSQL: INSERT … ON CONFLICT](https://postgrespro.ru/docs/postgresql/17/sql-insert) — upsert одной командой для загрузки словаря. На русском.
- [SQLAlchemy 2.0: ORM Quick Start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html) — модели через `Mapped` и `mapped_column`, сессия, `select`.
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) — `alembic init`, первая миграция, `upgrade head`.
- [Docker Compose: Control startup order](https://docs.docker.com/compose/how-tos/startup-order/) — `healthcheck` и `depends_on` с `condition: service_healthy`, чтобы сервис не стартовал раньше базы.

## Вопросы для самопроверки

1. Почему фразы нормализуются при записи, а не только при поиске? Что сломается, если хранить их как пришли?
2. Как загрузить 5 000 фраз быстро? Чем пачка `INSERT … ON CONFLICT` лучше цикла из отдельных запросов?
3. Почему `/health` должен ходить в базу, а не просто возвращать 200?
4. Чем миграция alembic лучше `Base.metadata.create_all()`? Что будет с данными при изменении схемы в каждом из вариантов?
5. Почему пустая выдача — 200 с пустым списком, а не 404?
