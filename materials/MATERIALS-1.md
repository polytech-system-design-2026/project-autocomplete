# Материалы к этапу 1. Архитектура

## Что почитать

- [Learn OpenAPI](https://learn.openapis.org/) — официальное введение в OpenAPI: структура документа, пути, операции, ответы, компоненты. Начните отсюда, прежде чем писать `openapi.yaml`.
- [Спецификация OpenAPI 3.1.0](https://spec.openapis.org/oas/v3.1.0) — справочник: когда нужно точно узнать, какие поля есть у Response Object или Parameter Object.
- [Mermaid: Sequence diagrams](https://mermaid.js.org/syntax/sequenceDiagram.html) — синтаксис диаграмм последовательности: удобно показать, кто кого вызывает при загрузке словаря и запросе подсказок. Для схемы компонентов — [flowchart](https://mermaid.js.org/syntax/flowchart.html).
- [PostgreSQL: классы и семейства операторов](https://postgrespro.ru/docs/postgresql/17/indexes-opclass) — почему обычный индекс не ускоряет `LIKE 'префикс%'` и что с этим делает `text_pattern_ops`. На русском.
- [System Design Primer](https://github.com/donnemartin/system-design-primer) — раздел Appendix с таблицей степеней двойки и задержками — пригодится для оценки нагрузки; там же разделы про кэш и базы данных.
- [GitHub: Creating a repository from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) — как создать свой репозиторий из шаблона.

## Вопросы для самопроверки

1. Сколько запросов подсказок в секунду получит сервис в пике? Почему запросов подсказок намного больше, чем поисков?
2. Какой индекс ускоряет поиск по префиксу и почему обычный индекс по `text` может не использоваться для `LIKE`?
3. Как сервис должен сортировать подсказки при равном весе и почему порядок должен быть детерминированным?
4. Что произойдёт с поиском, если пользователь введёт `%` или `_`?
5. Зачем писать `openapi.yaml` до кода, если FastAPI сгенерирует спецификацию сам?
