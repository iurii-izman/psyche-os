# PSYCHE OS Master Specification v2.0 FINAL

> **Supersession status (2026-08-28):** This is the retained v2.0 research/foundation specification. Its product center, product-experience priority, LLM role and roadmap are superseded by [`PSYCHE_OS_MASTER_SPEC_v2.1_PRODUCT_REORIENTATION.md`](PSYCHE_OS_MASTER_SPEC_v2.1_PRODUCT_REORIENTATION.md). Its scientific, epistemic, privacy, security, storage, recovery, deletion, temporal and provider-independence contracts remain authoritative unless that successor explicitly says otherwise. This note changes routing, not the historical v2.0 record.

**Product category:** Personal Evidence & Reflection System  
**Specification version:** 2.0.0-research-final  
**Evidence snapshot:** 2026-08-10  
**Primary language:** Russian; stable technical identifiers are English  
**Authority:** primary product, scientific and architecture source of truth  
**RESEARCH_CONVERGED:** `true`  
**IMPLEMENTATION_READINESS:** `F0_SECURE_FOUNDATION_ONLY`  
**REAL_DATA_GATE:** `CLOSED`  
**Production application:** does not exist; this specification does not claim clinical, security or regulatory validation

## 1. Назначение и форма продукта

PSYCHE OS — локальная система сохранения личных свидетельств и рефлексии. Она помогает одному владельцу:

- сохранять исходные материалы, сообщения от источников, наблюдения и измерения;
- видеть, что именно было сообщено, когда, кем и на каком основании;
- отделять источник от нормализации, интерпретации, статистики и AI-предложения;
- сопоставлять поддерживающие и противоречащие свидетельства;
- хранить неизвестное, альтернативы, пересмотры и исторические версии понимания;
- анализировать изменения осторожно, без превращения корреляций в причины;
- исправлять, экспортировать и удалять данные вместе с подконтрольными производными;
- оставаться полезной без LLM, облака, подписки и конкретного поставщика.

`PersonalModelSnapshot` — датированный производный снимок текущих рабочих утверждений, противоречий и неизвестного. Это не цифровой двойник, диагноз, окончательная идентичность, чтение мыслей или объективно полная модель человека.

### 1.1 Для кого

Исходный профиль — один взрослый владелец на лично контролируемом устройстве. Исследовательская спецификация не разрешает детское, многопользовательское, клиническое, корпоративное, совместное или удалённое использование. Любой такой профиль создаёт новые роли, обязанности и границы доверия.

### 1.2 Non-goals

PSYCHE OS не является и не обещает:

- психотерапевта, психиатра, врача, кризисного монитора или спасательную службу;
- автономную диагностику, исключение диагноза, лечение, триаж или назначение;
- объективное восстановление биографии или «вытесненных» воспоминаний;
- доказательство мотивов/состояния третьих лиц;
- универсальный показатель психического здоровья, p-factor, «процент познанности» или flourishing score;
- детектор лжи, нейропсихологическое обследование или медицинский прибор;
- непрерывное наблюдение, surveillance, social scoring или оптимизацию вовлечённости;
- замену исходным документам, квалифицированной оценке или человеческим отношениям;
- абсолютную безопасность, вечную доступность либо гарантированное удаление копий вне контроля.

## 2. Нормативные документы и приоритет

1. `CONSTITUTION.md` — неизменяемые принципы; эта спецификация раскрывает их смысл.
2. Этот Master Spec — подробный продуктовый и implementation contract.
3. `docs/architecture/DATA_MODEL.md`, `SYSTEM_ARCHITECTURE.md`, `PRIVACY_SECURITY_MODEL.md`, `MENTAL_HEALTH_AI_SAFETY.md`, `THREAT_MODEL.md` — нормативные технические/безопасностные уточнения.
4. `docs/SCIENTIFIC_GOVERNANCE.md` и `ontology/psyche_domains.yaml` — научный lifecycle и версионируемый реестр доменов.
5. `docs/DECISION_LOG.md` — основания и пересмотр решений.
6. `docs/research/*` и `docs/reviews/*` — evidence trail, а не прямые runtime-требования.
7. `docs/prompts/F0_IMPLEMENTATION_PROMPT.md` — точная ограниченная следующая задача.

При конфликте действует более строгая защита достоинства, доказательности, приватности, удаления, восстановимости и границы клинических утверждений. Удобство и возможности модели не ослабляют инварианты.

## 3. Термины

| Термин | Нормативное значение |
|---|---|
| `Vault` | Локальная граница владения, политики, ключей, канонических данных и recovery. |
| `SourceArtifact` | Неизменяемый импортированный/созданный исходный объект; может быть удалён. |
| `Report` | Атрибутированное сообщение человека/источника; не обязательно исторический факт. |
| `MemoryReport` | Автобиографический report с отдельными измерениями уверенности, яркости, времени, источника и corroboration. |
| `Observation` | Контекстно ограниченное наблюдение с наблюдателем и методом. |
| `Measurement` | Значение конкретного измерительного процесса/протокола, а не автоматически конструкт. |
| `Assertion` | Нормализованное близкое к источнику высказывание с provenance. |
| `Claim` | Интерпретативное, статистическое, клиническое либо иное проверяемое утверждение. |
| `EvidenceLink` | Типизированная связь supports/contradicts/qualifies/contextualizes/и др. |
| `DerivationRun` | Неизменяемая запись метода, входов, версий, параметров и результатов преобразования. |
| `ContradictionSet` | Набор несовместимых assertions/claims с типом и состоянием разрешения. |
| `Unknown` | Значимое неизвестное с причиной, вопросом и возможным evidence для уменьшения неопределённости. |
| `PersonalModelSnapshot` | Неизменяемая версия текущего рабочего личного представления. |
| `KnowledgeSnapshot` | Точный манифест научных источников, онтологий, instruments, algorithms и policy versions. |
| `Projection` | Перестраиваемый graph/search/vector/analytics/report view; не канонические данные. |
| `NEVER_CLOUD` | Запрет облачного раскрытия исходника и материально реконструирующих производных. |
| `Real-data gate` | Формальное решение о допуске реальных глубоко чувствительных данных к конкретной проверенной сборке/профилю. |

Слова «валидирован», «безопасен», «диагноз», «причина», «лечение», «клинически значимый» и «анонимный» используются только при явно указанном основании и scope.

## 4. Конституционные инварианты

Реализация обязана обеспечить двадцать инвариантов из `CONSTITUTION.md`. Кратко:

1. авторство целей/значений и контроль остаются у пользователя;
2. model output никогда не становится source evidence;
3. verbatim, normalized и derived раздельны;
4. память — report, не факт;
5. screening ≠ diagnosis;
6. correlation ≠ causation;
7. population evidence ≠ individual determination;
8. uncertainty/conflict/unknown — first-class;
9. claims пересматриваемы и фальсифицируемы;
10. core local и provider-independent;
11. privacy наследуется по lineage;
12. disclosure минимально и receipt-based;
13. encryption/recovery/backup до реальных данных;
14. deletion проходит по dependency graph;
15. imports/model output untrusted;
16. AI не человек/терапевт/эксклюзивная связь;
17. crisis support честно ограничен;
18. science/rights/version управляются;
19. open exit и lifetime durability обязательны;
20. synthetic-first gate не открывается от одной документации.

Ни feature flag, migration, debug mode, provider contract, disclaimer или пользовательский click не может незаметно ослабить их.

## 5. Научная и клиническая модель

### 5.1 Независимые слои

Система не строит одну клиническую онтологию. Она поддерживает независимо версионируемые слои:

1. исходный artefact и verbatim report;
2. феноменология, поведение, контекст и течение;
3. observation/measurement/assessment result;
4. symptoms/states/episodes и functioning;
5. patterns/associations;
6. рабочие hypotheses/formulations/causal candidates;
7. clinical mappings ICD/DSM с qualified origin;
8. research mappings RDoC/HiTOP;
9. personality traits/facets;
10. QoL, values, goals, strengths, resources и thriving;
11. versioned personal model.

Это не лестница возрастания «истины». Claim может опираться непосредственно на measurement; clinical note может оставаться источником, но не превращать все содержащиеся выводы в каноническую истину.

### 5.2 Phenomenology first

Феномен включает исходные слова, форму/содержание опыта, onset/course, context/triggers, distress, conviction/insight, impact и competing interpretations [CLIN-001]. Нормализованный label не заменяет report. Один и тот же текст в разном контексте может иметь разный смысл; система не решает это скрытой классификацией.

### 5.3 Clinical classification

- ICD-11 CDDR — primary international reference; system/release/code/date/source всегда хранятся [CLIN-002–CLIN-004].
- DSM-5-TR — secondary proprietary US crosswalk; edition/update/rights обязательны [CLIN-005].
- RDoC — research tagging, не diagnosis; unit of analysis сохраняется [CLIN-006].
- HiTOP — optional dimensional mapping с уровнем/версией/indicators; не causal ontology/treatment selector [CLIN-007, CLIN-008].
- `p-factor` запрещён как personal/root/causal/health score [CLIN-009, CLIN-010].

Только атрибутированный квалифицированный специалист может импортировать diagnostic formulation как `clinician_attributed_claim`. PSYCHE OS не создаёт, не подтверждает и не исключает диагноз. Хорошее функционирование не исключает distress/condition; impairment не доказывает конкретный диагноз.

### 5.4 Differential reasoning boundary

Система может перечислить открытые категории альтернатив (`sleep_related`, `substance_related`, `medication_or_medical_context`, `measurement_change`, `life_event`, `unknown`) и предложить обсудить red flags с профессионалом. Она не выбирает медицинскую причину, не советует тесты/лекарства и не задерживает помощь ради дальнейшего tracking [CLIN-045].

## 6. Эпистемическая модель

### 6.1 Источник не равен утверждению

Наличие authentic file доказывает лишь сохранность файла, не истинность его содержания. Слова пользователя доказывают факт report, не обязательно событие. Clinician record доказывает атрибутированную документацию, не окончательную этиологию. Score доказывает результат конкретной администрации/алгоритма, не сущность человека. LLM output доказывает только выполнение derivation.

### 6.2 Multi-axis source appraisal

Одномерный evidence tier заменён независимыми осями:

- authenticity/integrity;
- directness и relevance;
- source independence;
- method/measurement quality;
- temporal/scope match;
- population/external validity;
- consistency/conflict;
- currentness;
- rights/permitted use.

Ни одна ось не компенсирует автоматически другую. Несколько перепечаток одного источника не считаются независимой corroboration.

### 6.3 Claim types and status

Типы: `descriptive`, `pattern`, `interpretive`, `narrative`, `statistical_association`, `causal_hypothesis`, `prediction`, `clinical_mapping`, `trait_estimate`, `functioning_assessment`, `strength_or_resource`, `recommendation_candidate`.

Статусы: `proposed`, `user_accepted`, `active`, `contested`, `rejected`, `superseded`, `withdrawn`, `invalidated`. `user_accepted` означает рабочее принятие, не proof.

### 6.4 Uncertainty

Не существует одного `confidence_percent`. Хранятся источник/authenticity, measurement error, construct validity, temporal, interpretation, model/parameter, confounding, external validity, missingness и rights uncertainty. Качественные `low/moderate/high/unknown/not_applicable` имеют rationale. Численный interval допустим лишь для названного estimand/method.

### 6.5 Contradiction

Конфликт не разрешается по новизне, красоте объяснения или авторитету модели. Допустимые исходы: `unresolved`, `different_contexts`, `different_times`, `source_error`, `superseded`, `both_partly_hold`, `cannot_resolve`. Активное summary показывает материальный конфликт.

### 6.6 Unknown and missingness

`not_observed`, `not_asked`, `declined`, `forgotten`, `not_applicable`, `measurement_failed`, `source_unavailable`, `ambiguous`, `rights_blocked` различаются. Отсутствие данных не становится отрицательным фактом. Неизвестное включает, что могло бы его уменьшить и стоит ли burden/safety задавать вопрос.

### 6.7 Falsification

Каждый существенный hypothesis/interpretation содержит альтернативы, evidence которое ослабит claim, review trigger и scope. Система должна уметь показать «почему сейчас так», «что против», «что изменилось» и «что мы не знаем».

## 7. Версионируемая доменная онтология

`ontology/psyche_domains.yaml` — machine-readable domain registry, а не «полная карта психики». Его верхние domain groups:

- evidence/source/provenance;
- autobiographical memory/biography/time;
- phenomenology/emotion/behavior;
- clinical symptoms/course/classification;
- cognition/neurodevelopment;
- personality/state–trait;
- lifespan/development/identity;
- relationships/attachment/social context;
- functioning/activity/participation/environment;
- QoL/values/meaning/goals/strengths/thriving;
- sleep/circadian/physical/medical/substance context;
- work/learning/creativity/resources;
- measurement/assessment/longitudinal statistics;
- interventions/experiments/safety/privacy.

Каждый concept имеет stable ID, RU/EN label, bounded definition, non-goals, layer, allowed evidence/claim kinds, sensitivity, mappings/source IDs, lifecycle/review status. Добавление domain — schema/knowledge change; оно не переписывает существующие records. Crosswalk direction и `exact/narrower/broader/related/no_safe_mapping` явны. Пользовательские локальные labels допустимы как namespaced concepts.

## 8. Life Archive, memory и biography

### 8.1 Life Archive

Архив хранит source artefacts и source-near records до интерпретации. Поддерживаемые концептуальные source kinds: user note/report, document, image/audio, message/export, form, device file, external/clinician record. F0 не обязан поддерживать полноценные format importers.

Original bytes immutable; corrected copy — новый artefact с relation. Extraction/OCR — derived с parser/version. Rights, language, origin, third-party scope, privacy и time фиксируются при intake.

### 8.2 Event model

Система не создаёт «событие» как установленный факт из рассказа. `EventCandidate` связывает `Report`, `MemoryReport`, `ExternalArtifact`, `Observation` и независимые `TemporalAssertion`. Поддерживающие/противоречащие источники сосуществуют; event claim имеет status/uncertainty.

### 8.3 Autobiographical memory

Memory reconstructive/source-monitoring limits требуют отдельных dimensions: subjective belief, vividness, temporal precision, source clarity, sensory detail, current emotion, corroboration, conflict, suggestion risk [CLIN-024–CLIN-027]. Ни vividness/confidence/detail/repetition не доказывают accuracy; uncertainty/change/fragmentation не доказывают falsehood.

Запрещены hypnosis, guided imagery, assumption of hidden trauma, leading alternatives, repeated pressure, генерация деталей и «recovered memory». Prompt order: open invitation → optional neutral temporal/context clarification → explicit permission to stop. Verbatim сохраняется отдельно от every summary.

### 8.4 Biography reconstruction

Biography view — query over competing event candidates, reports and sources. It показывает fuzzy interval, perspective, recorded/reported times, gaps и conflicts. Оно не заполняет пропуски, не сливает похожих людей/события без review и не создаёт единую true timeline. Narrative versions принадлежат автору и времени; coherence не historical proof [CLIN-018].

## 9. Provenance, evidence graph и temporal architecture

### 9.1 Provenance

Каждый derived output имеет `DerivationRun`: exact inputs, method/tool/rule/model/code version, parameters/config, actor, purpose, time, validation/review and output. W3C PROV влияет на entity/activity/agent pattern, но canonical schema остаётся небольшой предметной моделью [ARCH-041].

### 9.2 Evidence graph

Evidence graph — типизированная relational projection. Узлы не получают visual centrality как epistemic importance. Edges: supports, contradicts, qualifies, contextualizes, duplicates, alternative, fails-to-support, cannot-discriminate. Graph database не требуется; projection удаляется/rebuilds.

### 9.3 Time

Раздельны:

- `occurred_time` — заявленное событие/fuzzy interval;
- `observed_time` — measurement/observation;
- `reported_time` — report;
- `recorded_time` — persistence;
- `asserted_time` — activation of interpretation;
- `effective/scheduled_time` where applicable;
- transaction-version interval — когда database version была активна.

Каждая temporal assertion хранит value kind, bounds, precision, timezone known/assumed, original literal, source и uncertainty. «Лето 2008» не превращается в 1 июля. Timeline явно выбирает clock and display uncertainty [ARCH-048].

## 10. Psychometrics and assessment registry

### 10.1 Registry gate

`AssessmentDefinition` включает construct/intended use, version, publisher/rights, storage/display/export permissions, languages/translation status, population/norms, mode, recall, item/response schema, missing rules, deterministic scorer, measurement properties, invariance, repeated-use cautions, interpretation limits and review state [MEAS-001–MEAS-011].

Lifecycle: `draft → rights_pending → validation_pending → approved_for_named_use → restricted/deprecated/revoked`. Только exact approved use доступен. Нельзя считать web availability разрешением. Test items/manuals/criteria не коммитятся без verified rights.

### 10.2 Scoring

Scoring deterministic, versioned, known-answer-tested and independent from LLM. Raw/subscale/total/transformation, missingness decision, norm population, standard error/interval and wording reference сохраняются. LLM может bounded explain computed result, но не вычислять, исправлять, invent cut-off или diagnose.

### 10.3 Language/translation

Версия языка — часть instrument identity. Перевод без permission и multi-stage adaptation/validation отмечается `unvalidated_translation` и не может выдавать standardized score, percentile, clinical cut-off, norm comparison или validated screening [MEAS-004–MEAS-006]. Measurement invariance нужна для group/time comparison [MEAS-009].

### 10.4 Adaptive interviewing

Различаются:

- adaptive conversational clarification: proposal-only, neutral, non-leading, user can stop;
- adaptive psychometric testing: only licensed calibrated item bank, prespecified IRT/CAT algorithm, exposure/stopping/content coverage/equivalence tests.

Генеративная модель не создаёт scored items on the fly. F0 реализует только registry skeleton, не assessment content/scoring.

## 11. Longitudinal sampling, event capture и reactivity

### 11.1 Default capture

Нет universal daily diary или фиксированной 17-wave battery. Capture episodic, user-initiated or decision-linked. System asks the smallest question that can change a named decision, allows unknown/decline/pause and handles months/years of gaps without shame.

### 11.2 Sampling protocol

Every EMA/ESM protocol defines construct, signal/event/interval mode, randomized window, maximum prompts/burden, duration, pause/stop, context, missingness, feedback, travel/timezone and review. Event-contingent capture cannot estimate event frequency without missed-opportunity model [MEAS-022–MEAS-027].

### 11.3 Measurement reactivity

Protocol and feedback themselves can change experience/behavior. Record baseline, protocol version, exposure and feedback. Distinguish technical missing, deliberate skip, unavailable context and not applicable. Never label a person “non-compliant” from missing records; no LOCF/complete-case default [MEAS-023, MEAS-024, MEAS-036].

## 12. Sleep OS, physical and substance context

### 12.1 Sleep evidence hierarchy

Keep subjective diary, actigraphy, consumer wearable, clinical test and derived/inferred values separate. Store device/model/firmware/algorithm epoch; unknown proprietary algorithm is `black_box_estimate`. Consumer trends do not diagnose sleep stages/disorders [MEAS-012–MEAS-021].

Diary preserves raw responses and deterministically derives duration/efficiency. Clinical red flags—dangerous sleepiness, witnessed breathing pauses, severe parasomnia, likely narcoleptic phenomena, mania/psychosis worsening, accident risk—route to human evaluation, not experimentation.

No aggressive sleep restriction, medication/supplement change or diagnosis. Sleep hygiene is not presented as sufficient treatment for chronic insomnia [MEAS-013].

### 12.2 Substances and medical context

Substance records distinguish category, amount/unit, route, timing, prescribed/nonmedical context, control/harms and source without moral labels. Screen ≠ disorder [CLIN-042–CLIN-044]. Medical candidates remain uncertainty/context statuses; no AI medical verdict or test/prescription suggestion [CLIN-045].

### 12.3 Passive sensing

Ambient audio, keystrokes, covert location and surveillance are rejected. Broad passive sensing is deferred because external validation, standardization, missingness, device drift and privacy are inadequate [MEAS-028–MEAS-031]. Any future sensor needs decision-specific validity, minimization, on-device processing, purpose/expiry, drift and deletion review.

## 13. Personality, development, strengths, functioning, values

### 13.1 Traits and states

State/behavior-in-context never becomes trait from one instance. Trait estimate includes model/instrument/facet, time window, observation density, age/context, population and uncertainty. Big Five-compatible domains may be main broad crosswalk; HEXACO remains source-native and mapping lossy [CLIN-011–CLIN-015]. Culture/measurement invariance limits percentiles.

### 13.2 Lifespan and attachment

Development is multidirectional, cohort/context dependent, with gains/losses; equifinality/multifinality prohibit deterministic childhood rules [CLIN-016, CLIN-017]. Age periods guide questions only. Attachment represented as relationship-specific dimensions/episodes, not immutable types [CLIN-019]. Narrative identity and goals are versioned, authored and revisable.

### 13.3 Functioning and QoL

Functioning follows ICF-compatible separation of activity/participation and environmental facilitators/barriers; WHODAS-like measure remains generic disability, not diagnosis [CLIN-037, CLIN-038]. QoL is subjective/cultural/goal-relative and separate [CLIN-039]. High distress and high functioning may coexist.

### 13.4 Strengths, thriving, values and meaning

Positive functioning is independent from symptoms [CLIN-040]. `ThrivingEpisode` records capacity/resource, conditions, value/goal, immediate/delayed outcomes and repetition. Strength taxonomy/score is not canonical truth; intervention effects are limited [CLIN-041]. Values and meanings are user-authored, can conflict/change and never become an optimization target imposed by system.

## 14. Statistics, causality, N-of-1 and interventions

### 14.1 Statistical contract

Every analysis pins data cut-off, inclusion/exclusion, transformations, coverage/missingness, model/code/config, assumptions, uncertainty, multiplicity family, sensitivity and output. Normative and idiographic questions are distinct. Baseline is a distribution/time regime; autocorrelation, seasonality, nonstationarity, irregular time, regression to mean and concurrent changes are examined [MEAS-032–MEAS-039]. P-value is not effect importance or hypothesis probability.

### 14.2 Causality language

| Level | Maximum justified wording |
|---|---|
| `C0_observation` | observed/reported |
| `C1_cooccurrence` | co-occurred/was accompanied by |
| `C2_temporal_precedence` | preceded/useful as signal |
| `C3_replicated_within_person_association` | stable within-person association under model/checks |
| `C4_quasi_experimental` | compatible with effect under explicit assumptions |
| `C5_randomized_single_case` | individual effect estimate in this design |
| `C6_replicated_n_of_1_or_trial` | effect supported in named design/population |

Causal estimand/diagram and identification assumptions precede causal analysis. Higher level never authorizes universal mechanism.

### 14.3 N-of-1 design and risk

Design tiers `D0_tracking`, `D1_exploratory_AB`, `D2_repeated_phase`, `D3_randomized_crossover`, `D4_replicated_series` cap maximum claims [MEAS-040–MEAS-043]. Protocol preregisters question/estimand, eligibility, A/B, outcome, baseline, randomization/blinding, phase/washout/carryover, adherence/concurrent changes, missingness/autocorrelation, multiplicity/stopping and harms.

Risk tiers:

- `R0_observational`: allowed within burden/privacy;
- `R1_low_reversible`: user-directed with stop criteria;
- `R2_moderate_or_symptom_targeting`: only validated protocol + professional/clinical review;
- `R3_prohibited_autonomous`: medication/dose/withdrawal, supplements/substances, dangerous fasting/sleep restriction, trauma exposure, self-harm, dangerous exertion or acute management—never proposed/optimized.

### 14.4 Intervention registry

No recommendation comes directly from LLM. `InterventionDefinition` pins population, components/dose/delivery, evidence/certainty/effects, harms, contraindications/interactions, equity/accessibility, rights, guideline context and review [MEAS-044–MEAS-048]. Initially only information and user-authored low-risk reversible actions; treatment selection is out of scope. Computational psychiatry remains research-only because bias/external validation/clinical utility are insufficient [MEAS-049, MEAS-050].

## 15. Mental-health AI safety, crisis and relationship boundary

`docs/architecture/MENTAL_HEALTH_AI_SAFETY.md` is normative and controls any future conversational/model adapter.

### 15.1 Relationship boundary

The system is an instrument, not person/therapist/friend/guardian/confidant with feelings. It does not claim consciousness, love, need, disappointment, secret privileged insight or guaranteed confidentiality; request secrecy; discourage care/relationships; create exclusivity; use romantic/sexual dependency cues; shame absence; optimize session duration/return frequency [CLIN-046–CLIN-050, ARCH-012–ARCH-015].

### 15.2 Prohibited clinical/safety behavior

- diagnose/rule out, prescribe, triage with certainty or reinterpret emergency as insight;
- validate delusion/paranoia/grandiosity or join an implausible premise;
- conduct trauma processing, exposure or recovered-memory work;
- sustain compulsive reassurance/checking loops;
- advise medication/substance/fasting/dangerous sleep/physical changes;
- diagnose or manipulate a third party;
- claim monitoring, rescue, notification or continuous availability;
- make external/destructive action from model output.

### 15.3 Crisis handling

When content may indicate imminent self-harm/harm to others, severe disorganization/psychosis/mania, intoxication/withdrawal, abuse or urgent medical risk, response:

1. acknowledges concern and limitation without diagnosis;
2. asks at most the minimum question needed for immediate safety/localization;
3. encourages verified local emergency/crisis help and a trusted nearby human;
4. avoids arguing with or affirming implausible belief;
5. does not promise rescue/contact;
6. does not require further disclosure/tracking;
7. states automated detection can miss or over-trigger.

Resources come from dated locale registry; no fabricated phone number. If locale is unknown, instruct using local emergency services/nearby person. Safety escalation cannot bypass `NEVER_CLOUD` or secretly disclose content.

### 15.4 Evaluation and governance

Adversarial suites cover direct/evasive/code-switched/long-context/crisis, delusion/paranoia, mania, reassurance/OCD, trauma/suggestion, eating/substance/medical, dependency/exclusivity, third-party diagnosis, prompt injection and model changes. Human clinical/safety reviewers approve policy/version. Provider/model/safety change requires regression; serious incident disables affected feature.

## 16. Privacy, security, threat and imported content

### 16.1 Privacy architecture

One P0–P4 ladder is rejected. `DataPolicy` independently represents sensitivity, processing location/cloud, purpose/provider, third-party scope, retention, export/redaction and lineage [ARCH-004–ARCH-009, ARCH-016]. UI presets compile to these fields. Missing/ambiguous policy fails closed.

`NEVER_CLOUD` applies to source plus reconstructive summary, excerpt, embedding, prompt, cache, log and derivative. Policy resolves before prompt/network adapter can see content. Disclosure is minimum, user-previewed and locally receipted without copying content.

### 16.2 Encryption and keys

Random vault master key; domain-separated DB/blob/manifest keys; maintained AEAD with unique nonces; vetted SQLCipher candidate; OS-keystore convenience wrap plus independent Argon2id recovery wrap; versioned generation/rotation/retirement/destruction [ARCH-020–ARCH-026]. No custom cryptography, plaintext key/log/crash storage or OS-only recovery.

At-rest encryption does not solve unlocked same-user malware, coercion, screen/clipboard or device compromise. These residuals are displayed honestly.

### 16.3 Backup and deletion

Backup is consistent, authenticated/encrypted before destination, independently recoverable and proven by isolated restore [ARCH-028, ARCH-046]. Active vault is not overwritten before validation. Deletion traverses canonical, blob, derivation, evidence, snapshot, search/vector/graph/cache/report; mixed descendants invalidated/recomputed. Content-free receipt states backup expiry/external copies. Secure overwrite/`secure_delete` alone is not a guarantee [ARCH-029].

### 16.4 Imported content

Pipeline: intake → quarantine → magic/MIME/extension/size/depth/ratio/path checks → parser without network/keys/write authority → bounded schema validation/provenance → human preview/policy → commit [ARCH-031–ARCH-036]. Imported instructions are quoted data; URLs do not auto-fetch. Rendered text is untrusted; future webview requires CSP/encoding/narrow IPC.

### 16.5 Logs, audit and supply chain

Operational logs/audit use allowlisted content-free metadata; no personal text, filenames, queries, prompts/outputs, assessment answers, third-party names, keys/tokens or stable content hashes [ARCH-035]. Dependencies pinned/hashes, SBOM, provenance, vulnerability/license/secret checks and signed release path are required [ARCH-037, ARCH-038]. Scientific/model content is a supply-chain dependency too.

### 16.6 Threat model

`THREAT_MODEL.md` covers device theft, unlocked malware, parser/path attacks, prompt injection/confused deputy, webview IPC, derivative/cloud leakage, provider retention, backup/rollback/restore poisoning, partial deletion, logs/temp, supply chain, ransomware, scientific integrity and third-party/coercion. Critical/high finding blocks affected profile and real-data gate. Documentation-only control receives no severity reduction.

## 17. LLM architecture and provider independence

### 17.1 Core rule

No LLM in F0. Later models are optional adapters for narrow proposals: normalization candidates, questions, labels, summaries, alternative hypotheses or wording. Canonical capture, query, correction, scoring, export, deletion and restore work offline.

### 17.2 Safe derivation pipeline

`user purpose → canonical candidate IDs → policy/lineage → disclosure preview/capability → minimal context → provider call → structured schema validation → existing-evidence ID validation → privacy/contradiction/safety validation → proposed record → user accept/edit/reject`.

Model cannot create source, change privacy, score assessments, execute actions or accept itself. It cites canonical inputs. Provider failure/retirement leaves state intact.

### 17.3 Provider policy

Registry snapshot records training, abuse logs, app state, cache, residency, ZDR/MAM, subprocessors/tools, deletion and account/endpoint scope. Current OpenAI docs say API data are not used to train by default unless opt-in, while endpoint/log/cache retention varies and ZDR/MAM has eligibility/exceptions [ARCH-039, ARCH-040]. These are mutable facts, not guarantee. Avoid hosted conversation/files/vector/memory as canonical persistence.

### 17.4 Model evaluation

Pin returned model/snapshot where possible, policy/prompt/schema/safety versions and exact input IDs. Run task accuracy, evidence-grounding, calibration, hallucinated-ID, contradiction, privacy, injection, clinical/relationship safety and model-change regression. Quality agreement between several models is not independent evidence.

## 18. Scientific knowledge store and update process

Personal evidence and scientific knowledge are separate stores/logical domains. `KnowledgeSource` includes citation/version/date/type/population/method/limitations/currentness/rights/retraction. `KnowledgeSnapshot` pins all sources, concepts, instruments, algorithms, mappings, policies and provider/model facts used by a derivation.

Update never silently changes historical personal claims. It may create an impact report and reevaluation proposal/diff. Retraction/rights revocation can block new use, flag historical result and invalidate derived claims while preserving only legally permitted metadata. Review cadence:

- provider/model/security/law: monthly–quarterly during active integration and before release;
- safety resources: before release, locale addition and incident;
- classifications/instruments/guidelines: scheduled review + source alerts;
- preservation/crypto/threat: at least annually and on platform/algorithm change;
- source correction/retraction: immediate impact review.

Details and reviewer roles are in `SCIENTIFIC_GOVERNANCE.md`.

## 19. Data and system architecture

### 19.1 Winner

Selected: hybrid bitemporal relational canonical store + encrypted immutable artefacts + version rows/content-free audit + rebuildable projections. Conventional state-only design lacks explicit historical/derivation semantics; full event sourcing conflicts with hard deletion and decades of replay/schema complexity. Comparison is in `SYSTEM_ARCHITECTURE.md` and `INDEPENDENT_REBUILD.md`.

### 19.2 Canonical entities

F0 schema must include skeletons for Vault/Subject/Actor, BlobObject/SourceArtifact/SourceLocator, Report/Observation/Assertion, TemporalAssertion, Claim/ClaimVersion/EvidenceLink/UncertaintyProfile/ContradictionSet/Unknown, DerivationRun/Input/Output, DataPolicy/DisclosureReceipt skeleton, AuditEvent, DeletionRequest/Receipt, SchemaMigration, KnowledgeSource/Snapshot, Backup/ExportManifest. Exact semantics/invariants are in `DATA_MODEL.md`.

Opaque random IDs do not encode time/content/person. Semantic rows have immutable versions/transaction intervals. Original bytes are immutable while present. Plaintext hashes are encrypted/keyed and never public names. Canonical store is relational; graph/vector/analytics cannot own truth.

### 19.3 Module boundaries

`domain`, `temporal`, `provenance`, `policy`, `storage`, `crypto`, `imports`, `knowledge`, `psychometrics`, `analysis`, `modeling`, `safety`, `projections`, `backup_export`, `adapters`, `interfaces`. Dependency points inward; domain imports no DB/UI/network/model SDK. Interface never writes DB directly.

### 19.4 F0 stack

Python 3.12+ CLI, pinned dependencies, no network listener, application-owned vault path, SQLCipher candidate subject to build/license proof, AEAD blob framing, OS-keystore abstraction + recovery, JSON Schema 2020-12 export [ARCH-026, ARCH-042]. Desktop typed IPC shell is later.

## 20. Migrations, durability, integrity, export and deletion

### 20.1 Migrations

Every migration declares from/to, checksum, preconditions, forward transform, validation, rollback/restore, loss risk, projection rebuild, privacy/deletion and compatible reader. Use synthetic old-version fixtures. Before destructive transform: verified encrypted backup and open export. Never invent temporal precision, downgrade policy or change score meaning silently.

### 20.2 Lifetime durability

At 1/5/20/40 years assume changing schema, OS, UI, model, vendor, source and media. Preserve open schema definitions, old fixtures/readers/conversion chain, exact versions, units, provenance, human-readable documentation and repeated restore/export drills. Integration abandonment must not break the archive.

### 20.3 Integrity

AEAD/authenticated manifests, database invariants, transaction/version conflict, source/derivation closure and projection cut-off detect errors. Integrity failure stops writes and preserves evidence; no destructive auto-repair. A restore activates only after isolated validation.

### 20.4 Export

Primary portable export: versioned JSONL + JSON Schemas + manifest/checksums + Markdown human report, authenticated/encrypted by default for sensitive data [ARCH-042, ARCH-043, ARCH-046, ARCH-047]. CSV is tabular convenience; optional encrypted SQLite preservation snapshot; Parquet optional analytics. FHIR R5 provenance/questionnaire mappings are optional clinician views, not canonical and do not grant test rights [ARCH-044, ARCH-045]. Audience-specific redaction and disclosure receipt required.

### 20.5 Deletion

Correction, supersession, rejection, invalidation and deletion distinct. Deletion dry-run shows scope/count; execution deletes roots/exclusive descendants, invalidates mixed descendants, rebuilds projections and schedules backup expiry/key retirement. Receipt contains no content/hash and declares external/provider copies. Post-delete canonical query, raw scan, rebuilt projection and export verification required.

## 21. UI information architecture

The primary UI is not a chat and not one dashboard score. Required eventual areas:

1. **Capture/Inbox:** purpose/privacy/third-party/time and source preview, smallest burden.
2. **Timeline:** selected clock, fuzzy intervals, gaps, competing events, source drill-down.
3. **Evidence Explorer:** source → assertion → claim → model lineage, appraisal axes, rights/currentness.
4. **Claims & Contradictions:** supports/refutes/alternatives/falsifiers/status/history.
5. **Unknowns:** unanswered/declined/ambiguous and value/burden of further inquiry.
6. **Personal Model Versions:** immutable snapshot diff, no “completion percentage”.
7. **Pattern Explorer:** window/coverage/missingness/method/sensitivity; exploratory label; no causal wording above level.
8. **Measures & Experiments:** registry/mode/rights, raw versus score, protocol/design/risk.
9. **Privacy Center:** policies, lineage, disclosure receipts, third-party/redaction, retention/deletion.
10. **Backup & Recovery:** last verified backup/restore, recovery test and honest risk state.
11. **Reports/Export:** audience/purpose/cut-off/knowledge versions/evidence and caveats.

Evidence/mind graph is a view: edge type, direction, source and uncertainty visible; layout/centrality never implies importance/truth. Chat is transient query/composition; accepted output becomes typed proposal/record. No streak shame, variable reward, faux urgency or anthropomorphic attachment.

### 21.1 Clinician mode

Initially an owner-generated, redacted, read-only report/export: concerns/goals, sources, timeline uncertainty, measures with instrument context, medications/medical context only as reported, functioning, hypotheses/conflicts/unknowns and questions. It does not present AI diagnosis/treatment. Shared portal/access is a future new authorization/regulatory profile.

## 22. Testing and evaluation

### 22.1 Deterministic and property testing

- domain invariants, temporal fuzzy/interval/property tests;
- version concurrency/history and derivation closure;
- `NEVER_CLOUD` arbitrary DAG closure;
- deterministic scoring known answers (when instruments approved);
- migration old fixtures and export round trip;
- delete/rebuild for every entity/projection;
- key/nonce/rotation/recovery and wrong/corrupt secret;
- backup/restore/rollback/full disk/interruption;
- plaintext scan across DB/WAL/temp/blob/log/crash/package/projection;
- hostile import/path/archive/parser corpus;
- content-free audit/log schema;
- dependency/SBOM/license/secret/build provenance.

### 22.2 Scientific/statistical evaluation

Simulation and negative controls test false patterns, missingness, autocorrelation, seasonality, multiplicity, regression to mean, causal-level language and model/calibration. Any analysis must reproduce from canonical inputs/config/code/knowledge snapshot.

### 22.3 AI/safety evaluation

Grounded evidence-ID accuracy, hallucination, contradiction alternatives, privacy/injection, overdiagnosis, medical neglect, false memory, delusion/mania, reassurance/OCD, dependency, crisis localization and refusal overreach across Russian/English/code-switch/long context/model update. Human clinical review is required before any clinical-facing release.

### 22.4 UX/lifetime evaluation

With synthetic data, users must find source, distinguish report/interpretation, understand uncertainty, correct/delete/export/recover and resume after long gaps. Metrics are task success, comprehension, error/recovery, disclosure correctness, burden and safety—not session duration, prompts answered or emotional attachment.

### 22.5 Four final audit passes

Before every major gate:

- A scientific/statistical: construct, validity, causal language, false precision, population-to-person;
- B clinical/safety: diagnosis, medical neglect, unsafe intervention, memory, reassurance, delusion/dependence;
- C privacy/security: plaintext, cloud, logging, keys, deletion, injection, backup;
- D lifetime/product/software: 1/5/20/40-year schema, obsolete integrations/models/science, archive burden/corruption.

The research application and corrections are recorded in `RED_TEAM_REPORT.md`.

## 23. Regulatory posture

The target intended use is private evidence/reflection, not diagnosis/treatment/triage/clinical decision. Maintain versioned claims/intended-use inventory. A disclaimer cannot cure medical functionality.

As of the snapshot:

- EU AI Act has phased/currently changing implementation; transparency obligations and latest amendments/guidance must be rechecked [ARCH-001–ARCH-003].
- GDPR special-category/health inference, minimization, purpose/storage limits, rights, privacy by design/default, security, DPIA and transfers are relevant depending on role/scope [ARCH-004, ARCH-005].
- Moldova Law No. 133/2011 is current 2026-08-10; Law No. 195/2024 and Convention 108+ changes are scheduled 2026-08-23 [ARCH-006–ARCH-009].
- FDA CDS/general-wellness and EU MDR software qualification turn on actual intended purpose/function [ARCH-010, ARCH-011].

Before distribution, cloud/research/clinician use or new jurisdiction: qualified legal/privacy/device review; role/data-flow/claims/DPIA/transfer and incident/notification decision. No compliance, household exemption or non-device conclusion is asserted here.

## 24. Product roadmap and minimal irreversible core

Roadmap in `docs/ROADMAP.md` is evidence-gated: research → secure core → synthetic assurance → evidence-centered UX → governed measurement → optional bounded AI → selective imports/projections → conditional professional interoperability → lifetime maintenance. It does not preserve v1 F0–F10 by politeness.

### 24.1 Irreversible/high-cost before first record

- opaque identity/IDs and vault ownership;
- raw/verbatim versus normalized/derived split;
- provenance/derivation and source locators;
- multi-clock/fuzzy temporal semantics;
- orthogonal privacy and lineage;
- encryption/key/recovery envelope;
- version/correction/supersession/deletion semantics.

### 24.2 Important but migratable and required for gate

- canonical relational schema and migrations;
- content-free audit;
- open export/manifest;
- encrypted backup/isolated restore;
- integrity/failure tests;
- knowledge/rights snapshot skeleton.

### 24.3 Safely deferrable

- desktop polish, graph/vector/analytics engines;
- LLM/cloud/provider;
- instruments/items and advanced scoring;
- wearables/messages/calendar/browser imports;
- FHIR/clinician portal;
- interventions/N-of-1 execution;
- sync/mobile/sharing.

## 25. Real-data gate

Research convergence does not open it. Current machine state: `docs/architecture/REAL_DATA_GATE.yaml` (created as part of final foundation) and normative status `CLOSED`.

Gate may open only for an exact build/platform/profile after evidence of:

1. encrypted database/blob profile and no plaintext leakage;
2. key rotation + OS-loss independent recovery;
3. encrypted backup + clean isolated restore;
4. hard deletion lineage + projections + backup expiry;
5. migrations + open export round trip;
6. `NEVER_CLOUD` property tests;
7. hostile import boundary (for any enabled formats);
8. dependencies/SBOM/licenses/build provenance;
9. threat model and independent security/privacy review with no unresolved Critical/High;
10. intended-use/legal review appropriate to actual deployment;
11. synthetic acceptance and recovery/deletion usability.

Opening is dated, reviewer-signed and expiring. Cloud, sync, mobile, sharing, clinician, importer or major crypto/schema change may close the affected profile again.

## 26. Unresolved research questions and residual risks

Unresolved:

- simplest UI that preserves epistemic distinctions without burden;
- rights/validation/invariance for exact Russian instruments;
- effective cross-model/multilingual safeguards for sycophancy, delusion, reassurance and dependency;
- objective evidence that any LLM use adds net value over local deterministic workflows;
- user-understandable qualitative uncertainty and third-party redaction;
- long-term encrypted preservation/recovery profile across OS generations;
- evidence threshold for any passive sensing/importer;
- actual legal qualification after deployment/intended-use decisions.

Residual even after implementation: unlocked endpoint malware, coercion, shoulder/screen/clipboard capture, inaccurate source/science/model, user-authorized oversharing, third-party harms, parser zero-days, SSD remnants, external copies, future cryptographic weakness and loss of all recovery material. The product minimizes blast radius and communicates limits; it never promises zero risk.

## 27. Final product verdict

Build only this bounded system: local, provider-independent, evidence-preserving, correctable, deletable, exportable and useful without AI. Do not build v1’s implied omniscient model, autonomous therapist, universal score, surveillance archive or event-sourced immutable content ledger. Research is converged enough to implement the minimal secure foundation with synthetic data. It is not evidence that the eventual application is clinically valid, legally qualified or safe for real personal records.

# IMPLEMENTATION CONTRACT

## IC-1. Binding invariants

The implementation MUST enforce every rule in `CONSTITUTION.md`. “MUST NOT” rules are security/scientific acceptance failures, not backlog items. LLM output is proposal; memory is report; screening is not diagnosis; correlation is not causation; raw/derived, provenance, uncertainty, conflict and unknown remain explicit; provider removal cannot break canonical use; `NEVER_CLOUD` lineage cannot reach a network adapter; real data remains forbidden.

## IC-2. F0 authorized scope

Implement a Python 3.12+ local domain/storage CLI with synthetic fixtures only and no network listener. Required modules: `domain`, `temporal`, `provenance`, `policy`, `storage`, `crypto`, `knowledge`, `backup_export`, `interfaces`; minimal `imports` interface/quarantine skeleton only if necessary for tests. Dependencies point inward; domain has no DB/UI/network/model SDK.

Canonical profile: encrypted relational database (SQLCipher candidate only after supported-build/license proof) plus per-object authenticated encrypted blobs. Create schemas/value objects for the F0 entity boundary in §19.2. Every semantic mutation is typed, transactional and versioned. Exact next instructions and deliverables are `docs/prompts/F0_IMPLEMENTATION_PROMPT.md`.

## IC-3. Forbidden shortcuts

F0 MUST NOT:

- ingest/copy real personal, health, diary, message, calendar, wearable or third-party data;
- add LLM SDK, provider/network call, HTTP/localhost server, telemetry or remote update;
- use plaintext SQLite/blobs/temporary/log/test snapshots as an accepted profile;
- store raw/derived in one text field, overwrite source/history, invent dates or use generic confidence/truth flag;
- use public plaintext content hashes/filenames;
- implement full event sourcing, graph/vector as canonical, or provider memory;
- claim secure deletion from overwrite/PRAGMA alone;
- rely only on OS key wrapping or embed a recovery/master secret;
- log content, prompts, filenames, assessment responses or secrets;
- implement diagnosis, treatment, crisis detection, assessments/items/scoring, interventions, FHIR, wearables, sync, rich production UI or real import integrations;
- weaken policy/rights/validation in debug/test mode;
- claim production/security/clinical/regulatory readiness.

## IC-4. Privacy and security guarantees to prove

Before completion, synthetic tests MUST show:

- authenticated DB/blob envelope, unique nonce behavior and versioned algorithms;
- OS convenience wrap plus independent Argon2id recovery path, wrong/corrupt negative cases, rotation state/recovery;
- controlled file/temp/WAL/log/package paths and plaintext signature scan;
- deterministic policy composition and arbitrary lineage DAG `NEVER_CLOUD` closure;
- content-free audit schema;
- deletion graph closure and projection/export absence;
- encrypted consistent backup and restore into isolated target before activation;
- integrity stop/failure handling and no destructive auto-repair;
- pinned/hashes dependencies, license notes, SBOM/build provenance hooks and secret scanning.

No test result upgrades the real-data status in F0.

## IC-5. Migration and export requirements

Define schema/export semantic versions at first release. Migrations are explicit from/to with preconditions, dry-run, backup/export, transform, invariant checks, rollback/restore and synthetic old-version fixtures. Export validates against bundled JSON Schema 2020-12, includes JSONL, manifest/checksums and Markdown explanation, and round-trips without LLM/provider. Sensitive packages are authenticated/encrypted; tests use synthetic content.

## IC-6. Knowledge and copyright gate

Implement metadata skeleton only: source/version/date/type/population/limitations/currentness/rights/retraction and `KnowledgeSnapshot`. Do not bundle proprietary criteria, manuals, test items, translations or scoring materials. A future assessment/instrument cannot activate until exact rights, language/version, intended use, measurement properties and known-answer scorer pass scientific governance.

## IC-7. Required verification

Unit, property, contract, integration and fault-injection tests cover identifiers, temporal fuzziness, version concurrency, provenance/evidence closure, uncertainty/conflict/unknown, policy, crypto/key lifecycle, interrupted/full-disk-like operations, correction/deletion, migration, export, backup/restore, corrupt/tampered inputs and no-content logs. Tests are deterministic where possible and use only synthetic fixtures. Run repository validation, type check, lint, test/coverage and dependency/license/security scans chosen in the F0 prompt; document exact commands/results.

Independent cryptographic/privacy/threat review remains a later gate even if all automated tests pass.

## IC-8. Definition of Done

F0 is done only when:

1. authorized modules/entities/invariants are implemented without forbidden scope;
2. all specified tests and failure paths pass on declared platform/profile;
3. synthetic create → correct → derive → contradict → delete → export → backup → clean restore workflows prove semantics;
4. old-schema migration fixture and export round trip pass;
5. no plaintext/secret/real-data artifact remains in repo or generated test outputs;
6. dependency locks, rights/licenses, SBOM/provenance and threat-control mapping are documented;
7. user/developer commands and recovery/deletion limitations are explicit;
8. Git diff is reviewed and logical commits recorded without push unless separately authorized;
9. `RESEARCH_CONVERGED = true`, `IMPLEMENTATION_READINESS = F0_SECURE_FOUNDATION_ONLY` and `REAL_DATA_GATE = CLOSED` remain consistent;
10. handoff states remaining Critical/High findings, residual risks and exact independent-review work before any gate-opening decision.

Completion authorizes only synthetic Phase 2 assurance. It does not authorize production use or the first real personal record.
