# Материалы к этапу 3. Масштабирование

## Что почитать

- [Redis Strings](https://redis.io/docs/latest/develop/data-types/strings/) — `GET`, `SET`, `INCR`, время жизни ключа: всё, что нужно для кэша ответов и номера версии словаря.
- [Redis Sorted sets](https://redis.io/docs/latest/develop/data-types/sorted-sets/) — упорядоченные множества: если решите хранить индекс подсказок в Redis, а не кэш ответов.
- [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/) — поток событий, consumer group, `XREADGROUP` и `XACK`: как читать очередь и не терять события при падении воркера.
- [Шаблон «Кэш на стороне приложения» (cache-aside)](https://learn.microsoft.com/ru-ru/azure/architecture/patterns/cache-aside) — когда читать из кэша, когда из БД и как кэш наполняется. На русском.
- [Locust: Quick start](https://docs.locust.io/en/stable/quickstart.html) — как описать пользователя и задачи в `locustfile.py`.
- [Locust: Running without the web UI](https://docs.locust.io/en/stable/running-without-web-ui.html) — запуск `--headless` с параметрами `--users`, `--spawn-rate`, `--run-time`.

## Вопросы для самопроверки

1. Как ваш кэш узнаёт, что словарь изменился? Что увидит пользователь в промежутке между изменением и инвалидацией?
2. Почему для учёта выборов нужна очередь, а не `UPDATE` прямо в обработчике `POST /queries`?
3. Что будет с выборами, если воркер упадёт после чтения из очереди, но до записи в БД? Как это решает ваша реализация?
4. Сколько памяти займёт ваш кэш, если пользователи запросят 100 000 разных префиксов? Нужен ли TTL?
5. Как вы объясните разницу в p95 до и после Redis? Где сервис тратил время раньше?
