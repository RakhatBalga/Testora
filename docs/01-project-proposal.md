# 1. Project Proposal

## 1.1 Project title
**Development of an Intelligent IELTS Exam Preparation System Based on Large Language Models and Machine Learning Methods (Testora)**

## 1.2 Team and supervisor

| Role | Name | GitHub | Area of responsibility |
|---|---|---|---|
| Student | Rakhat Balgabekov | [RakhatBalga](https://github.com/RakhatBalga) | LLM-based assessment core (Writing), user weakness model and personalization, system architecture, backend, deployment |
| Student | Nurhan Turganbek | [nurhan-ghost](https://github.com/nurhan-ghost) | Speaking ML assessment module, adaptive Reading/Listening practice, security and reliability, practice UI, learning content, testing |
| Supervisor | Tomiris Zhaksylyk | — | Supervision, review of key deliverables |

Educational programme: Software Engineering, Astana IT University. Pre-defense and defense: May 2027.

## 1.3 Problem statement
Millions of people take IELTS every year to study, work or immigrate. The most expensive part of preparation is feedback on the productive skills — Writing and Speaking: a human tutor or examiner is unaffordable for many candidates, and without feedback learners do not know *why* their band does not grow.

Existing online trainers (see section 4) can already give a band score per criterion, but they usually stop there: the learner receives a number and a list of corrections for one attempt, not an explanation of the recurring mistakes that block their band and a concrete next step. Reading and Listening practice is widely available, but answers are rarely justified with evidence from the text, which limits learning from mistakes.

**Problem:** budget-limited IELTS candidates lack affordable, explainable and personalized feedback that connects individual attempts into a learning path — what is wrong, why the band is stuck, what to do today, and whether it helped.

> Verification status: the problem is based on the team's own preparation experience, analysis of existing systems (section 4) and literature (section 3). It was checked in 5 interviews with IELTS candidates (section 2): Writing is the hardest part for 4 of 5, and the missing piece in current AI feedback is tracking repeated mistakes. Findings not confirmed by interviews are treated as assumptions.

## 1.4 Target users
- **Primary:** people worldwide preparing for IELTS Academic or General Training for study, work or immigration, especially those with a limited budget who prepare on their own.
- **Secondary:** learners who already have a tutor and want extra graded practice between lessons.
- **Out of scope as users:** teachers/schools managing groups (possible future extension).

## 1.5 Aim
To design, implement and evaluate a web-based intelligent IELTS preparation system that assesses Writing and Speaking answers with large language models and machine-learning models, explains the main reason why the learner's band is not improving, and adapts practice to the learner's weaknesses.

## 1.6 Objectives
1. Analyse the domain: IELTS assessment criteria, existing preparation systems, and research on automated essay/speech scoring, LLM-based assessment and adaptive learning (sections 3–4).
2. Collect and specify requirements, validated with user interviews (sections 2, 6).
3. Design the architecture of the platform and its ML components (section 7).
4. Implement LLM-based Writing assessment on the four IELTS criteria with mistake extraction (**implemented**).
5. Implement the user weakness model (recency-weighted mistakes, band gap) and the personalized loop "grade → mistakes → main cause → task for today → regrade" (**v1 implemented**).
6. Implement the Speaking assessment module: speech recognition (Whisper), fluency features and a band prediction model (**research code implemented, integration planned**).
7. Implement adaptive Reading/Listening practice: item difficulty calibration (Rasch/IRT) and knowledge tracing (**research code implemented, integration planned**).
8. Evaluate the system: accuracy of automatic assessment against expert scores (MAE, QWK, ±0.5 band agreement), WER, AUC of adaptive prediction, and a pilot with real users (section 9).

## 1.7 Expected outcomes
- A deployed web platform (https://testora.studio) with the full loop: assessment → mistakes → main blocker → task for today → regrade → band change.
- An integrated Speaking assessment module and adaptive Reading/Listening selection.
- An experimental report on assessment quality: MAE/QWK vs expert scores for Writing and Speaking, stability of LLM grading across runs, comparison of several LLMs with a baseline ML model, WER of speech recognition, AUC of adaptive prediction.
- Pilot results with real users and the explanatory note.

## 1.8 Project scope

**In scope**
- IELTS only (Academic and General Training), all four skills.
- Web application (desktop and mobile browser).
- Writing and Speaking assessment by the four official IELTS criteria; mistake extraction and recurring-mistake analysis.
- Reading and Listening tests with automatic checking and verbatim evidence for answers.
- Personalization: weakness model, band gap, next task recommendation, adaptive item selection.
- Experimental evaluation of assessment quality.

**Out of scope**
- Other exams (TOEFL, SAT, Duolingo English Test, etc.).
- Native mobile applications.
- Official certification or prediction of the real exam result with guaranteed accuracy — Testora gives practice estimates.
- Social/community features, teacher dashboards, payments infrastructure (may appear later, not part of the diploma).
- Training a large language model from scratch.

## 1.9 Engineering complexity
- Assessment of open-ended answers by an LLM with structured, schema-validated output, calibration and a provider-independent model layer.
- Measuring the quality and reproducibility of AI grading against expert scores (MAE, QWK) and comparing it with a classical ML baseline.
- Speech processing: ASR, fluency features, regression models evaluated on speaker-disjoint splits.
- Psychometric modelling (Rasch/IRT) and knowledge tracing for adaptive practice.
- A production web system: FastAPI + PostgreSQL backend with Clean Architecture, Next.js frontend, authentication (JWT, Google OAuth with PKCE), rate limiting and quotas, CI, cloud deployment.

## 1.10 Current status (October 2026)
The platform is deployed and the core loop for Writing works with Gemini-based grading. Reading/Listening tests, the first version of the weakness model and the personalization loop are implemented. The Speaking and adaptive modules exist as research code with evaluation metrics and are planned for integration. Accuracy against expert scores has not been measured yet — labeled datasets are planned for November 2026. See section 10 for milestones.
