# Ветки, коммиты и релизы

## Модель веток

Упрощённый Git Flow: стабильный `main`, интеграционный `develop` и короткоживущие
тематические ветки.

```text
main     ●──────────────●──────────────●  (теги v1.0.0, v1.1.0)
          \            / \            /
develop    ●──●──●──●──   ●──●──●──●──
              \    /          \    /
feature/*      ●──●            ●──●
```

| Ветка | Назначение | Кто вливает |
| --- | --- | --- |
| `main` | Только релизы; каждый коммит помечен тегом | merge из `develop` |
| `develop` | Интеграция готовых изменений | PR из тематических веток |
| `feature/<тема>` | Новая функциональность | PR в `develop` |
| `fix/<тема>` | Исправление ошибки | PR в `develop` |
| `docs/<тема>` | Документация | PR в `develop` |
| `chore/<тема>` | Инфраструктура, зависимости, CI | PR в `develop` |

Правила:

- ветки создаются от `develop`, кроме `hotfix/*` — он создаётся от `main`;
- одна ветка — одна задача; имя в kebab-case: `feature/redis-history`;
- в `main` не коммитят напрямую;
- слияние в `develop` — через pull request с зелёным CI;
- релизный merge `develop → main` выполняется с `--no-ff`, чтобы сохранить точку релиза.

## Именование коммитов

Используются [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <краткое описание>
```

| Тип | Когда |
| --- | --- |
| `feat` | Новая функциональность |
| `fix` | Исправление ошибки |
| `docs` | Документация |
| `test` | Тесты |
| `refactor` | Рефакторинг без изменения поведения |
| `chore` | CI, зависимости, конфигурация |
| `perf` | Производительность |

Примеры:

```text
feat(knowledge): учитывать синонимы предметной области
fix(vk): не отвечать на исходящие сообщения сообщества
docs(readme): добавить схему архитектуры
test(handlers): покрыть fallback при ошибке ProxyAPI
```

## Рабочий цикл

```bash
git switch develop
git pull --ff-only
git switch -c feature/redis-history

# ... изменения ...
pytest
ruff check src tests

git add .
git commit -m "feat(history): добавить хранилище на Redis"
git push -u origin feature/redis-history
```

Далее — pull request в `develop`. CI должен быть зелёным, после ревью — squash или merge
(в проекте используется merge с `--no-ff`, чтобы сохранять историю ветки).

## Релиз

```bash
git switch develop
git pull --ff-only
git switch main
git pull --ff-only
git merge --no-ff develop -m "chore(release): v1.1.0"
git tag -a v1.1.0 -m "v1.1.0"
git push origin main --tags
git switch develop
git merge --no-ff main -m "chore: синхронизировать develop с релизом"
git push origin develop
```

Перед релизом:

1. Обновить `CHANGELOG.md`.
2. Поднять версию в `pyproject.toml` и `src/alina_bot/__init__.py`.
3. Убедиться, что CI на `develop` зелёный.
4. Проверить, что `.env` и секреты не попали в коммит (`git status`, `git diff --cached`).

## Hotfix

```bash
git switch main
git switch -c hotfix/vk-timeout
# исправление + тест
git commit -m "fix(vk): увеличить таймаут Long Poll"
git switch main
git merge --no-ff hotfix/vk-timeout
git tag -a v1.1.1 -m "v1.1.1"
git push origin main --tags
git switch develop
git merge --no-ff main
git push origin develop
```

## Защита веток (рекомендация для GitHub)

Для `main`:

- запретить прямой push;
- требовать pull request и хотя бы один review;
- требовать успешный CI (`Ruff`, `Pytest`);
- запретить force push и удаление ветки.

Для `develop` — те же правила, кроме обязательного review.
