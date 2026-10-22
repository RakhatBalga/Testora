# 4. Comparison of Existing Systems

## 4.1 Selection of systems and criteria

Many websites help people prepare for IELTS. We compared only those that, like Testora, give **automated (AI) feedback on productive skills** (Writing and/or Speaking) and are open to self-study learners. We chose four systems:

| # | System | Why it was selected |
|---|---|---|
| S1 | **Writing9** (writing9.com) | A well-known paid AI checker for IELTS Writing that reports a band for each criterion |
| S2 | **IELTS Online Tests** (ieltsonlinetests.com) | A large free bank of full mock tests, plus paid AI and human evaluation |
| S3 | **SmallTalk2Me** (smalltalk2.me) | An AI Speaking simulator with an estimated IELTS band and a learning path |
| S4 | **IELTS Ready** (British Council) | The official preparation platform of a test owner, with AI feedback and a progress dashboard |

**Excluded:** Engnovate is popular, but its pages returned HTTP 403 to our checks on 2026-10-22. The only descriptions we found were from third parties, including a competitor (PrepEx), so we could not support claims about it with first-party evidence. IELTS Liz and Magoosh mainly offer lessons, videos or human feedback, so they do not compete on automated scoring.

**Criteria (8).** Each criterion matches a step of Testora's core loop or a constraint from its target users, who are budget-limited self-learners:

| ID | Criterion | What counts as "yes" |
|---|---|---|
| C1 | Writing AI scoring by the 4 IELTS criteria | A separate band for TA/TR, CC, LR and GRA, not only an overall band |
| C2 | Speaking AI scoring | An automated band estimate from the learner's recorded speech |
| C3 | Mistake explanation and diagnosis | Mistakes shown with reasons, plus a statement of *which* weakness most limits the band |
| C4 | Personalised next task | The system picks what to practise next from the learner's own results |
| C5 | Reading/Listening full tests with evidence | Full tests are checked automatically, and the text passage supporting each answer is shown |
| C6 | Progress tracking over attempts | A history or chart of bands across attempts |
| C7 | Price / free access | Whether a learner can use the AI feedback without paying |
| C8 | Transparency / validation of AI scores | A published method or evidence of agreement with human examiners, or at least a clear disclaimer |

All competitor pages were checked on **2026-10-22**. Codes in square brackets, such as [E1], refer to the evidence list in 4.3.

## 4.2 Comparison table

Legend: **Yes** = confirmed on the vendor's page; **Partial** = only part of the criterion is met; **No / not found** = not present on the pages checked; **Unclear** = mentioned but not described well enough to judge.

| Criterion | S1 Writing9 | S2 IELTS Online Tests | S3 SmallTalk2Me | S4 IELTS Ready (BC) | **Testora (target)** |
|---|---|---|---|---|---|
| **C1** Writing, 4 criteria | **Yes**: TA, CC, LR, GR plus overall band [E1] | **Yes**: AI Examiner gives the 4 criteria plus overall [E4] | **Unclear**: a Writing Simulator exists, but its scoring is not described [E6][E7] | **Unclear**: "AI feedback for all four skills", per-criterion breakdown not verified [E8] | **Implemented**: LLM grader returns the 4 criteria as validated JSON |
| **C2** Speaking AI | **No / not found**: a "Speaking Simulator" links to a separate site, scoring not stated [E2] | **Partial / unclear**: the homepage lists AI evaluation for Speaking, but the Speaking evaluation page describes a human examiner (USD 19.99, 48 h) [E3][E5] | **Yes**: estimated band on IELTS speaking criteria [E6][E7] | **Unclear**: AI feedback "across all four skills" in the mock tests [E8] | **Implemented**: the LLM grades the recorded audio. **Research:** Whisper ASR + fluency features + regression |
| **C3** Mistakes and diagnosis | **Partial**: "Weakness discovery", sub-checks per criterion; no single main-blocker diagnosis found [E1][E2] | **Partial**: inline corrections with a short reason, plus comments per criterion [E4] | **Partial**: "actionable insights to target your weaknesses" (Speaking) [E7] | **Not found** on pages checked | **Implemented**: extracts mistakes and names the main reason the band is stuck (weakness model with recency decay) |
| **C4** Personalised next task | **Partial**: "Personalized suggestions" (Premium) [E2] | **Partial**: a placement test builds a learning path; 1-on-1 coaching is paid [E3] | **Partial**: "learning path tailored to your level", recommendations [E6][E7] | **Partial**: dashboard "with study recommendations" [E8] | **Implemented**: rule-based "task for today" from the main weakness. **Research:** adaptive selection with IRT/Rasch + knowledge tracing |
| **C5** R/L tests with evidence | **No**: only a Listening practice bonus [E2] | **Partial**: free full tests [E3]; explanations or evidence per answer not confirmed | **No**: Listening is a practice mode only; Reading not mentioned [E6][E7] | **Partial**: 40 full practice tests "with scores and model answers" (Premium) [E8] | **Implemented**: automatic checking with a verbatim evidence passage for every answer |
| **C6** Progress tracking | **Not found** | **Not found** as a dedicated tracker [E3] | **Yes**: "Every gain is logged and visible" [E6] | **Yes**: dashboard with progress tracking [E8] | **Implemented**: band history, trajectory, and the band change after a regrade |
| **C7** Price / free access | Paid only: USD 7.99/week, 14.99/month, 29.99/year; demo available [E2] | Tests free; AI Writing evaluation USD 4.99 per essay [E3][E4] | Free Speaking mock with estimated band; Pro price not shown [E6][E7] | Free Mini Mock Test with AI feedback; Premium free only after booking an IELTS test with the British Council; detailed AI feedback "from US$3.99" [E8] | Free quota of AI grades (currently 2 Writing + 2 Speaking); R/L tests free; paid plan not yet defined |
| **C8** Transparency / validation | Self-claims only: "tested … on thousands of essays", "meets British Council standards"; also says the result is "a scoring estimation" [E2] | Self-claims: "Accuracy up to 95%", trained on "28 million students"; no method published [E4] | "95% CEFR English level accuracy" refers to CEFR, not IELTS bands; no method [E6] | User-satisfaction figures (97% / 98%) from a pilot, not score accuracy [E9] | **Partial**: calibration script compares model bands against reference essays (±0.5 band tolerance); public validation report (MAE/QWK vs. human bands) **planned** |

## 4.3 Evidence

All pages accessed 2026-10-22.

| ID | Claim(s) supported | Source |
|---|---|---|
| E1 | Writing9 scores Coherence & Cohesion, Lexical Resource, Grammatical Range, Task Achievement with sub-checks, plus "Overall Band Score" | https://writing9.com/draft |
| E2 | Writing9 prices (USD 7.99/week, 14.99/month, 29.99/year), no free tier stated, demo, "Weakness discovery", "Personalized suggestions", Speaking Simulator links to speaking9.com, Listening Practice bonus, "scoring estimation", "tested the algorithms on thousands of essays", "meets British Council standards" | https://writing9.com/ |
| E3 | IELTS Online Tests: "Our online IELTS tests are always free"; AI Examiner Evaluation listed for Writing and Speaking; human examiner option; placement test → learning path | https://ieltsonlinetests.com/ |
| E4 | IELTS Online Tests AI Writing: 4 criteria + overall band, inline corrections with reasons, USD 4.99 per essay, "Accuracy up to 95%", "28 million students" | https://ieltsonlinetests.com/ielts-writing-ai-examiner-evaluation |
| E5 | IELTS Online Tests Speaking evaluation by a professional examiner, USD 19.99, 48 h | https://ieltsonlinetests.com/ielts-speaking-examiner-evaluation |
| E6 | SmallTalk2Me: estimated Speaking band, "learning path tailored to your level", "Every gain is logged and visible", free sign-up, "95% CEFR English level accuracy" | https://smalltalk2.me/ |
| E7 | SmallTalk2Me IELTS page: Speaking assessed on the IELTS speaking criteria, "Personalized IELTS speaking improvement recommendations", free Speaking mock test; Writing Simulator linked but scoring not described; Reading not mentioned | https://smalltalk2.me/ielts |
| E8 | IELTS Ready: 40 full practice tests with scores and model answers, optional AI feedback for all four skills "from just US$3.99", Express Mock Test, personalised dashboard with study recommendations and progress tracking, free Mini Mock Test; Premium free with a British Council test booking | https://takeielts.britishcouncil.org/prepare/ielts-ready ; https://www.britishcouncil.or.th/en/ielts-ready-premium ; https://www.britishcouncil.vn/en/ielts-ready-premium |
| E9 | IELTS Ready Premium launch (July 2023), 97% / 98% user-satisfaction figures from the pilot | https://britishcouncil.org.tw/en/about/press/british-council-ielts-launches-%E2%80%9Cielts-ready-premium%E2%80%9D |

**Limits of the evidence.**
- **E8 was not read directly.** The British Council pages timed out when we tried to load them on 2026-10-22, so E8 rests on the indexed text of those official pages returned by web search.
- **Claims are taken from the vendors' own pages.** We did not create paid accounts. Where a feature may sit behind a paywall, it is marked "Unclear" rather than "No".
- **Accuracy figures are the vendors' own.** None of the four systems publishes a method that would let anyone check them.

## 4.4 Identified gap

The comparison supports three conclusions:

1. **Scoring is common; diagnosis is not.** S1 and S2 already give per-criterion Writing bands, and S3 gives a Speaking band. Testora's scoring alone is therefore not new. What none of the checked systems states is *which single weakness is keeping the band where it is* and *what to do today about it*, followed by regrading to show whether the band moved. That closed loop (grade → mistakes → main blocker → task → regrade → band change) is the gap Testora addresses.
2. **No checked system combines all four skills, evidence-based Reading/Listening and low cost.** S1 and S3 focus on one productive skill. S2 has free tests but charges per AI essay. S4 is the most complete, but its full Premium access depends on booking a British Council test, and detailed AI feedback is paid. None of the checked pages shows the exact text passage that proves each Reading/Listening answer.
3. **Nobody publishes how accurate their AI scores are.** All accuracy statements found are unverifiable vendor claims ("up to 95%", "meets British Council standards"). Testora does not solve this yet. A calibration tool exists, but a public validation report is planned and not finished. This is a shared limitation, and Section 3 already identified it as a research gap. Testora has to measure and report its error against human-rated essays rather than claim parity with examiners.

**Honest limitations of Testora compared with these systems.**
- **Smaller content bank.** S4 offers 40 full tests; Testora has fewer.
- **No human-examiner option.** S2 offers one; Testora does not.
- **Adaptive selection is still research.** IRT/knowledge tracing are not yet in production.
- **Speaking runs on a general LLM.** It is not yet a specialised, validated speech-scoring model.
