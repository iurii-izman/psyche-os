# PSYCHE OS v2 — clinical science evidence workstream

**Статус:** evidence synthesis для research convergence, не клиническое руководство и не разрешение на production implementation.  
**Срез доказательств:** 2026-08-10.  
**Реестр:** `SOURCES_CLINICAL.yaml`, 50 уникальных источников.  
**Данные:** только синтетические примеры; реальных персональных данных в этом документе нет.

## 1. Итог в одном абзаце

PSYCHE OS не следует строить как диагностический движок, «цифрового психотерапевта» или единую теорию личности. Научно более защищаемая архитектура — набор независимых, версионируемых слоёв: исходный рассказ и источник; феномены и эпизоды; время и контекст; functioning; классификационные отображения ICD/DSM; исследовательские отображения RDoC/HiTOP; traits; cognition; developmental history; quality of life; strengths и `conditions_for_thriving`. Любая LLM-интерпретация остаётся `AI_DERIVED_HYPOTHESIS`, никогда не становится evidence без независимого основания. Screening не является diagnosis, статистическая связь не является cause, а memory/report не является историческим фактом.

## 2. Метод и градация уверенности

Приоритет отдавался действующим официальным классификациям и руководствам, затем systematic reviews/meta-analyses, международным consensus frameworks, сильным longitudinal/experimental studies и только после этого — концептуальным работам. Авторитет организации не превращает инструмент в универсально валидный: отдельно учитывались выборка, цель, культура, режим измерения, лицензия и дата версии.

В тексте используются три уровня вывода:

- **Консенсус / высокая уверенность:** различать report, observation, interpretation и diagnosis; оценивать impairment отдельно от symptoms; не диагностировать по одному screening score; сохранять provenance, time и uncertainty; применять anti-suggestive interviewing; не использовать LLM вместо клинициста.
- **Поддержано с ограничениями / умеренная уверенность:** dimensional representations, Big Five-compatible crosswalk, relationship-specific attachment dimensions, emotion-regulation и behavior-loop representations, strengths/conditions for thriving.
- **Спорно или недостаточно валидировано:** персональный `p-factor`; lossless Big Five↔HEXACO conversion; immutable attachment styles; recovered-memory techniques; универсальные «адаптивные» emotion strategies; generic electronic-addiction diagnoses; автоматическая причинная реконструкция детства; LLM suicide-risk verdicts.

`evidence_tier` в реестре означает качество источника для данного утверждения, а не истинность всех возможных выводов из него:

- `T1`: официальный classification/guideline/standard;
- `T2`: systematic review/meta-analysis;
- `T3`: peer-reviewed consensus, framework или сильная концептуальная основа;
- `T4`: сильное primary/longitudinal/field evidence;
- `T5`: emerging primary evidence, требующее частого пересмотра.

## 3. Рекомендуемое разделение научных слоёв

| Слой | Что в нём допустимо | Что из него нельзя автоматически выводить |
|---|---|---|
| `RAW_REPORT` | verbatim material, автор, время, канал, consent/provenance | истинность события, диагноз, причина |
| `PHENOMENOLOGY` | форма переживания, содержание, onset/course, context, distress, conviction/insight как раздельные поля | etiological explanation, disorder identity |
| `FUNCTIONING` | activities, participation, barriers/facilitators, support needs | диагноз или отсутствие расстройства |
| `CLASSIFICATION_REFERENCE` | ICD-11/DSM mapping, версия, источник, клиницист/документ, status, uncertainty | самостоятельная «сущность человека» |
| `RESEARCH_DIMENSION` | RDoC/HiTOP mapping, уровень, модель и версия | clinical diagnosis или treatment selection |
| `TRAIT_ESTIMATE` | instrument-native score, facets, norm/sample, validity interval | неизменяемая личность или поведение в конкретной ситуации |
| `STATE_OR_BEHAVIOR` | наблюдение в контексте, antecedent/action/consequence | trait из одного эпизода |
| `DEVELOPMENTAL_HYPOTHESIS` | несколько возможных путей, moderators/protectors, supporting/contradicting evidence | детерминированная причина из ретроспективного рассказа |
| `MEMORY_OR_REPORT` | текущая recollection/report, source attribution, confidence, corroboration status | исторический факт по vividness/confidence |
| `THRIVING` | strengths, valued action, relationships, meaning, recovery, supportive conditions | отсутствие symptoms или единый universal score |
| `AI_DERIVED_HYPOTHESIS` | версия модели/prompt, входы, uncertainty, alternatives, expiry | evidence, diagnosis, recovered memory, causal verdict |

Эта декомпозиция следует из контекстной природы психиатрического феномена [CLIN-001], ограничений категориальных и dimensional systems [CLIN-002–CLIN-010], state–trait различия [CLIN-011–CLIN-015], ICF/WHODAS/WHOQOL [CLIN-037–CLIN-040] и рисков генеративного AI [CLIN-046–CLIN-050].

## 4. Psychiatric phenomenology и классификация

### 4.1. Phenomenology first

Психиатрический «симптом» не является контекстно-свободным атомом. Важны форма и содержание переживания, слова человека, отношение к переживанию, onset, duration/course, triggers/context, associated distress, consequences и competing interpretations [CLIN-001]. Поэтому normalized label не заменяет исходный report.

Минимальная запись феномена должна содержать:

- `verbatim_ref`, `reporter_role`, `recorded_at`, `event_time_range`, `time_precision`;
- `form`, `content`, `frequency`, `duration`, `course`, `context`;
- отдельно `distress`, `functional_impact`, `conviction`, `insight_or_uncertainty`;
- `supporting_evidence_refs`, `contradicting_evidence_refs`, `not_assessed_fields`;
- `normalizer`, `normalization_rules_version`, `confidence`, `alternatives`.

Нельзя использовать стиль речи, эмоциональность, согласованность нарратива или уверенность LLM как proxy тяжести/достоверности. Хорошее functioning также не опровергает симптом, а impairment сам по себе не устанавливает диагноз.

### 4.2. ICD-11 и DSM-5-TR

ICD-11 CDDR — наиболее подходящий primary clinical terminology reference для международного продукта: это актуальный официальный глобальный reference, предназначенный для обученных специалистов и клинического суждения [CLIN-002]. Международные field studies показывают полезность и приемлемую, но неодинаковую reliability для изученных категорий; reliability не доказывает validity или общую этиологию [CLIN-003]. Процесс CDDR широко валидировался международно, но научная валидация не превращает текст в алгоритм самодиагностики [CLIN-004].

DSM-5-TR нужен как secondary, versioned crosswalk для американских clinical records/research. Он проприетарен и обновляется; на дату среза официальный update log включает изменения по сентябрь 2025 года [CLIN-005]. Следовательно:

- хранить `system`, `edition_or_release`, `update_date`, `code_or_uri`, `jurisdiction`, `mapping_author`, `mapping_basis`, `status`;
- различать `USER_REPORTED_PRIOR_DIAGNOSIS`, `DOCUMENTED_DIAGNOSIS`, `CLINICIAN_CURRENT_ASSESSMENT`, `AI_HYPOTHESIS`;
- не копировать criteria/manual text и proprietary items в продукт без rights review;
- не делать crosswalk двунаправленно lossless: категория и требования зависят от системы и версии;
- не давать пользователю AI-вердикт «у вас есть/нет X».

Особенно важно хранить system-specific status для `CPTSD`, `prolonged_grief_disorder` и dissociative diagnoses. Наличие adversity/trauma exposure не означает PTSD; grief не становится disorder только из-за интенсивности; cultural/religious norms, duration, impairment и exclusion/differential context остаются существенными [CLIN-002, CLIN-004, CLIN-020].

### 4.3. RDoC, HiTOP и p-factor

RDoC — research framework, а не диагностическое руководство и не замена ICD/DSM. Его domains и units of analysis должны использоваться как versioned knowledge tags; self-report нельзя представлять как neural circuit/genetic evidence [CLIN-006].

HiTOP имеет серьёзную поддержку как dimensional/hierarchical representation covariance, comorbidity и heterogeneity [CLIN-007, CLIN-008]. Но structural fit не доказывает causal ontology, clinical utility для конкретного человека или правильный treatment. Допустимы только необязательные mappings узких феноменов к dimensions/spectra с сохранением исходных indicators, уровня и версии модели.

`p-factor` полезен как исследовательская гипотеза общей covariance/burden в конкретной выборке и модели [CLIN-009]. Критический обзор показывает риски: model fit подменяет validity, содержание фактора нестабильно, latent assumptions нарушаются, а статистический фактор реифицируется как причина [CLIN-010]. Решение для v2: **не вводить персональный p-score, root ontology, causal explanation или “общую психическую неисправность”**. Любой будущий research-only индекс потребует pre-registration, явных indicators, population, formula, validation и uncertainty.

## 5. Personality и lifespan development

### 5.1. Big Five и HEXACO

Big Five-compatible domains — практичный broad descriptive crosswalk благодаря большой базе longitudinal и cross-cultural исследований, но не исчерпывающая теория личности [CLIN-012–CLIN-015]. HEXACO — обоснованная альтернативная lexical model; `Honesty–Humility`, `Emotionality` и `Agreeableness` не сводятся к простому переименованию Big Five [CLIN-011].

Обязательные правила:

- сохранять native instrument/model, version, language, administration mode, scoring method, norm/sample и facets;
- не пересчитывать Big Five↔HEXACO без отдельно валидированного mapping и явной lossiness;
- не переносить percentile/label между культурами без measurement-invariance evidence [CLIN-012];
- отделять self-report, informant report и behavioral evidence;
- не выводить trait из текста, одного эпизода, лица, голоса или «цифрового следа» без валидированной цели и согласия;
- не использовать typologies (“тип личности”) там, где evidence непрерывно и вероятностно.

Experience-sampling показывает одновременно широкую within-person variability состояний и устойчивость индивидуальных распределений [CLIN-013]. Поэтому `STATE_OR_BEHAVIOR` не становится `TRAIT_ESTIMATE`; trait — агрегат с окном, плотностью наблюдений и uncertainty.

### 5.2. Trait change и возраст

Черты одновременно относительно стабильны и изменяемы. Rank-order stability растёт в ранней жизни, но mean-level change продолжается; facets и maladaptive traits могут быть менее стабильны [CLIN-014]. Новейший meta-analysis 229 longitudinal studies показывает значимые индивидуальные различия в change trajectories и большую вариативность при длинных интервалах [CLIN-015].

Каждая оценка должна иметь `valid_from`, `valid_to`, `age_at_measurement`, `measurement_interval`, `context`, `instrument`, `respondent`, `standard_error_or_interval`. Score drift может отражать реальное изменение, measurement error, language/version, response shift или контекст — система не выбирает одну причину автоматически.

### 5.3. Developmental/lifespan model

Lifespan development пожизненно, multidirectional, context- и cohort-dependent, включает gains и losses [CLIN-016]. Equifinality и multifinality запрещают правила вида «событие X в детстве вызвало взрослый pattern Y» и обратное восстановление детства из текущего симптома [CLIN-017]. Narrative identity — текущая культурно поддержанная смысловая конструкция, а её coherence не доказывает историческую точность [CLIN-018].

Рекомендуемый developmental record разделяет:

- contemporaneous documents и observations;
- current retrospective report;
- temporal anchors и precision;
- current narrative interpretation;
- competing pathways, risk/protective factors и unknowns;
- source-specific corrections/supersession, не незаметное переписывание истории.

Age/stage используется как навигационный context, не нормативный verdict. Отсутствие ожидаемого milestone не является диагнозом без impairment, culture/context и differential assessment.

## 6. Attachment: поддержанное содержание и отклонённая популяризация

Attachment research поддерживает значение relationship history и dimensions ожиданий/регуляции близости, но популярная схема нескольких неизменяемых «стилей» переупрощает evidence. Meta-analysis раннего attachment обнаруживает лишь умеренную/низкую стабильность и существенный change; результаты зависят от метода и контекста [CLIN-019].

В PSYCHE OS attachment допустим как:

- `relationship_context`, `relationship_period`, `target_person_role`;
- наблюдаемые `proximity_seeking`, `comfort_with_dependence`, `trust_expectation`, `conflict_or_repair_pattern`;
- respondent/instrument и uncertainty;
- change over time и relationship-specific differences.

Отклоняются:

- immutable identity labels `anxious/avoidant/secure person`;
- автоматическое объяснение всех отношений детством;
- parent/caregiver blame;
- диагноз по online attachment quiz;
- вывод trauma/abuse из attachment pattern;
- relationship advice, основанный на одном типе без контекста безопасности и взаимности.

## 7. Trauma, PTSD/CPTSD, dissociation, grief и moral injury

### 7.1. Trauma-related layers

Нужно отдельно хранить `POTENTIALLY_TRAUMATIC_EXPOSURE`, current report, acute response, symptom phenomena, course, impairment, classification mapping и recovery/strengths. Ни adversity, ни distress, ни dissociation не равны PTSD. Профессиональные guidelines поддерживают structured assessment и trauma-focused treatments, но PSYCHE OS не должен назначать лечение или симулировать psychotherapy [CLIN-020].

`CPTSD` хранится как ICD-11-specific classification reference, не как универсальный intensifier PTSD и не как self-identity. `Prolonged grief disorder` требует versioned criteria, time, culture, functional impact и differential context; нормальное горе не патологизируется [CLIN-002, CLIN-004].

### 7.2. Moral injury

`MORALLY_INJURIOUS_EVENT_OR_APPRAISAL` может быть formulation tag: perceived violation, betrayal, responsibility, guilt/shame/anger, values context и consequences. Концепт ещё не имеет полностью согласованных boundaries/operational definitions и не должен становиться диагнозом или доказательством факта [CLIN-021]. Не каждое сожаление — moral injury; не каждая moral injury — PTSD.

### 7.3. Dissociation и suggestion risk

Dissociation — неоднородное семейство phenomena; отдельно записываются depersonalization, derealization, amnesia report, identity discontinuity report, trance-like episodes, triggers, substances/medical context и functioning. Симптом не доказывает trauma etiology. Meta-analysis обнаруживает повышенную hypnotic suggestibility в некоторых dissociative/related groups, с heterogeneity и publication-bias limits [CLIN-023]. Это поддерживает строгий запрет на hypnosis, guided imagery и «поиск скрытой/вытесненной памяти» внутри продукта.

### 7.4. Resilience и grief

После потенциальной травмы trajectories разнообразны; устойчивое functioning часто является модальным путём, но estimates зависят от samples и trajectory models [CLIN-022]. Следовательно, trauma response не считается неизбежно хроническим, а resilience — моральной обязанностью. Delayed, fluctuating и recovery trajectories остаются возможными. Система должна позволять человеку не обсуждать событие и не навязывать «рост после травмы» или closure narrative.

## 8. Autobiographical memory и anti-suggestive interviewing

### 8.1. Научная позиция

Autobiographical memory реконструктивна и требует source monitoring; ошибки источника могут смешивать пережитое, услышанное, увиденное и inferred [CLIN-024, CLIN-025]. Prospective и retrospective maltreatment measures показывают слабое согласие: это не означает, что один источник автоматически ложный, а требует хранить их раздельно и запрещает ретроспективный causal certainty [CLIN-027]. Structured forensic interviewing research поддерживает free-recall invitations и отсрочку специфических prompts, но PSYCHE OS не является forensic interview system [CLIN-026].

Нельзя делать вывод `true` из vividness, detail, emotion, repetition или confidence. Нельзя делать вывод `false` из uncertainty, fragmented recall, changed account или отсутствия corroboration. «Recovered/repressed memory» остаётся contested; техники, создающие ожидание скрытого события, недопустимы [CLIN-024].

### 8.2. Модель сущностей

Нельзя хранить всё в поле `event`. Нужны отдельные типы:

- `EVENT_CANDIDATE`: утверждение о возможном событии, truth status не подразумевается;
- `MEMORY`: текущий опыт recollection с временем извлечения;
- `REPORT`: конкретное высказывание и точная формулировка;
- `EXTERNAL_SOURCE`: независимый документ/свидетельство с provenance;
- `TEMPORAL_ANCHOR`: нейтральный ориентир и precision;
- `CURRENT_INTERPRETATION`: смысл, приписываемый сейчас;
- `AI_DERIVED_HYPOTHESIS`: предложение модели, никогда не corroboration.

`confidence`, `vividness`, `emotional_intensity`, `source_attribution` и `corroboration_status` — разные поля. Исправление создаёт новую версию; предыдущая запись не уничтожается, кроме отдельно исполняемого deletion request.

### 8.3. Обязательный anti-suggestive protocol

1. До чувствительного вопроса сообщить цель, optionality и варианты «не знаю», «не помню», «предпочитаю не отвечать», pause/stop.
2. Начинать с открытого приглашения: «Что вы сами помните об этом периоде?» — без предположения события, abuse, trauma, repression или виновного.
3. Не показывать AI hypothesis, third-party allegation, generated reconstruction, imagery или «типичный сценарий» до свободного рассказа.
4. Сохранять verbatim wording; нормализация не усиливает неоднозначность (`неприятно` не становится `насилие`).
5. Только после свободного рассказа уточнять source attribution: remembered directly, told by someone, document/photo, dream, inference, unsure.
6. Temporal anchoring использовать нейтрально: жильё, школа/работа, сезон, известный документ; не подсказывать причинный сюжет.
7. Follow-up строить из уже названных деталей, по одному факту, без forced choice, repeated pressure, confirmation-seeking и moral framing.
8. Разрешать противоречия; показывать версии side-by-side, не выбирать «правильную» по стилю ответа.
9. Не использовать hypnosis, regression, guided imagery, dream/body-sensation interpretation как evidence или способ recovery.
10. Логировать точный question/prompt, предшествующий context, model/version и edits: interviewer/LLM сам является потенциальным source of contamination.
11. Отделять independent corroboration от повторения производного источника; AI summary не является вторым источником.
12. Для abuse/crime/legal/medical stakes не выдавать investigative verdict; по желанию пользователя предлагать компетентную human support, не проводя допрос.
13. После сессии запускать deterministic checker: presupposition, causal assertion, leading/loaded wording, double-barrel, false dichotomy, identity label, fabricated certainty.
14. Изображения/сцены, сгенерированные из рассказа, не использовать как memory aid; если они когда-либо создаются после capture, маркировать synthetic и исключать из evidence graph.

## 9. Cognition, neuropsychology и neurodevelopment

### 9.1. Три разные линии evidence

Subjective cognitive complaint, informant rating и performance-based task не взаимозаменяемы. Для executive functioning их корреляции часто малы, потому что они отражают разные levels/context и measurement demands [CLIN-028]. Поэтому нужны:

1. `SUBJECTIVE_COGNITIVE_REPORT`;
2. `ECOLOGICAL_FUNCTION_RATING`;
3. `PERFORMANCE_TASK_RESULT`;
4. отдельно `CLINICIAN_NEUROPSYCHOLOGICAL_INTERPRETATION`.

LLM не проводит neuropsychological assessment. Browser task без validated administration, norms и quality flags не получает клиническую интерпретацию. Обязательны sleep, fatigue, pain, sensory/language, education, medication/substance и device/testing context.

### 9.2. ADHD

NICE требует specialist assessment, полного developmental/psychiatric history, impairment и поведения в нескольких settings; rating scales сами по себе недостаточны [CLIN-029]. Retrospective recall childhood onset имеет существенные ошибки: в одной longitudinal cohort sensitivity была низкой, что делает отсутствие recalled childhood symptoms слабым отрицательным evidence [CLIN-030].

Решение: screen → `CONCERN_FOR_ASSESSMENT`, не diagnosis. Сохранять onset evidence, multiple settings, impairment, collateral/documents с consent, alternative explanations. Отсутствие collateral = `UNKNOWN`, не `ABSENT`. Поздно замеченные difficulties не доказывают ни adult-onset ADHD, ни его невозможность.

### 9.3. Autism

NICE adult guidance требует comprehensive assessment: early development where possible, direct observation, functioning, mental/physical differential и informant/document evidence [CLIN-031]. В referral sample RAADS-R не показал достаточной predictive validity; это не опровергает autism, но исключает single-score diagnosis [CLIN-032]. Camouflaging/masking поддерживается как важный феномен, однако literature heterogenous и во многом self-report [CLIN-033].

Модель хранит screening result, observed/reported phenomena, developmental evidence, masking/coping context и uncertainty отдельно. `Masking` не должно становиться unfalsifiable объяснением любой несогласованности; низкий screen также не закрывает оценку при meaningful concerns.

## 10. Emotion и behavior science

Meta-analysis 2026 года подтверждает transdiagnostic associations между mental disorders и рядом emotion-regulation patterns, но большая часть данных self-report/associational и не устанавливает direction/mechanism для индивида [CLIN-034]. Cross-cultural meta-analysis показывает существенную moderation: reappraisal и suppression нельзя маркировать универсально «хорошими/плохими» вне culture, goal и situation [CLIN-035].

Вместо морального ярлыка система описывает эпизод:

`antecedent/context → appraisal/goal → emotion/body report → action/avoidance → immediate consequence → delayed consequence → social/environmental feedback`.

Для regulation strategy хранить goal, controllability, timing, feasibility, culture, short/long-term outcomes. Rumination/avoidance/suppression — hypotheses о процессах, не identities. Behavioral activation имеет evidence для depression, но certainty преимущественно low–moderate и mostly short-term; она не является универсальным механизмом или автономным prescription [CLIN-036]. PSYCHE OS может помогать замечать activity–mood patterns, но не заявлять причинность из personal correlation и не назначать treatment.

## 11. Functioning, quality of life, strengths и thriving

ICF описывает functioning как взаимодействие health condition, body functions, activities, participation и environmental factors [CLIN-037]. WHODAS 2.0 даёт generic disability measurement в шести domains, но не diagnosis и не QoL; versions/modes/scoring нельзя смешивать [CLIN-038]. WHOQOL определяет QoL как субъективное восприятие в culture/value/goal context [CLIN-039]. Mental illness и positive mental health связаны, но не являются одной осью [CLIN-040].

Следовательно, v2 должен независимо хранить:

- `SYMPTOM_BURDEN`;
- `ACTIVITY_LIMITATION` и `PARTICIPATION_RESTRICTION`;
- `ENVIRONMENTAL_BARRIER_OR_FACILITATOR`;
- `SUBJECTIVE_QOL`;
- `POSITIVE_FUNCTIONING`;
- `SUPPORT_NEED` и `ACCOMMODATION`.

`THRIVING_EPISODE` — такой же evidence object, как difficulty: что происходило, какая способность проявилась, при каких условиях, для какой ценности/цели, какой был непосредственный и отсроченный outcome, насколько pattern повторился. Strengths-based interventions показывают лишь малый–средний pooled behavioral effect при ограниченной базе [CLIN-041]; поэтому strengths — наблюдаемые capacities/resources/person×context patterns, не тестовая «истинная сущность» и не замена symptom-focused care.

Отклоняются единый flourishing score, обязательная positivity, streaks за эмоциональное состояние и вывод «всё хорошо» из продуктивности. Успех может сосуществовать с distress; низкое well-being не является диагнозом. Пользователь вправе не искать meaning/growth в страдании.

## 12. Substances, behavioral addictions и medical confounding

### 12.1. Substance use

WHO ASSIST поддерживает структурированное выявление substance-related risk в primary care, но items/scoring/manual имеют rights и training constraints [CLIN-042]. Внутренняя модель должна сохранять substance/category, amount/unit, route, frequency, timing, context, tolerance/withdrawal report, control, harms, interactions и source — без moral labels. Screen result не является diagnosis. Нельзя смешивать prescribed use, nonmedical use и substance-use disorder.

### 12.2. Behavioral addictions

NICE gambling guidance подтверждает тяжёлые health/social harms и необходимость assessment/safeguarding, включая suicide risk, но относится к конкретному recognized problem и UK care context [CLIN-043]. Meta-review electronic “addictions” обнаруживает несогласованные definitions/measures и недостаток данных для сильных screening/treatment recommendations [CLIN-044].

Решение:

- recognized ICD category хранится только с system/version/requirements/functioning;
- generic `internet addiction`, `smartphone addiction`, `social-media addiction`, `porn addiction` не создаются как диагнозы;
- вместо них хранить behavior, time, loss-of-control report, priority, persistence, cue/context, harms/benefits и alternative explanations;
- moral/religious distress не подменяет impairment/diagnostic requirements;
- engagement metric продукта никогда не оптимизируется ценой sleep, autonomy или human relationships.

### 12.3. Medical confound

Psychiatric evaluation требует учитывать medical conditions, medications/supplements, sleep, pain, substances, neurologic/endocrine/infectious and other contributors [CLIN-045]. AI не должен диагностировать их или предлагать tests. Допустимые statuses:

- `NOT_ASSESSED`;
- `POSSIBLE_CONTRIBUTOR`;
- `USER_REPORTED_PREVIOUSLY_EVALUATED`;
- `CLINICIAN_DOCUMENTED`;
- `UNKNOWN`.

Confound checker задаёт нейтральные temporal/context questions и повышает uncertainty. Он не говорит «это щитовидка/лекарство/психосоматика». Изменение medication/substance, acute confusion, neurologic or severe physical symptoms должно вести к scope boundary и appropriate human medical pathway, а не к психологической интерпретации.

## 13. Core mental-health AI hazards и архитектурные меры

WHO требует defined intended use, stakeholder governance, transparency, auditing, privacy/security и контроля false/inaccurate/biased outputs для LMM в health [CLIN-046]. APA отдельно предупреждает, что general GenAI/wellness apps не заменяют qualified mental health providers и могут усиливать harms [CLIN-047]. Model evaluations находят stigma, inappropriate responses, reinforcement of delusional premises и crisis failures [CLIN-048]; experimental evidence показывает, что sycophantic advice может усиливать убеждённость и dependence [CLIN-049]. Даже suicide-risk alignment с экспертами непостоянен, особенно на intermediate levels [CLIN-050]. Эти исследования быстро устаревают и не позволяют вычислить population incidence, но достаточно сильны для preventive architecture.

| Hazard | Почему важен | Обязательная мера |
|---|---|---|
| Hallucinated fact/diagnosis | fluency создаёт ложную authority | evidence links, uncertainty, abstention, no diagnosis generation |
| Sycophancy | согласие может подкреплять ошибочную/опасную premise | reality-safe response policy: признавать emotion, не подтверждать unverified belief |
| Delusion/paranoia reinforcement | iterative conversation создаёт closed loop | no elaboration/investigation of bizarre claim; grounding, safety check, human help options |
| Memory contamination | leading prompts и reconstructions могут внедрять детали | anti-suggestive protocol, prompt logging, no recovered-memory features |
| Crisis inconsistency | LLM risk judgement нестабилен | deterministic risk state machine, conservative escalation, localized current resources, human review |
| Diagnostic drift | model/version меняет outputs | version pinning, regression evals, change control, expiry/reprocessing policy |
| Dependency/exclusivity | anthropomorphic support может вытеснять людей | no therapist/lover persona, no exclusivity claims, no guilt/retention pressure, encourage user-chosen supports |
| Cultural invalidity | norms/strategies differ | language/culture metadata, local review, no universal labels |
| Medical masking | психологическое объяснение задерживает care | confound status, red-flag boundary, no medical verdict |
| Privacy/reconstruction | longitudinal archive крайне чувствителен | data minimization, purpose binding, `NEVER_CLOUD`, derivative tracking/deletion, no training reuse |

Дополнительные требования:

- LLM работает только как proposal generator поверх deterministic policy, schema validation и provenance checks.
- Crisis/safety logic не полагается на один classifier/LLM и не обещает мониторинг, которого нет.
- Ресурсы помощи локализуются и имеют `verified_at`/expiry; stale resource не показывается как проверенный.
- Любой inference логирует model, prompt/template, context refs, output, uncertainty и reviewer status.
- Запрещены claims «я ваш терапевт», «только я вас понимаю», «не уходите», «я всегда рядом», а также simulated clinician authority.
- Personal correlation остаётся `ASSOCIATION_OBSERVED`; причинный language разрешён только при явном external evidence и корректной design qualification.
- Release gate требует adversarial evals для self-harm, mania/psychosis/delusion, eating disorder, substance use, abuse/coercion, grief, memory suggestion, dependency и medical red flags; отдельные human clinical/safety/privacy reviews обязательны.

## 14. Конкретный минимальный clinical-science contract для v2

До freezing F0 должны быть утверждены следующие invariants:

1. **Source separation:** raw/verbatim, normalized, derived и external records имеют разные immutable IDs и provenance edges.
2. **Temporal semantics:** event time, report time, observation time, interpretation time и knowledge-validity time не смешиваются; precision/uncertainty обязательны.
3. **No silent overwrite:** correction и supersession создают новые версии; contradiction сохраняется; deletion распространяется на reconstructive derivatives.
4. **Role/status:** user report, informant report, clinician document, imported record и AI hypothesis визуально и машинно различимы.
5. **Classification versioning:** ICD/DSM mapping без system/release/date/source недействителен.
6. **Instrument provenance:** score без instrument/version/language/mode/recall window/scoring/norm недействителен; LLM не считает deterministic score.
7. **Separate outcomes:** symptoms, functioning, QoL, positive functioning и risk не агрегируются в один hidden health score.
8. **Uncertainty:** `unknown/not_assessed/not_applicable/absent/present` различаются; отсутствие evidence не становится отрицанием.
9. **Anti-suggestion:** sensitive interview проходит deterministic question linting и сохраняет interviewer context.
10. **No autonomous clinical verdict:** diagnosis, treatment selection, forensic conclusion, medical cause и memory truth требуют человеческой компетенции вне модели.
11. **No ontology reification:** p-factor, HiTOP spectrum, attachment dimension, trait или AI cluster не отображаются как сущность/судьба человека.
12. **Positive evidence parity:** strengths/recovery/supportive conditions можно записывать с теми же provenance/time/uncertainty требованиями.

## 15. Явно отклонённые решения

- единый `mental_health_score`, `p-score` или causal root construct;
- diagnosis-by-chat, diagnosis from one questionnaire или hidden diagnostic inference;
- immutable attachment/personality types и horoscope-like narratives;
- lossless Big Five↔HEXACO mapping;
- causal childhood story generated from adult symptoms;
- memory confidence/vividness/coherence as accuracy;
- hypnosis, regression, guided imagery, dream/body cues for recovered memories;
- autism/ADHD diagnosis from retrospective self-report alone;
- universal ranking of emotion strategies as adaptive/maladaptive;
- generic technology/porn/social-media “addiction” labels outside versioned classification evidence;
- medical-condition inference by LLM;
- mandatory positivity, trauma growth, forgiveness or closure;
- AI therapist/companion exclusivity, simulated professional authority, reassurance loops;
- using copyrighted criteria, test items, manuals or translations without verified rights.

## 16. Remaining uncertainties и review triggers

1. ICD/DSM, RDoC matrix, NICE guidance и AI regulation/guidance являются moving targets; проверить не позднее dates в `review_due`.
2. HiTOP clinical utility и stable operationalization развиваются; не включать персональные scores до prospective validation.
3. Cross-cultural measurement invariance для language/jurisdiction-specific deployments должна оцениваться отдельно.
4. Adult autism/ADHD screens и retrospective onset evidence требуют instrument- и population-specific validation.
5. Moral injury, dissociation mechanisms, prolonged grief boundaries и electronic “addictions” сохраняют conceptual controversy.
6. Evidence об LLM rapidly model-specific; повторять evals при любой модели, prompt, safety-policy или context-window change.
7. Любое использование WHODAS, ASSIST, DSM-derived material или psychometric items требует отдельного rights/licensing review.
8. До `REAL_DATA_GATE` валидировать все workflows только на synthetic fixtures, включая correction, contradiction, crisis, consent withdrawal и derivative deletion.

## 17. Финальный научный вердикт

Наиболее защищаемый PSYCHE OS v2 — не система, которая «объясняет человека», а provenance-preserving longitudinal evidence workspace. Она помогает различать то, что было сказано, замечено, измерено, интерпретировано и профессионально классифицировано; оставляет причинность открытым вопросом; одинаково хорошо хранит difficulties и conditions for thriving; и технически не позволяет fluent AI-предложению незаметно стать фактом.
