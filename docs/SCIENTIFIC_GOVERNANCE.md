# PSYCHE OS v2 — scientific governance

**Статус:** нормативный научный контракт для research convergence и последующей реализации  
**Версия:** `2.0.0`  
**Срез знаний:** `2026-08-10`  
**Владелец:** `Scientific Governance Board`  
**Связанный реестр:** `ontology/psyche_domains.yaml`  
**Ограничение:** документ не является медицинским руководством и не разрешает работу с реальными данными

## 1. Назначение и область власти

Этот документ определяет, при каких условиях PSYCHE OS может хранить, связывать, вычислять и показывать научно нагруженные представления о человеке. Он управляет:

- внешними источниками знаний и их версиями;
- классификационными, исследовательскими и функциональными слоями;
- психометрическими инструментами и алгоритмами подсчёта;
- наблюдательными, статистическими, причинными и N-of-1 выводами;
- воспроизводимостью производных результатов;
- научным review, обновлением, отзывом и миграцией знаний;
- правами на тестовые материалы, руководства, нормы, переводы и intervention content.

Его власть ограничена. Он не заменяет клиническое суждение, юридическую консультацию, consent, privacy/security review или `REAL_DATA_GATE`. Научное одобрение означает только пригодность конкретного представления для конкретной цели и популяции. Оно не означает истинность, безопасность всех применений или разрешение на диагноз, лечение и триаж.

Основные инварианты:

1. `report != fact`; `memory != historical_fact`; `screening != diagnosis`.
2. `association != causation`; временное предшествование само по себе не доказывает влияние.
3. `LLM_output == proposal`; оно не становится evidence, observation или score.
4. Исходный материал, нормализация, измерение, интерпретация и классификационное отображение остаются разными слоями.
5. `unknown`, противоречие и неприменимость — допустимые результаты; система не обязана завершать историю.
6. Валидность относится к интерпретации для заданного `context_of_use`, а не к тесту «вообще» [MEAS-001–MEAS-003].
7. Система не заявляет «полную модель психики». Реестр доменов — версия навигационной схемы, открытая для исправления и удаления.
8. Любой вывод воспроизводим либо явно помечен как невоспроизводимое предложение с сохранённой provenance.

## 2. Единица научного решения

Научный review проводится не для абстрактной функции, статьи или шкалы, а для пары:

```text
ScientificDecision =
  representation_or_method
  × intended_use
  × target_population
  × language_and_locale
  × administration_or_data_mode
  × output_claim
  × risk_tier
  × version
```

Изменение любого множителя создаёт новое решение. Например, валидированная англоязычная шкала для группового исследования не получает автоматически разрешение на русскоязычный индивидуальный мониторинг; ассоциация в популяции не становится индивидуальным правилом; клинический код из документа не становится текущим диагнозом.

Каждое решение имеет:

- `decision_id`, версию и владельца;
- допустимую цель и явно запрещённые цели;
- набор поддерживающих и противоречащих источников;
- профиль доказательств по осям раздела 3;
- разрешённый тип утверждения и максимальный уровень причинности;
- права, ограничения, срок review и триггеры досрочного review;
- статус: `draft`, `approved_with_limits`, `research_only`, `suspended`, `deprecated` или `withdrawn`;
- журнал dissent и основание решения.

## 3. Иерархия источников и многомерная оценка

### 3.1. Классы источников

Класс задаёт начальную презумпцию, но не итоговый ранг:

| Класс | Типичный материал | Для чего особенно значим | Ограничение |
|---|---|---|---|
| `S1_binding_or_official` | закон, официальный classification, regulator guidance, нормативный стандарт | обязанности, официальная версия, intended scope | не доказывает эмпирическую эффективность каждого применения |
| `S2_systematic_synthesis` | systematic review, meta-analysis, evidence-based guideline | совокупность evidence и неоднородность | зависит от search date, включённых исследований и risk of bias |
| `S3_consensus_or_framework` | профессиональный consensus, reporting guideline, ontology/framework | терминология, минимальные процедуры, прозрачность | consensus не равен эмпирической валидности |
| `S4_strong_primary` | preregistered/large longitudinal, RCT, validation или field study | прямой эффект/свойство в изученном контексте | переносимость и replication остаются отдельными вопросами |
| `S5_emerging_primary` | пилот, новый метод, малая/узкая выборка | генерация гипотез | не основание для consequential claim |
| `S6_conceptual_or_critical` | теоретическая или критическая работа | альтернативы, hidden assumptions, falsification targets | не устанавливает величину эффекта |
| `S7_authoritative_technical` | официальный стандарт протокола, platform/vendor documentation | конкретное поведение формата, API или продукта | vendor source не подтверждает общую безопасность/научность |
| `S8_secondary_or_contextual` | обзор без систематического метода, учебный материал | ориентация и поиск первичных источников | не является load-bearing source без явного обоснования |

Источники более низкого класса не игнорируются: критическая работа может лучше выявить несостоятельность конструкта, чем официальный справочник; официальная документация лучше статьи описывает текущую политику конкретного API. Но `S5–S8` не могут в одиночку разрешать диагноз, лечение, рискованное вмешательство, clinical cutoff или персональный причинный вывод.

### 3.2. Обязательные оси appraisal

Нельзя сводить качество к одному числу или цвету. Для каждого load-bearing утверждения хранится профиль:

| Ось | Значения | Главный вопрос |
|---|---|---|
| `authority_and_status` | binding / official / consensus / independent / vendor / informal | кто издал и каков нормативный статус? |
| `directness` | direct / partially_direct / indirect | совпадают ли construct, цель, outcome и режим? |
| `design_rigor` | high / moderate / low / not_applicable | способен ли дизайн поддержать именно этот тип вывода? |
| `risk_of_bias` | low / some_concerns / high / unknown | какие systematic errors вероятны? |
| `measurement_fit` | adequate / partial / inadequate / unknown | валидны ли операционализация, scoring и change interpretation? |
| `population_transportability` | supported / plausible / unsupported / unknown | применимо ли к возрасту, языку, культуре, состоянию и setting? |
| `precision_and_heterogeneity` | adequate / limited / unstable / not_reported | каковы интервалы, вариативность и границы? |
| `independence_and_replication` | replicated_independent / replicated_related / single / contradicted | есть ли независимое повторение и конфликт? |
| `currentness` | current / review_due / superseded / retracted / unknown | актуальна ли конкретная версия на дату решения? |
| `rights_and_access` | cleared / restricted / metadata_only / unknown | разрешено ли хранить, показывать, считать и экспортировать? |
| `applicability_risk` | low / moderate / high / prohibited | какова цена ошибочного переноса? |

`unknown` не конвертируется в среднее значение. Для consequential use отсутствие данных по ключевой оси закрывает gate. Итог хранится как аргументированное решение, а не арифметическое среднее.

### 3.3. Минимальная достаточность

| Использование | Минимальное основание |
|---|---|
| Навигационный metadata tag | официальный/консенсусный источник либо два независимых peer-reviewed источника; no truth claim |
| Описательное резюме собственных записей | прослеживаемые исходные записи, явные границы окна, uncertainty и человеческая проверка |
| Scoring | точная разрешённая версия, детерминированный алгоритм, known-answer tests и language/population fit |
| Norm/cutoff/change claim | права на нормы, валидная версия и population/mode fit, measurement error и интерпретационные ограничения |
| Индивидуальная статистическая связь | достаточное within-person coverage, предзаданный estimand, autocorrelation/missingness/multiplicity checks [MEAS-032–MEAS-037] |
| Причинный вывод | дизайн и assumptions соответствуют уровню `C4+`; для индивидуального эффекта предпочтителен качественный N-of-1 [MEAS-038–MEAS-043] |
| Intervention candidate | запись в allowlist, evidence/certainty/harms/contraindications/rights и risk-tier gate [MEAS-044–MEAS-048] |
| Диагностическое/лечебное решение | вне автономной области PSYCHE OS; только квалифицированный специалист и применимое регулирование [CLIN-002–CLIN-005, CLIN-045–CLIN-050, ARCH-010–ARCH-015] |

## 4. Source Registry и knowledge snapshots

### 4.1. `KnowledgeSource`

Каждый load-bearing внешний источник регистрируется в `docs/research/SOURCE_REGISTRY.yaml` до использования. Минимальные поля:

```text
source_id, title, authors_or_organization, source_type,
publication_or_release_date, exact_version, canonical_url_or_doi,
accessed_at, evidence_class, domains, project_implications,
limitations, rights_notes, currentness_status, supersedes,
superseded_by, correction_or_retraction_status, review_due
```

Ссылка на веб-страницу без версии допустима только с `accessed_at` и коротким сохранённым утверждением о том, что именно было проверено. Для закона, классификации, API, лицензии и guideline требуется текущая официальная страница или текст. Агрегатор или поисковый результат не является canonical source.

### 4.2. `KnowledgeSnapshot`

Любой производный scientific output фиксирует неизменяемый manifest:

```text
snapshot_id, created_at, evidence_cutoff,
source_ids_and_versions, ontology_registry_version,
assessment_definition_versions, intervention_registry_versions,
algorithm_and_rule_versions, classification_release_versions,
code_digest, configuration_digest, locale, reviewer_decisions
```

Snapshot показывает, **с какими знаниями** был получен результат, но не замораживает истину. Новый snapshot не переписывает старый вывод. Diff обязан перечислять добавленные, исключённые, ослабленные, усиленные и вновь конфликтующие основания [ARCH-041–ARCH-043].

### 4.3. Currentness и retractions

Состояния источника:

- `current`: версия проверена и review ещё не просрочен;
- `review_due`: источник не объявлен неверным, но consequential use временно не расширяется;
- `corrected`: хранится correction notice; затронутые claims пересчитываются или помечаются;
- `superseded`: новая версия существует; старые snapshots остаются читаемыми;
- `retracted`: источник не поддерживает новые claims; существующие зависимости немедленно получают `invalidated_pending_review`;
- `withdrawn_or_legally_unavailable`: контент не используется, даже если библиографический факт сохраняется;
- `unknown`: currentness не подтверждена; consequential gate закрыт.

Процесс retraction/correction:

1. Зафиксировать событие и первичный официальный notice.
2. Найти `source_id` → `EvidenceLink` → `Claim` → `PersonalModelSnapshot` → export/projection dependencies.
3. Не удаляя историческую provenance, остановить новые derivations.
4. Пересмотреть, остаётся ли вывод поддержан независимыми источниками.
5. Создать новую версию/инвалидацию с объяснением пользователю; никогда не менять старый snapshot молча.
6. Если источник содержал licensed content, отдельно применить rights/deletion obligations.

## 5. Разделение классификационных и научных слоёв

### 5.1. Слои

| Слой | Роль | Допустимый output | Недопустимый переход |
|---|---|---|---|
| `RAW_SOURCE_REPORT` | что было предоставлено/сказано | source, locator, verbatim report, provenance | подлинность файла → истинность утверждения |
| `PHENOMENOLOGY` | форма, содержание, контекст, course, distress | normalized phenomenon с обратной ссылкой | phenomenon → диагноз/этиология |
| `FUNCTIONING_ICF` | activities, participation, barriers/facilitators | functioning assessment | impairment → конкретный disorder; хорошее functioning → отсутствие симптомов |
| `ICD_REFERENCE` | международная клиническая классификация | versioned mapping, созданный/подтверждённый допустимым actor | self-report/screen → диагноз |
| `DSM_REFERENCE` | versioned proprietary US clinical reference/crosswalk | документированный code/reference metadata | копирование criteria; lossless ICD↔DSM mapping |
| `RDOC_RESEARCH` | исследовательские domains и units of analysis | research tag с уровнем и версией | self-report → neural/genetic evidence; tag → diagnosis |
| `HITOP_RESEARCH` | dimensional/hierarchical covariance representation | research-only spectrum/dimension mapping | model fit → causal ontology или treatment selection |
| `TRAIT_AND_STATE` | traits, facets и контекстные состояния | instrument-native estimate или observation | один эпизод → trait; Big Five ↔ HEXACO lossless conversion |
| `DEVELOPMENT_AND_NARRATIVE` | lifespan context и текущая смысловая история | competing developmental hypotheses | взрослый pattern → восстановленная причина детства |
| `THRIVING_AND_VALUES` | strengths, valued action, meaning, quality of life | positive-functioning/strength claims | strengths → отсутствие disorder/distress |
| `AI_PROPOSAL` | черновая формулировка, альтернативы, вопросы | `proposed` claim | proposal → evidence/diagnosis/fact |

ICD-11 используется как основной международный clinical terminology reference, DSM-5-TR — как отдельный versioned crosswalk там, где он нужен. Оба предназначены для клинического контекста; тексты и mappings не превращаются в алгоритм самодиагностики [CLIN-002–CLIN-005]. RDoC является research framework, HiTOP — исследовательской dimensional taxonomy; ни один не заменяет диагноз, functioning или феноменологию [CLIN-006–CLIN-010]. ICF/WHODAS и quality-of-life constructs остаются отдельными от symptom classification [CLIN-037–CLIN-040].

### 5.2. Mapping contract

Любой crosswalk — направленное утверждение:

```text
mapping_id, source_concept_id, target_scheme_and_version,
target_concept_id, relation,
mapping_authority, basis_source_ids,
scope, uncertainty, known_loss, review_due
```

Допустимые relations: `exact`, `narrower`, `broader`, `related`, `overlaps`, `no_safe_mapping`. `exact` требует строгого доказательства эквивалентности; симметричность не предполагается. Если rights запрещают embedding definitions, хранятся только разрешённые code/URI и ссылка.

## 6. Psychometrics governance

### 6.1. Deny-by-default registry

Инструмент не предъявляется и не считается, пока `AssessmentDefinition` не прошёл все применимые gates. Наличие статьи, PDF, онлайн-калькулятора или опубликованных пунктов не доказывает права на использование [MEAS-001–MEAS-006, MEAS-011].

| Gate | Доказательство | Fail-closed результат |
|---|---|---|
| `P0_identity_and_use` | точное название, owner, version, construct, intended use, population, mode, recall period | `metadata_only` |
| `P1_rights` | copyright/license, право хранить и показывать items, считать, переводить, экспортировать, распространять | `rights_blocked` |
| `P2_version_integrity` | source form, response options, missing rules, scoring manual и update history согласованы | `version_unresolved` |
| `P3_language_translation` | authorized translation/adaptation, locale, cognitive debriefing и документация процесса | `unvalidated_translation` |
| `P4_measurement_evidence` | content/structural validity, reliability, error, hypotheses, cross-cultural validity/invariance, responsiveness по цели | `research_only` или `not_scored` |
| `P5_scoring_implementation` | детерминированный versioned algorithm, edge cases, synthetic known-answer vectors, independent review | `scoring_disabled` |
| `P6_interpretation` | нормы/thresholds/change rule относятся к версии, языку, population и context of use | raw response/score only, без norm/cutoff claim |
| `P7_monitoring_and_burden` | retest/practice/reactivity, cadence, stop rules, burden и harm review | repeated use disabled |

### 6.2. Rights matrix

Права проверяются раздельно:

```text
view_items, store_items, collect_responses, store_responses,
score_locally, store_score, display_interpretation,
use_norms_or_cutoffs, translate_or_adapt,
export_content, distribute_implementation, use_in_research
```

Неясность любого требуемого права означает `deny`. Citation не заменяет license. Публичная доступность не означает public domain. Тексты тестов, manuals, scoring keys и norm tables не помещаются в Git без документированного разрешения.

### 6.3. Перевод и measurement invariance

Пользовательский перевод или LLM-перевод получает статус `unvalidated_translation`. Для русскоязычного approved use требуются правообладательская процедура, forward/reconciled translation, обратная/экспертная проверка, cognitive debriefing, locale/population documentation и evidence измерительных свойств [MEAS-004–MEAS-006].

Сравнение групп или времени требует соответствующего уровня invariance. Configural/metric/scalar и, при необходимости, residual/longitudinal invariance оцениваются раздельно. Partial invariance разрешается только с заранее описанным правилом и sensitivity analysis. Недостаточная мощность или незначимый DIF не доказывают эквивалентность [MEAS-009].

### 6.4. Scoring contract

- LLM не подсчитывает score, не выполняет reverse coding, missing-item rule, norm lookup или cutoff classification.
- Алгоритм привязан к exact form/version/language и имеет hash, test vectors и reviewer sign-off.
- Missing не заменяется догадкой; без разрешённого правила результат `not_scored`.
- Raw score, transformed score, standard error/interval, norm reference и interpretation — разные поля.
- Internal consistency не используется без structural validity; statistical change не равен meaningful change.
- Score version drift блокирует сравнение до explicit comparability decision.
- Скрининговый порог создаёт `screening_result`, но не `diagnosis` и не treatment recommendation.
- Proprietary content не попадает в log, prompt, telemetry или unrestricted export.

## 7. Claim governance

### 7.1. Типы и жизненный цикл

Поддерживаются типы `descriptive`, `pattern`, `interpretive`, `narrative`, `statistical_association`, `causal_hypothesis`, `prediction`, `clinical_mapping`, `trait_estimate`, `functioning_assessment`, `strength_or_resource`, `recommendation_candidate`.

Статусы не означают истину:

- `proposed`: черновик человека, правила или модели;
- `supported`: есть typed evidence, но сохраняются scope и uncertainty;
- `contested`: есть существенное противоречие;
- `accepted_working_representation`: пользователь принял как текущую рабочую формулировку;
- `rejected`: рассмотрено и отклонено с основанием;
- `superseded`: заменено новой версией, историческая provenance сохранена;
- `invalidated`: вход, метод, права или source status больше не поддерживают claim;
- `expired_pending_review`: истёк review или context изменился.

`EvidenceLink` имеет direction `supports`, `contradicts`, `qualifies`, `contextualizes` или `does_not_address`; независимая репликация не подменяется числом ссылок на одну data set. Claim без evidence допустим только как `unsupported_proposal`.

### 7.2. Claim-strength ceiling

Сила формулировки не может превышать самое слабое load-bearing звено:

```text
claim_ceiling = min(
  source_applicability,
  measurement_fit,
  design_identification,
  population_transportability,
  currentness,
  rights_permission,
  reviewer_authority
)
```

Это логическое ограничение, не числовой score. Высокое качество статьи не компенсирует неверный язык шкалы; большой объём passive data не компенсирует construct mismatch; человеческое принятие гипотезы не превращает её в факт.

### 7.3. Causality ladder

| Уровень | Минимальное основание | Разрешённый язык |
|---|---|---|
| `C0_observation` | прослеживаемая запись/измерение | «сообщено», «наблюдалось» |
| `C1_cooccurrence` | совпадение в определённом окне | «совпадало», «сопровождалось» |
| `C2_temporal_precedence` | X повторно предшествует Y при приемлемом coverage | «предшествовало», «возможный сигнал» |
| `C3_replicated_within_person_association` | предзаданный lag, serial-dependence model, replication/sensitivity | «устойчивая внутрииндивидуальная ассоциация» |
| `C4_quasi_experimental` | ITS/multiple baseline/natural experiment и явные assumptions | «совместимо с эффектом при указанных допущениях» |
| `C5_randomized_single_case` | рандомизированные повторные периоды, carryover/washout analysis | «оценка индивидуального эффекта в этом протоколе» |
| `C6_replicated_n_of_1_or_trial` | качественная репликация/испытание в ограниченной target scope | «эффект поддержан в данном дизайне/популяции» |

Для `C4+` до анализа фиксируются estimand, counterfactual logic/causal diagram, exchangeability/consistency/positivity assumptions, concurrent events, missingness и sensitivity analysis [MEAS-038, MEAS-039]. Ни один уровень не разрешает универсальную этиологическую историю человека.

### 7.4. N-of-1 governance

Design tiers:

- `D0_tracking`: наблюдение, максимум `C0–C2`;
- `D1_exploratory_AB`: одна смена, только hypothesis;
- `D2_repeated_phase`: ABA/ABAB или multiple baseline, потенциально `C4`;
- `D3_randomized_crossover`: повторный рандомизированный crossover, потенциально `C5`;
- `D4_replicated_series`: несколько качественных single-case protocols, потенциально `C6` в ограниченной scope.

CENT/SPENT/SCRIBE и N-of-1 design guidance задают минимальную прозрачность, но не гарантируют валидность конкретного исследования [MEAS-040–MEAS-043].

Action risk tiers:

- `R0_observational`: допустимо при consent и burden limits;
- `R1_low_reversible`: self-directed только при обратимости, stop criteria и отсутствии клинической цели;
- `R2_moderate_or_symptom_targeting`: только approved protocol и qualified clinical/professional review;
- `R3_prohibited_autonomous`: лекарства/дозы/отмена, вещества, опасное голодание/sleep restriction, trauma exposure, self-harm или управление острым состоянием — система не предлагает и не оптимизирует.

Модель не может понижать tier. Adverse event или новый contraindication останавливает протокол до human review.

## 8. Reproducibility contract

### 8.1. Детерминированный pipeline

Каждый scoring, normalization, statistic, migration и export проходит:

1. versioned input schema и immutable source references;
2. validation с явными rejected/missing records;
3. versioned deterministic transformation;
4. `DerivationRun` с code/config/environment digests;
5. synthetic known-answer и property/invariant tests;
6. machine-readable output schema;
7. uncertainty, limitations и knowledge snapshot;
8. independent rerun для consequential algorithms.

Randomized methods фиксируют algorithm, seed и RNG version. Floating-point tolerance объявляется заранее. Результат, который нельзя повторить в поддерживаемой среде, получает `reproducibility_failed` и не используется для consequential claim.

### 8.2. LLM runs

LLM-run хранит provider/model snapshot or alias, system contract, prompt-template version, exact input record IDs/categories, redaction transformations, locale, structured-output schema, timestamp, policy snapshot и deterministic post-validations. Содержимое sensitive prompt не дублируется в audit log [ARCH-039, ARCH-040].

Поскольку одинаковый LLM-вызов может не быть bitwise reproducible, сохраняются исходный output и provenance; rerun создаёт нового кандидата, а не перезаписывает старый. Ни majority vote моделей, ни self-consistency не превращают output в evidence. Импортированный текст считается недоверенным content и не может менять scientific policy [ARCH-031, ARCH-032].

### 8.3. Audit package

Для review воспроизводится package без реальных данных: schema, synthetic fixture, source/snapshot manifests, executable deterministic rules, expected outputs, rights metadata и reviewer decisions. Экспорт использует versioned JSON Schema и canonical manifest; provenance следует явным entity/activity/agent links [ARCH-041–ARCH-043].

## 9. Роли и независимость review

| Роль | Обязанность | Не может единолично разрешить |
|---|---|---|
| `scientific_methodologist` | evidence appraisal, design, inference ceiling, reproducibility | клиническое использование или права |
| `clinical_safety_reviewer` | scope, diagnostic/treatment boundary, harm/escalation, vulnerable contexts | scientific validity вне компетенции |
| `psychometrician` | construct, validity, reliability, invariance, scoring/change | copyright/license и clinical use |
| `domain_specialist` | substantive interpretation и альтернативы | cross-domain generalization |
| `privacy_security_reviewer` | disclosure, minimization, lineage, abuse cases | научную валидность |
| `rights_legal_reviewer` | license, copyright, regulation, jurisdiction | clinical or scientific efficacy |
| `lived_experience_accessibility_reviewer` | burden, stigma, language, accessibility, agency | causal identification или licensing |
| `data_steward_maintainer` | registry integrity, versions, migrations, source monitoring | consequential scientific approval |

Минимальное одобрение:

- low-risk metadata/ontology change: methodologist + domain specialist + maintainer;
- assessment enablement: psychometrician + rights reviewer + methodologist; clinical safety reviewer для screening/clinical constructs;
- `R2` intervention или safety feature: clinical safety + methodologist + domain specialist + rights/privacy as applicable;
- classification/mapping change: domain specialist + methodologist + rights reviewer;
- `C4+` causal or predictive feature: methodologist/statistician + independent reproducer + clinical safety reviewer when health-related.

Автор не является единственным approver. Reviewer декларирует conflict of interest, competence and recusal. Dissent сохраняется, а не сглаживается голосованием. Для single-user research maintainer может совмещать роли только в `research_only`; production gate остаётся закрытым до независимого review.

## 10. Обновление, deprecation и migration

### 10.1. Cadence

| Частота | Действие |
|---|---|
| Непрерывно | retraction/correction, safety/regulatory alert, license withdrawal, critical vulnerability |
| Ежемесячно | triage новых official releases, retractions и high-risk evidence |
| Ежеквартально | currentness laws/API/security/provider policies и `review_due` consequential sources |
| Каждые 6 месяцев | classifications, assessment versions, clinical/digital-health guidelines, intervention allowlist |
| Ежегодно | полный audit source coverage, ontology, scoring implementations, reviewer matrix и reproducibility suite |
| Перед release/real-data gate | целевой resnapshot всех time-sensitive и jurisdiction-specific источников |

Досрочные triggers: новая classification edition; изменённый test manual/license/translation; device/algorithm update; retraction; material guideline reversal; новое contraindication/harm; перенос на другую population/language/mode; provider retention change; выявленная non-invariance; невозможность воспроизведения.

### 10.2. Deprecation

Deprecation не удаляет историю. Запись получает:

```text
deprecated_at, reason, replacement_id_or_none,
affected_uses, migration_required, last_safe_version,
new_derivation_policy, user_communication, deletion_or_rights_action
```

`deprecated` запрещает новые derivations, но позволяет читать version-pinned history. `withdrawn` дополнительно блокирует показ/использование контента, если этого требуют safety или права. Идентификатор не переиспользуется для нового смысла.

### 10.3. Migration

- semantic change всегда повышает registry/schema version;
- изменение definition не переписывает старые records; используется mapping/migration assertion;
- migration имеет dry run, backup, rollback plan, synthetic fixture и invariant checks;
- lossy transformation объявляет потерю и сохраняет source reference;
- derived outputs инвалидируются и пересчитываются только из допустимых inputs;
- old→new mapping направлен и может быть `no_safe_mapping`;
- после migration сравниваются counts, provenance closure, rights/privacy labels и snapshot readability.

## 11. Конфликт, фальсификация и epistemic humility

### 11.1. Conflict handling

Система не выбирает победителя потому, что источник новее, увереннее сформулирован, чаще процитирован или создан человеком/LLM. `ContradictionSet` фиксирует scope, time, source independence и тип конфликта. Возможные resolution states:

`unresolved`, `different_contexts`, `different_times`, `source_error`, `superseded`, `both_partly_hold`, `cannot_resolve`.

Если conflict затрагивает consequential output, вывод ослабляется или приостанавливается. Противоречащие данные остаются видимыми в пределах privacy/rights.

### 11.2. Falsification discipline

Каждая interpretive/causal/predictive гипотеза должна содержать:

- альтернативные объяснения;
- какие наблюдения поддержали бы и какие ослабили бы её;
- time window и target scope;
- confounders и measurement failure modes;
- expiry/review trigger;
- максимальный допустимый claim level;
- stop criteria для эксперимента.

Невозможная к опровержению история хранится как narrative/meaning, не scientific explanation. Vividness, narrative coherence, emotional intensity и confidence не доказывают accuracy памяти; source monitoring и corroboration моделируются отдельно [CLIN-024–CLIN-027]. Lifespan paths допускают equifinality/multifinality и не реконструируются детерминистически [CLIN-016–CLIN-018].

### 11.3. Negative and null evidence

Отсутствие записи не означает отсутствие явления. Missingness, отказ отвечать, неприменимость, rights block, measurement failure и «не спрашивали» различаются. Null result хранит precision, power/sensitivity, analysis plan и coverage; он не становится доказательством нулевого эффекта без достаточной информативности.

## 12. Copyright, licenses и научная добросовестность

1. В репозитории хранятся библиографические metadata, собственные краткие выводы и разрешённые open materials; не полные copyrighted articles/manuals/items.
2. DSM text, proprietary diagnostic criteria, test items, scoring keys, norm tables, manuals и intervention content не копируются без проверенных прав [CLIN-005, MEAS-006, MEAS-011].
3. Генерация или перевод copyrighted items через LLM не обходят права и не создают валидную адаптацию.
4. `rights_notes` и exact license/version обязательны; «free online» не является лицензией.
5. Attribution, share-alike, non-commercial, no-derivatives и jurisdictional limits исполняются отдельно.
6. Citation обязана указывать первичный источник; secondary source не маскируется как original evidence.
7. Retracted/corrected work обозначается явно; citation laundering и cherry-picking запрещены.
8. Заимствованные tables/figures/code/data требуют отдельной проверки; ссылка сама по себе не даёт право встраивания.
9. Synthetic fixtures не имитируют copyrighted item wording и не содержат реальные персональные данные.

## 13. Машинно-проверяемые gates

Перед merge scientific feature CI/validation должны доказать:

- все cited IDs существуют в `SOURCE_REGISTRY.yaml` и не помечены `retracted` без documented exception;
- `KnowledgeSnapshot` фиксирует exact source, ontology, assessment, intervention и algorithm versions;
- ontology domain IDs уникальны, references существуют, layer/claim/evidence/sensitivity значения входят в enums;
- assessment имеет положительные gates `P0–P7` для requested use;
- LLM не является scorer, evidence source или policy authority;
- claim имеет evidence link либо `unsupported_proposal`, uncertainty и ceiling;
- `C4+` имеет causal design/assumptions; N-of-1 имеет design/risk tier и stop rules;
- deprecated/withdrawn definitions не используются в новых derivations;
- migration и deterministic algorithms проходят synthetic known-answer/invariant tests;
- copyrighted content и реальные данные отсутствуют;
- `REAL_DATA_GATE` остаётся `CLOSED`, пока независимые scientific, clinical, privacy/security, recovery/deletion и rights reviews не завершены.

## 14. Основания текущего контракта

Ключевые группы источников:

- феноменология, classifications и research taxonomies: [CLIN-001–CLIN-010];
- traits, lifespan, narrative и memory humility: [CLIN-011–CLIN-027];
- cognition, neurodevelopment, emotion и functioning: [CLIN-028–CLIN-040];
- clinical/AI boundaries: [CLIN-045–CLIN-050, ARCH-010–ARCH-015];
- psychometric standards, translation, invariance и rights: [MEAS-001–MEAS-011];
- repeated measurement, EMA, sensors и burden: [MEAS-012–MEAS-031, ARCH-049–ARCH-053];
- longitudinal inference, causality и N-of-1: [MEAS-032–MEAS-043];
- intervention evidence and harms: [MEAS-044–MEAS-048];
- reproducibility/provenance/schema/provider constraints: [ARCH-031, ARCH-032, ARCH-039–ARCH-043].

Полные библиографические записи, limitations, rights notes и review dates находятся в source registry. Ссылки этого документа не заменяют чтение этих полей.

## 15. Acceptance criteria

Scientific governance считается реализованным только если:

1. Он представлен не только текстом, но и enforceable registries/gates.
2. Пользователь видит источник, время, scope, uncertainty, contradiction и статус proposal/working representation.
3. Исправление, supersession, retraction и deletion проходят по dependency graph.
4. Любое scoring/analysis можно повторить на synthetic fixture.
5. Ни classification, ни research dimension, ни LLM не становятся скрытой identity ontology.
6. Rights-deny-by-default блокирует неопределённый контент.
7. Review overdue, conflict или non-reproducibility ослабляют/останавливают вывод автоматически.
8. Реестр доменов явно утверждает неполноту, версионируется и допускает `no_safe_mapping`.
9. Consequential вывод требует независимого компетентного review.
10. До отдельного решения используются только синтетические данные, а `REAL_DATA_GATE` остаётся закрытым.
