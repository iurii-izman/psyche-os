# PSYCHE OS — точный implementation prompt для F0

## Роль и конечный результат

Ты — implementation agent в репозитории PSYCHE OS. Реализуй **только F0: Minimal Irreversible Secure Core** — локальное, однопользовательское, offline-first Python 3.12+ ядро и CLI без сетевого listener. Цель F0 — не создать продукт, а доказать на синтетических данных те семантические, криптографические, deletion/recovery и portability-инварианты, которые опасно откладывать.

Работай автономно до проверяемого результата. Не подменяй реализацию документацией и не объявляй контроль готовым только потому, что существует интерфейс или тест-заглушка. Если на текущей платформе невозможно честно доказать SQLCipher, OS key wrap, лицензию или recovery path, сохрани fail-closed состояние, выполни всё безопасно достижимое и зафиксируй точный blocker. Не переходи на обычный SQLite под именем «encrypted», не ослабляй требования и не открывай real-data gate.

Язык документации и пользовательских сообщений CLI — русский, если это не мешает стабильным machine-readable кодам. Имена модулей, типов, полей, команд, ошибок и схем — английские стабильные идентификаторы.

## 1. Сначала прочитай нормативные документы

До изменения кода полностью прочитай, в указанном порядке:

1. `AGENTS.md`;
2. `CONSTITUTION.md`;
3. `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`;
4. `docs/architecture/DATA_MODEL.md`;
5. `docs/architecture/SYSTEM_ARCHITECTURE.md`;
6. `docs/architecture/PRIVACY_SECURITY_MODEL.md`;
7. `docs/architecture/THREAT_MODEL.md`;
8. `docs/SCIENTIFIC_GOVERNANCE.md`;
9. `ontology/psyche_domains.yaml`;
10. `docs/DECISION_LOG.md` и `docs/ROADMAP.md`.

Эти файлы являются требованиями, а не справочным фоном. В implementation report связывай решения с локальными ссылками вида `CONSTITUTION.md#...`, `docs/architecture/PRIVACY_SECURITY_MODEL.md#...`, `TM-...`, `PS-...`, `C-...`. Не используй внешние web-ссылки как замену репозиторным требованиям. Метаданные точных версий и лицензий зависимостей получай из установленного пакета, lock-файла и его license files и сохраняй локально.

Если любой обязательный файл отсутствует, поврежден, еще содержит незавершенные placeholders или два нормативных документа непримиримо расходятся, не угадывай. Сначала проверь, не создается ли файл параллельно, затем сообщи точный конфликт владельцу задачи. Приоритет: `CONSTITUTION.md` → v2 master spec → профильные architecture/governance документы → ontology → decision log/roadmap. Ни один код не может молча ослабить конституционный инвариант.

## 2. Discovery и защита рабочей копии

Перед правками выполни и сохрани в рабочем журнале:

```powershell
git status --short
git branch --show-current
git log -1 --oneline
rg --files
python --version
```

Затем:

- прочитай все применимые `AGENTS.md` в дереве;
- проверь существующие `pyproject.toml`, lock-файлы, исходники, миграции, тесты и CI прежде, чем создавать новые;
- считай уже существующие незакоммиченные изменения пользовательскими или параллельными; не удаляй, не reset/checkout их и не перезаписывай без анализа;
- при пересечении правок сначала сделай минимальный diff и интегрируй изменения; остановись только если безопасное объединение действительно невозможно;
- используй `rg`/`rg --files` для поиска и `apply_patch` для ручных правок;
- не применяй destructive Git-команды, не переписывай историю, не commit/push и не создавай PR без отдельного явного разрешения;
- если исходная задача явно разрешает commits, делай только небольшие логические local commits после соответствующих тестов и никогда не push; иначе запиши предложенное разбиение commits в implementation report;
- не читай и не копируй какие-либо внешние пользовательские каталоги, vault, backup, export, почту, календарь или иные персональные данные.

Считай `CONSTITUTION.md`, v2 master spec, `docs/architecture/*`, `docs/SCIENTIFIC_GOVERNANCE.md`, `ontology/psyche_domains.yaml`, `docs/DECISION_LOG.md`, `docs/ROADMAP.md` и research/review inputs замороженными нормативными артефактами. F0 не редактирует их, кроме добавления проверяемых implementation evidence в существующий `docs/architecture/REAL_DATA_GATE.yaml` при сохранении `CLOSED`. Если код выявляет дефект требования, зафиксируй conflict/change request, а не переписывай источник власти.

## 3. Абсолютная граница F0

### 3.1 Разрешено и обязательно

Реализуй минимальный вертикальный срез:

- локальный Python 3.12+ package и CLI;
- однопользовательский vault с opaque random 128-bit IDs;
- immutable version rows и transaction-time intervals;
- rich temporal assertions: роли времени, exact/interval/fuzzy/unknown, precision, timezone-known/assumed;
- строгие различия source/verbatim, report/observation, normalized assertion и derived claim;
- typed provenance, derivation inputs/outputs, evidence links;
- uncertainty, contradiction и unknown как отдельные сущности;
- versioned `DataPolicy`, deterministic policy composition и lineage closure для `NEVER_CLOUD`;
- envelope/key interfaces, проверенный локальный OS-wrap профиль текущей ОС и независимый recovery wrap;
- fail-closed SQLCipher profile gate;
- independently authenticated encrypted blob envelopes и crash-safe blob/database commit protocol;
- content-free allowlisted operational audit;
- correction, supersession, rejection, invalidation и hard deletion как разные операции;
- versioned migrations;
- authenticated encrypted backup, isolated restore и open logical export внутри encrypted package;
- knowledge-source/snapshot, ontology registry и assessment registry **только как metadata skeleton**;
- synthetic fixtures, contract/property/integration/security/fault-injection tests;
- machine-readable validators, evidence reports и gate status.

### 3.2 Запрещено без исключений

Не реализуй и не подключай:

- реальные персональные, психологические, медицинские, сексуальные, семейные, юридические, финансовые, messaging/calendar/wearable данные;
- произвольный пользовательский capture, ввод свободного текста, stdin/file ingestion или general-purpose import;
- production desktop/web/mobile UI, webview, browser, HTTP/RPC server, localhost listener, daemon или background worker;
- любой network client, telemetry, update check, remote logging, cloud storage, sync, sharing или collaboration;
- LLM, model/provider SDK, prompt execution, embeddings, agents, MCP или внешние tools;
- assessment items, manuals, translations, copyrighted criteria, actual scoring algorithms, norms, cutoffs или clinical interpretation; допускается лишь закрытый metadata registry skeleton с synthetic dummy entry;
- diagnosis, differential diagnosis, triage, treatment/prescription, crisis detection, therapy, clinical recommendation или causal conclusion;
- graph database, evidence graph runtime, vector/full-text engine, analytics warehouse или derived projection engine;
- email/message/calendar/wearable/document parsers и прочие import integrations;
- FHIR, clinician export, EHR, public API;
- N-of-1 execution, interventions, notifications, reminders, engagement mechanics;
- multi-user tenancy, remote access, cross-device sync;
- custom cryptographic primitives, самодельный KDF/AEAD, plaintext fallback или secrets в коде/env/CLI arguments/logs/tests.

Наличие будущего интерфейса/enum не дает права создать adapter. Запрещенные зависимости не должны появиться даже транзитивно без отдельного обоснования. В `src/` не должно быть импортов `socket`, `http.client`, `urllib`, `requests`, `httpx`, `aiohttp`, provider SDK или web frameworks. Стандартные модули, которые транзитивно умеют сеть, не используются для сетевых операций; scope validator проверяет фактические imports и dependency list.

## 4. Synthetic-only enforcement

`REAL_DATA_GATE` на входе и выходе F0 равен `CLOSED`. Это runtime-инвариант, а не только надпись в документации.

Обязательная реализация:

1. Каждый F0 vault имеет неизменяемый профиль `data_mode = synthetic_only`.
2. CLI не принимает note/report/claim text, произвольный путь к source-файлу, pipe/stdin или JSON payload.
3. Единственный способ создать содержательные записи — загрузить один из встроенных package-resource fixture packs по allowlisted `fixture_pack_id`; пакеты содержат явный `synthetic_fixture = true`, schema/version и digest.
4. Application command для записи требует `SyntheticFixtureCapability`, выдаваемую только после проверки встроенного manifest. Нельзя получить ее через CLI flag, env var или произвольный файл.
5. Restore и migration отказываются активировать vault/package без подтвержденного `synthetic_only` manifest.
6. Export/backup сохраняют synthetic marker. Он не может быть миграцией изменен на real-data profile.
7. Fixtures явно вымышлены, не основаны на реальном человеке и не содержат правдоподобных ФИО, адресов, контактов, диагнозов, traumatic narratives, assessment text или secrets.
8. Добавь negative tests на обход guard через malformed manifest, unknown fixture ID, прямой repository call, restore/export package, migration и измененный digest.

Не создавай команду «временно разрешить real data». В F0 такого состояния не существует.

## 5. Модульная архитектура и dependency direction

Сохрани или создай `src/psyche_os/` с четкими границами:

```text
src/psyche_os/
  __init__.py
  __main__.py
  domain/
  temporal/
  provenance/
  policy/
  application/
  crypto/
  storage/
  backup_export/
  knowledge/
  adapters/
  interfaces/
```

Правила:

- `domain`, `temporal`, `provenance`, `policy` — pure Python; они не импортируют CLI, database driver, filesystem, OS keystore или crypto implementation.
- `application` оркестрирует use cases через typed ports и одну transaction boundary; не выполняет SQL и не вызывает CLI.
- `crypto`, `storage`, `backup_export`, `adapters` реализуют ports; они не делают психологические/научные inference.
- `interfaces` содержит CLI composition и view models; CLI не обращается к SQL/файлам vault напрямую.
- `knowledge` хранит только version/rights/status/source metadata skeleton и snapshot manifest; personal evidence туда не попадает.
- Cross-module write возможен только через application command и unit-of-work.
- Clock, UUID/randomness, secret input, key wrapper, AEAD, database, blob store и filesystem faults инъецируются через ports. Test adapters находятся только в `tests/`, не в production composition root.
- Добавь автоматический архитектурный test, который анализирует imports и запрещает обратные зависимости.

Не создавай catch-all `utils.py`, generic JSON blob вместо typed entity или «repository» с обходом policy/provenance. Новая зависимость допускается только если она уменьшает риск, pin/hash/лицензия проверены и стандартной библиотеки недостаточно.

## 6. Канонический минимум данных

Схема и domain model должны реализовать семантику из `docs/architecture/DATA_MODEL.md`, не изобретая универсальный `is_true`/`confidence`.

Обязательные aggregates/records:

- `Vault`, `Subject`, `Actor`;
- `SourceArtifact`, `BlobObject`, `SourceLocator`;
- `Report`, `Observation`, `Assertion`;
- `TemporalAssertion`;
- `Claim`/`ClaimVersion`, `EvidenceLink`, `UncertaintyProfile`, `ContradictionSet`, `Unknown`;
- `DerivationRun`, `DerivationInput`, `DerivationOutput`;
- `DataPolicy`, `PolicyLineageEdge`, `DisclosureReceipt` skeleton;
- `AuditEvent`;
- `DeletionRequest`, `DeletionPlan`, `DeletionReceipt`;
- `BackupManifest`, `ExportManifest`;
- `SchemaMigration`;
- `KnowledgeSource`, `KnowledgeSnapshot`, `OntologyRegistryEntry`, `AssessmentRegistryEntry` metadata skeletons.

Для versioned semantic record обязательно: stable `record_id`, distinct `version_id`, `schema_version`, half-open `transaction_from`, nullable `transaction_to`, `change_reason_code`, optional `supersedes_version_id`, `created_by_actor_id`, optional `derivation_id`. Закрытие предыдущей active version и вставка новой атомарны; одновременно активна не более одна версия; intervals не перекрываются; stale expected-version дает typed conflict.

Для времени сохрани `temporal_role`, `value_kind`, bounds/inclusivity, precision, original literal reference, timezone и known/assumed state, calendar, assertion actor/source, certainty class/rationale и conflict/supersession links. Никогда не превращай `summer 2008`, `примерно`, `не помню` или unknown в выдуманный timestamp. Transaction time и domain time не смешиваются.

Для claims/evidence:

- output правила, deterministic transform или будущей модели всегда derived/proposed, не evidence;
- active claim имеет evidence link либо явный `unsupported_proposal`;
- evidence relation, directness, independence group, scope/temporal match и rationale раздельны;
- uncertainty остается многомерной;
- contradiction не разрешается автоматически по новизне;
- missing, declined, unknown и not-applicable различимы;
- causal и diagnostic claim types существуют лишь для fail-closed validation: F0 запрещает их создавать/активировать.

Все derived records имеют один действующий `DerivationRun` и существующие typed inputs. Все source-near assertions имеют locator или typed source-unavailable reason. Assessment registry status по умолчанию `blocked`; item/scoring/content fields отсутствуют из F0 schema, чтобы их нельзя было случайно наполнить.

`ontology/psyche_domains.yaml` импортируется только как version-pinned knowledge registry metadata: проверь его schema contract, stable IDs, registry version и digest, затем включи exact reference в `KnowledgeSnapshot`. Domain entry не является фактом о человеке и не создает personal claim. Не копируй scientific source text или copyrighted content в database fixture.

## 7. Data policy и `NEVER_CLOUD`

Реализуй orthogonal policy axes из `PRIVACY_SECURITY_MODEL.md`: sensitivity, processing location, cloud policy, purpose/provider bounds, third-party scope, retention, export/redaction и derived-lineage rule.

Требования:

- missing, unknown, contradictory или unsupported policy fails closed;
- effective derivative policy — deterministic meet наиболее строгих родителей по каждой оси;
- `NEVER_CLOUD` наследуется excerpt/summary/prediction/aggregate/embedding-like placeholder и любым materially reconstructive descendant;
- неизвестный тип derivation/edge считается reconstructive и наследует наиболее строгую политику;
- broad permission и fixture metadata не понижают политику;
- declassification в F0 отсутствует;
- policy разрешается до export context и до чтения содержимого для adapter; сетевого adapter в F0 нет;
- local export отдельно проверяет export/audience policy; `NEVER_CLOUD` не означает автоматического разрешения plaintext export;
- property tests строят произвольные DAG, меняют порядок родителей и доказывают monotonicity, commutativity/idempotence где применимо, transitive closure и fail-closed cycles/unknowns.

## 8. Криптография, ключи и SQLCipher gate

### 8.1 Запрещенные заявления

Не пиши «secure», «military-grade», «zero-knowledge», «guaranteed deletion» или «production-ready». Python не гарантирует полное zeroization; SSD/OS remnants, unlocked endpoint, coercion и потеря всех recovery materials остаются рисками. Документируй их без маркетингового языка.

### 8.2 Key hierarchy

Реализуй versioned envelope pattern из `PS-04`–`PS-06` и `ADR-008`:

- случайный 256-bit Vault Master Key из OS CSPRNG;
- domain-separated database/blob/manifest keys через стандартный library KDF с versioned labels;
- OS-protected convenience wrap для **текущей фактически тестируемой ОС**;
- независимый recovery wrap того же VMK: Argon2id с per-vault random salt, параметрами в header и authenticated key wrap;
- recovery secret никогда не является database key, не передается argv/env, не логируется и не встраивается в backup;
- secret читается через injected `SecretSource`; интерактивный CLI использует masked TTY prompt; tests используют in-memory test source;
- raw keys не сериализуются и не попадают в exception/repr/core dump; best-effort очистка mutable buffers документирована как ограничение;
- states: `generated`, `active`, `rotation_pending`, `retired_for_write`, `retained_for_read`, `destroyed`;
- interrupted rotation resumable; retired key не шифрует новые объекты; неизвестный key/envelope version fail closed.

Используй только maintained, pinned cryptographic libraries. Конкретный AEAD/KDF profile, nonce size, AAD canonicalization и package versions зафиксируй в `docs/implementation/F0_LICENSE_CRYPTO_REVIEW.md`. Не реализуй crypto arithmetic самостоятельно. Для blob допустим только independently authenticated per-object envelope: random per-object data key, unique nonce, versioned authenticated metadata и wrap data key под versioned blob key. AAD включает как минимум magic, envelope version, vault ID, blob ID, key version и content length. Имена blobs — opaque IDs; plaintext digest не является путем/ID и, если нужен для synthetic duplicate test, хранится только keyed/encrypted.

### 8.3 SQLCipher profile gate

`sqlcipher` профиль доступен только если startup probe на реальном установленном driver/build доказал:

1. `PRAGMA cipher_version` возвращает ожидаемый non-empty version;
2. точный package/build и license зафиксированы;
3. database открывается правильным raw derived key и не открывается неправильным;
4. header не равен plaintext SQLite header;
5. synthetic sentinel не находится byte scan в database, WAL, journal, shared-memory и temp artifacts;
6. foreign keys, integrity check и выбранные cipher pragmas реально применены;
7. consistent encrypted backup/restore path поддерживается и тестируется;
8. locked/pinned dependency artifact воспроизводим для текущего target profile.

Обычный `sqlite3` разрешен только как явно названный `unsafe_synthetic_test` adapter в automated tests/ephemeral temp directory. Он недоступен из normal CLI composition, не принимает произвольные данные и никогда не удовлетворяет SQLCipher/real-data checks. Если SQLCipher probe не проходит, CLI выводит stable code `SQLCIPHER_PROFILE_UNAVAILABLE`, не создает vault и не fallback-ит.

SQL tracing запрещен. Key material не должно попадать в SQL logs/errors. Не полагайся на `secure_delete` или overwrite как доказательство physical erasure.

## 9. Blob/database atomicity и integrity

Реализуй явную restartable state machine для blob commit, а не «write file then insert row» без recovery:

1. зашифровать во controlled staging с новым opaque ID;
2. authenticate/read-back verify, flush/fsync где доступно;
3. зарегистрировать prepared metadata в transaction;
4. выполнить atomic rename/activation;
5. отметить active только после согласованного commit;
6. при restart детерминированно reconcile prepared/orphan state без догадок по filename и без удаления неизвестного ciphertext.

Reader видит только authenticated active blob. Любая authentication/integrity/schema failure останавливает writes и возвращает typed non-content error. Добавь fault points перед/после каждого шага, transaction commit, rename, fsync и manifest update. Проверь crash/retry/idempotency, concurrent nonce generation, orphan quarantine и full-disk simulation.

## 10. Audit, correction и deletion

`AuditEvent` — строгий allowlist schema. Разрешены только event code, UTC time, actor category/opaque ID, action/result code, target opaque ID/type, policy/rule/schema version, correlation ID и coarse duration/size bucket. Запрещены content, note/report/claim text, filenames/paths, search terms, assessment responses, prompts, diagnoses, third-party names, keys/tokens, exception dumps и stable content hashes. Debug mode не расширяет schema.

Correction создает новую version, закрывает старую и инвалидирует dependent derived records. Source bytes не переписываются. Supersession, rejection, invalidation и deletion имеют разные typed commands/status transitions.

Hard deletion обязана:

1. создать content-free dry-run plan с counts by type и external/backup limitations;
2. пройти ownership, provenance, derivation, evidence, snapshot, export и projection-manifest edges;
3. удалить roots и exclusive reconstructive descendants;
4. invalidировать/recompute mixed descendants без удаленного input;
5. удалить blob references и безопасно quarantine/collect authenticated orphan;
6. удалить content из historical versions, а не скрыть tombstone;
7. создать content-free receipt с request-local opaque references, counts, status и backup expiry horizon;
8. быть retryable/idempotent после fault;
9. доказать отсутствие удаленного synthetic marker в canonical queries, rebuilt state, новом export и product-controlled blobs/logs.

Не обещай удалить уже скопированные exports/offline backups. Backup expiry/crypto-erasure — отдельное состояние с честной границей контроля.

## 11. Migrations, backup/restore и export

### Migrations

- numbered, checksummed, directional migrations и schema-version table;
- preconditions, dry run, invariant checks, privacy/deletion impact и minimum reader;
- минимум один старый synthetic schema fixture и доказанный upgrade path;
- destructive migration требует verified encrypted backup и open export;
- failure не активирует частично migrated vault; rollback осуществляется через isolated validated restore, если надежный down-transform не доказан;
- migration не меняет temporal precision, policy, synthetic marker, rights или claim meaning молча.

### Backup/restore

- consistent database snapshot только через поддерживаемый driver API;
- package шифруется/authenticates до выхода из controlled staging;
- authenticated inventory охватывает database, blobs, schema/app/key-wrap versions и manifest;
- recovery secret не включается; recovery-wrapped VMK metadata допускается;
- output создается новым файлом/каталогом и не overwrites существующий путь;
- restore выполняется только в новый isolated target: authenticate → unwrap → inventory → database/blob integrity → migration dry-run → domain/policy/derivation invariants → projection rebuild/no-op → explicit activation;
- failed restore не меняет active vault и не удаляет package;
- tests: wrong secret, corrupt/missing/extra entry, rollback/stale cut-off, unsupported schema, interrupted restore/migration, full disk, OS wrapper unavailable и recovery-only success.

### Open export

Логически export содержит versioned JSONL records, JSON Schema 2020-12 schemas, UTF-8 Markdown data dictionary/summary и canonical manifest/checksums. Для F0 package по умолчанию authenticated encrypted; «open» означает открытые форматы после authorized decryption, а не plaintext на диске. JSON serialization детерминирована и versioned. Export не включает secrets, OS key material, audit content, internal absolute paths или неразрешенные policy records.

Сделай schema validation и synthetic semantic round trip в новый ephemeral vault через внутренний test reader. Это не general-purpose import integration и не становится CLI-командой импорта. CSV/Parquet/PDF/SQLite dump/FHIR не добавляй.

## 12. CLI contract

Normal CLI composition не имеет network/listener и не предлагает произвольный content input. Реализуй стабильные команды:

```text
psyche-os doctor --json
psyche-os gate status --json
psyche-os vault init --path PATH --profile sqlcipher
psyche-os vault verify --path PATH --json
psyche-os fixture list --json
psyche-os fixture load --path PATH --pack-id PACK_ID
psyche-os migrate plan --path PATH --json
psyche-os migrate apply --path PATH
psyche-os delete plan --path PATH --root-id UUID --scope SCOPE --json
psyche-os delete execute --path PATH --plan-id UUID
psyche-os backup create --path PATH --output NEW_PATH
psyche-os backup verify --package PATH --json
psyche-os restore verify --package PATH --target NEW_EMPTY_PATH --json
psyche-os restore activate --verified-target PATH --replace-empty PATH
psyche-os export create --path PATH --output NEW_PATH --audience personal_archive
psyche-os export verify --package PATH --json
psyche-os audit verify --path PATH --json
```

Recovery secrets запрашиваются masked TTY prompt, не flag/env. Non-interactive secret injection доступен только test composition. Любая команда проверяет synthetic-only marker и не отображает content: только IDs, counts, status, versions и non-sensitive error codes. JSON output имеет schema и не содержит stack trace. `doctor` отдельно показывает `sqlcipher_profile_verified`, `os_wrap_profile_verified`, `recovery_profile_verified`, platform/build и blockers. `gate status` всегда возвращает `CLOSED` в F0.

## 13. Точные deliverables

Адаптируй существующую структуру, не дублируй уже эквивалентные файлы. В результате должны существовать:

```text
pyproject.toml
uv.lock
src/psyche_os/**
migrations/**
schemas/export/v1/manifest.schema.json
schemas/export/v1/record.schema.json
schemas/export/v1/deletion_receipt.schema.json
schemas/export/v1/backup_manifest.schema.json
tests/unit/**
tests/property/**
tests/integration/**
tests/security/**
tests/faults/**
tests/contracts/**
tests/fixtures/**              # only manifest-declared synthetic fixtures
scripts/validate_f0_scope.py
scripts/validate_f0_artifacts.py
docs/implementation/F0_IMPLEMENTATION_REPORT.md
docs/implementation/F0_THREAT_TEST_MATRIX.md
docs/implementation/F0_LICENSE_CRYPTO_REVIEW.md
docs/implementation/F0_TEST_EVIDENCE.json
docs/architecture/REAL_DATA_GATE.yaml   # existing authoritative gate; keep CLOSED
artifacts/f0/sbom.cdx.json
```

`pyproject.toml` фиксирует Python `>=3.12`, exact direct dependency constraints, Ruff, mypy strict-enough settings, pytest, coverage и property-testing tooling. `uv.lock` должен быть актуален и использоваться frozen. Не добавляй runtime dependency без lock, license entry и rationale. Generated SBOM не содержит local paths/secrets.

Не создавай второй конкурирующий gate-файл. Сохрани schema и authority существующего `docs/architecture/REAL_DATA_GATE.yaml`; status остается `CLOSED`, `production_implementation_exists` остается `false`, а независимые/Phase 2 requirements остаются `UNSATISFIED`. Для действительно прошедших F0 controls можно добавить точные локальные evidence references и состояние synthetic-profile implementation, не смешивая его с разрешением real data. Даже если implementation findings пусты, gate остается `CLOSED`.

## 14. Порядок реализации

Работай фазами и после каждой запускай узкие тесты:

1. **Discovery/freeze:** входные документы, dirty worktree, target OS/profile, dependency/license feasibility, threat-to-test matrix.
2. **Scaffold/boundaries:** package, ports, CLI skeleton, dependency-direction test, synthetic guard.
3. **Pure domain:** IDs, versions, temporal values, provenance, claims/evidence/uncertainty/contradictions/unknown и invariants.
4. **Policy:** orthogonal composition, lineage DAG, unknown/cycle fail-closed property tests.
5. **Crypto/key envelope:** library profile, VMK/KDF, OS/recovery wraps, blob envelope, negative/known-answer/integrity tests.
6. **SQLCipher/storage:** runtime gate, schema/migrations, unit of work, version concurrency, blob state machine.
7. **Correction/deletion/audit:** typed transitions, dependency traversal, content-free schemas, fault recovery.
8. **Backup/restore/export:** authenticated packages, recovery-only isolated restore, schemas и semantic round trip.
9. **CLI:** только synthetic fixture workflows; stable JSON/error contract; отсутствие free-text/file/network paths.
10. **Adversarial assurance:** полный threat matrix, faults, scans, SBOM/license/secret/scope validation.
11. **Documentation/evidence:** exact versions, commands, test results, known limitations, no security overclaim, final diff review.

Не начинай следующий слой с временным plaintext/secrets shortcut, который может пережить фазу. Если secure dependency blocked, держи adapter unavailable и продолжай pure/domain tests отдельно.

## 15. Threat-derived tests и fault injection

`docs/implementation/F0_THREAT_TEST_MATRIX.md` должен сопоставить каждый релевантный `TM-*` с prevent/detect/recover control, test ID, evidence и residual risk. Как минимум реализуй:

- `TM-01`: wrong recovery secret/key, offline database/blob/header scan;
- `TM-02`: restore без OS wrapper только через independent recovery;
- `TM-03`: явно зафиксировать unlocked same-user endpoint как неустраненный риск; не выдавать at-rest encryption за защиту;
- `TM-04`: unique synthetic canary scan по DB/WAL/journal/shm/temp/blob/staging/log/backup/export; plaintext допустим только внутри контролируемой памяти теста и расшифрованного ephemeral round-trip reader;
- `TM-05`: opaque filenames/IDs, отсутствие plaintext/stable digest;
- `TM-09`: arbitrary lineage DAG и `NEVER_CLOUD` closure;
- `TM-13`: backup encrypted before boundary, tamper/wrong-secret/missing-entry rejection;
- `TM-14`: stale/rollback package не активируется молча;
- `TM-15`: corrupt/hostile package не overwrites active vault;
- `TM-16`: exception/fault после каждого commit/rename/fsync/migration/rotation/deletion/restore шага; retry/idempotency;
- `TM-17`: deletion closure across canonical/history/blob/derivation/export and mixed-descendant invalidation;
- `TM-18`: schema/property tests запрещенных audit/log fields и canary absence;
- `TM-19`: pinned hashes, SBOM, license/secret/vulnerability check; найденный Critical/High блокирует профиль;
- `TM-21`: swapped/truncated/bit-flipped blob/database/package detection и write stop;
- `TM-26`: real-data guard cannot be bypassed; repo/artifact scan не находит personal data/secrets;
- absence tests: нет listener/network/provider/import/FHIR/graph/vector/assessment-scoring dependency, module или CLI command.

Fault harness должен быть deterministic: named fault points, seeded schedule, точный before/after invariant и повторяемый test case. Не симулируй успех пустым mock. Для filesystem/database границ используй реальные temp directories/process restart tests там, где это существенно. Security tests не зависят от внешней сети.

## 16. Validation commands

Сделай команды ниже рабочими и запусти их из корня репозитория. Если среда использует другой уже существующий менеджер, сохрани один канонический frozen workflow и обнови этот список в implementation report с обоснованием; не держи два расходящихся lock flow.

```powershell
uv sync --frozen --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run pytest -q
uv run pytest tests/security tests/faults -q
uv run coverage run -m pytest
uv run coverage report --fail-under=90
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
uv run python -m psyche_os doctor --json
uv run python -m psyche_os gate status --json
git diff --check
git status --short
```

Дополнительно запусти platform-specific SQLCipher/OS-wrap/recovery integration suite. Все тесты работают без сети. Не маскируй skipped security test как pass: skip допустим только для явно нецелевого OS profile, отражается blocker-ом в evidence и не считается доказательством соответствующего контроля.

`F0_TEST_EVIDENCE.json` содержит UTC time, commit/worktree identity, OS/Python/dependency/SQLCipher/crypto versions, команды, exit codes, test counts, skipped/xfail, artifact digests, gate status и blockers; без username, home path, vault path, content или secrets.

## 17. Definition of Done

F0 считается **реализованным для synthetic target profile**, только если одновременно:

1. все обязательные normative документы прочитаны, конфликтов/placeholders нет;
2. scope validator доказывает отсутствие запрещенных modules/dependencies/commands и arbitrary content input;
3. domain/version/temporal/provenance/claim/policy database invariants имеют executable tests;
4. `NEVER_CLOUD` property suite проходит для произвольных DAG и неизвестных типов;
5. SQLCipher runtime probe, wrong-key test и plaintext artifact scans проходят на заявленном target profile без fallback;
6. OS wrap и независимый recovery wrap оба реально проходят; loss/corruption/rotation faults не мутируют данные;
7. blob/database crash protocol и integrity/tamper tests проходят;
8. correction и hard deletion проходят по всем реализованным entity kinds, historical versions и derivatives;
9. audit/log schemas остаются content-free при success/failure/debug paths;
10. encrypted backup → recovery-only isolated restore → invariant validation проходит; corrupt/stale package не активируется;
11. open logical export schema-valid и дает synthetic semantic round trip без secrets/internal paths;
12. migrations из минимум одной старой synthetic schema и failure recovery доказаны;
13. dependency lock, SBOM, license/crypto review, secret/synthetic-data scans и все validation commands проходят;
14. threat-test matrix не содержит неподтвержденного implemented control или unresolved Critical/High implementation finding;
15. diff не затрагивает исторические research inputs и не уничтожает параллельные изменения;
16. `REAL_DATA_GATE.status = CLOSED`, `opening_rule.automatic_opening_forbidden = true` и это подтверждает CLI;
17. report честно разделяет implemented/tested, planned, blocked и independently-unreviewed.

Отдельный end-to-end test обязан выполнить и проверить семантику последовательности: `synthetic create → correct → derive → add competing/contradicting evidence → preserve unknown → hard-delete selected root and dependencies → create/verify export → create encrypted backup → restore with independent recovery into a clean isolated target → re-run all invariants`. На каждом шаге сравнивай stable IDs/versions, transaction cut-offs, policy, provenance и отсутствие удаленного content; не ограничивайся проверкой exit code.

Если пункты 5–13 не могут быть доказаны, не называй F0 завершенным: выдай `F0_STATUS = BLOCKED` или `PARTIAL_SYNTHETIC_ONLY` с точными причинами. Даже полный технический pass дает только `F0_STATUS = SYNTHETIC_TARGET_IMPLEMENTED`; он не означает безопасность для реальных данных.

Независимые cryptographic/key/recovery, threat-model, privacy-lineage/deletion и clean-restore reviews не могут быть выполнены тем же implementation agent. До них запрещены формулировки «прошел независимый review» и любые security/certification claims.

## 18. Финальный отчет agent

В конце сообщи кратко и проверяемо:

- `F0_STATUS` и почему;
- что реализовано по слоям;
- какие решения/отклонения связаны с какими repo requirements;
- target OS, Python, SQLCipher и crypto profile versions;
- результаты exact validation commands, test count, skips/failures и threat-matrix coverage;
- Critical/High findings и blockers;
- список созданных/измененных файлов;
- Git branch/HEAD и наличие незакоммиченных пользовательских изменений;
- `REAL_DATA_GATE = CLOSED`;
- какие независимые reviews и Phase 2 проверки нужны дальше.

Не включай в ответ secrets, recovery material, raw keys, synthetic content bodies, absolute user-home paths или внешние данные. Не предлагай начать real-data ingestion, UI, LLM или иной следующий scope. Следующий допустимый шаг после технического F0 — Phase 2 synthetic assurance и независимый review, а не расширение продукта.
