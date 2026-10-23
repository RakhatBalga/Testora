# 2. Evidence of Relevance

Requirement: 3–5 discussions with user representatives; distinguish verified findings from assumptions.

## 2.1 Method
- **Participants:** 5 people who are preparing for IELTS or have taken it, recruited among AITU students and acquaintances of the team (convenience sample).
- **Format:** structured interview in Telegram; each respondent answered the same 6 questions in writing. Participants agreed to the use of their answers; no names are stored.
- **Interviewers:** Rakhat Balgabekov, Nurhan Turganbek.
- **Questions:**
  1. Have you taken IELTS, or are you preparing for it? What band do you need, and what did you get or expect?
  2. How did you prepare, and roughly how much did you spend?
  3. Which part is the hardest for you, and why?
  4. Who checked your essays and Speaking? Was it clear what your mistakes were and why your score was not improving?
  5. Would you use an app that grades essays on the 4 IELTS criteria, finds repeated mistakes and gives a task for today? What would make you trust an AI score?
  6. How often would you use it, and how much would you pay per month?

Full guide: `docs/interviews/interview-guide.md`.

## 2.2 Respondents

| # | Date | Format | IELTS status | Target / current band | Main preparation |
|---|---|---|---|---|---|
| R1 | 23 Oct 2026 | Telegram, written | Preparing, first attempt (exam 30–31 Oct 2026) | 6.5 / about 6.5 on practice tests | Self-study (Cambridge IELTS), AI chatbot for feedback |
| R2 | 23 Oct 2026 | Telegram, written | Took IELTS about 3 years ago, plans to retake | not stated | Offline courses (about 210,000 KZT), online platforms, YouTube |
| R3 | 23 Oct 2026 | Telegram, written | Took IELTS twice (7.0, then 7.5), preparing again | 8.0 / 7.5 | Tutor for 3 months, then self-study with ChatGPT |
| R4 | 23 Oct 2026 | Telegram, written | Preparing | 7.0 / 6.0–6.5 expected | YouTube, free websites, practice tests (about $50) |
| R5 | 23 Oct 2026 | Telegram, written | Preparing, exam this autumn | 8.0 expected | Official books, online mock tests, AI chatbots (no paid tutor) |

## 2.3 Findings

| # | Finding | Respondents | Evidence (quote) | Affects requirement |
|---|---|---|---|---|
| F1 | **Writing is the hardest part** for most respondents. | 4 of 5 (R1, R3, R4, R5); R2 named Speaking | R4: "Writing is the hardest because it's difficult to organize ideas and avoid grammar mistakes." R5: "advancing from 7.5 to 8.0 may take a lot of time." | FR-4, FR-5: Writing stays the core of the MVP |
| F2 | **General AI chatbots are already the main feedback tool**; paid tutors are used less. | 4 of 5 (R1, R3, R4, R5); R2 used a tutor | R4: "I mostly use AI to check my essays." R5: "I use AI chatbots, they are more than capable of giving detailed feedback." | Competition is with free chatbots, not only with paid tools (section 4) |
| F3 | **Chatbot feedback lacks tracking of repeated mistakes and is not always clear.** | 2 of 5 (R1, R4) | R1: "I couldn't easily see which ones I kept repeating from essay to essay, so I didn't always know what to practise next." R4: "Sometimes the feedback isn't clear enough." | FR-6, FR-8, FR-9, FR-10: confirms the weakness engine and the task for today |
| F4 | **Trust in an AI score depends on alignment with official criteria and explained mistakes.** | 4 of 5 (R1, R2, R4, R5) | R1: "point at the specific sentences that cost me points and link them to the band descriptor." R2: "I would not completely trust AI, as it does not always understand the exact criteria." | FR-5, FR-6; NFR on stable scoring; validation against examiners (section 9) |
| F5 | **Learners expect consistent scores and published validation.** | 1 of 5 (R1) | R1: "The same essay should also get the same score if I submit it twice. And I'd want to see how the AI was tested." | Test–retest and agreement metrics in the experiment (section 9) |
| F6 | **Usage is intensive but limited to the preparation period.** | 5 of 5 | R1: "Every day until the exam… for me this is a one- or two-month product." R3: "every day if I were actively preparing." R4: "4–5 times a week." | FR-10 (daily task, study plan); short subscription periods |
| F7 | **Willingness to pay is low and varies.** | 3 of 5 would pay; 1 would not; 1 did not say | R4: $5–10; R5: $10–20; R1: $20–40. R2: "I don't think I would pay… there are plenty of other free resources." | Free tier (FR-19); pricing stays an open question |
| F8 | **Speaking feedback on pronunciation is missing in current tools.** | 2 of 5 (R1, R2) | R1: "a text chat can't hear how I actually sound." R2: Speaking "reduced the total score that I got." | FR-14, FR-15: supports the Speaking module |
| F9 | Some learners want a study calendar or a Writing-only focus. | 1 of 5 (R5) | R5: "would use it according to the calendar if the app has one"; "we need a specialized app for Academic Writing only." | FR-10 (study plan) |

## 2.4 Verified findings vs assumptions

| Statement | Source | Status |
|---|---|---|
| Writing is the hardest and most important part to support | Interviews (F1, 4 of 5) | **Confirmed** in this sample |
| Feedback on Writing/Speaking is the most expensive and least available part of preparation | Interviews (F2); competitor pricing (section 4) | **Revised.** Tutors and courses are expensive (R2: about 210,000 KZT), but 4 of 5 now get free feedback from AI chatbots. The gap is not access to feedback but its structure: repeated mistakes and what to practise next (F3). |
| Learners do not understand why their band does not grow | Interviews (F3) | **Partially confirmed:** 2 of 5. R2, R3 and R5 found their feedback clear. |
| Learners would trust and use an AI band estimate with explanations | Interviews (F4) | **Confirmed with conditions:** 4 of 5 would use it if scores follow the band descriptors and point to specific mistakes; 1 of 5 is sceptical. |
| Per-criterion AI scoring is already offered by existing tools | Section 4 (vendor pages, checked 22 Oct 2026) | Verified (desk research) |
| LLM scores agree with expert scores well enough to be useful | Literature (section 3) | Partially supported in literature; to be measured in our experiment (section 9) |
| Learners will pay for the product | Interviews (F7) | **Assumption.** 3 of 5 named $5–40 per month; 1 of 5 would not pay. Needs a larger sample. |
| Speaking feedback with pronunciation is needed | Interviews (F8) | **Partially confirmed:** 2 of 5 |

## 2.5 Conclusions for the project
- The core loop (grade on 4 criteria → repeated mistakes → task for today) answers a problem that respondents described in their own words (F3). The main competitor is a general AI chatbot, so Testora must show what a chatbot does not: memory of repeated mistakes across essays and a clear next step.
- Trust needs evidence: sentence-level mistakes linked to the band descriptors, stable scores for the same essay and published agreement with human examiners. These become acceptance criteria in sections 6 and 9.
- People use such a tool intensively for 1–2 months before the exam, so the daily task and the study plan matter more than long-term retention features.
- **Limitations:** 5 respondents, a convenience sample of students known to the team, written answers and self-reported bands. Two respondents already score 7.5–8.0, which is above the main target group. The findings guide the MVP but are not statistically representative.

## 2.6 Supporting data
- Desk research of existing systems and their prices (section 4).
- Literature on automated scoring and LLM graders (section 3).
- Usage data from the deployed platform (testora.studio) will be analysed during the pilot (section 9).
