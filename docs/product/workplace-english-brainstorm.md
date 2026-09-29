# Workplace English AI Tutor — Brainstorm and Design Handoff

Date: 2026-09-26

**Current handoff:** The [mockup summary and specification handoff](workplace-english-mockup-handoff.md) consolidates revision 02, the user's voice/scoring clarification, and the decisions for the product and technical specification session. The initial mockup brief below preserves the earlier discussion.

This document captures the product direction discussed so far and provides context for a separate mobile mockup session. It distinguishes agreed direction from proposed interaction details. Technical architecture and implementation planning remain to be completed.

## 1. Product direction

Build a real-time voice AI tutor that helps non-native English speakers find appropriate workplace expressions more easily and use them comfortably in conversation.

The product is organized around familiar workplace scenarios. Each scenario contains useful expressions and explanations of the reasoning behind them: what the speaker is trying to accomplish, why an expression helps, and when it fits. Learners can then practice using those expressions with a voice tutor.

The primary audience is people using the product on a phone. Mockups should use portrait phone proportions and account for touch interaction and limited screen space.

## 2. Agreed direction and remaining assumptions

| Area                                           | Status                                                                                                                                                                 |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Subject                                        | Workplace English was selected.                                                                                                                                        |
| Main difficulty                                | Appropriate words and expressions do not come to mind quickly enough, causing pauses that disrupt the conversation's rhythm.                                           |
| Desired improvement                            | Speak more naturally and appropriately, including making colleagues feel welcomed and comfortable.                                                                     |
| Content structure                              | Scenarios contain useful expressions and the reasoning behind those expressions.                                                                                       |
| Initial scenarios                              | Casual talk, one-on-one meetings, and hosting a meeting.                                                                                                               |
| Audience and format                            | Phone users are the primary audience; mockups should be portrait mobile screens.                                                                                       |
| Next activity                                  | Mockup revision 02 is available; a separate session will develop product and technical specifications.                                                                 |
| Voice priority, clarified during mockup review | Voice is always primary. The tutor should speak its responses and coaching; text supports meaning.                                                                     |
| Scoring, clarified during mockup review        | Give feedback across several dimensions after a completed spoken response. The current mockup proposes fluency, pronunciation, naturalness, and workplace tone.        |
| Learner proficiency                            | Some existing English knowledge is a working assumption. No proficiency level, native language, region, or career stage was fixed.                                     |
| Platform                                       | Native iOS/Android versus a mobile web frontend remains undecided. Phone-oriented mockups do not imply a native implementation.                                        |
| Visual style                                   | The mockup proposes Good Company, a warm ivory/charcoal/sage palette, Newsreader and Plus Jakarta Sans, and a 390 × 844 phone viewport. These remain design proposals. |

The discussion has enough personal context to proceed with product and visual design. The user explicitly preferred moving to the overall experience rather than continuing to investigate individual workplace situations in detail.

## 3. The learner's problem

The learner often knows what they want to communicate but spends too long searching for suitable English wording. Beyond expressing the basic meaning, they want to sound warm, natural, and appropriate for the situation.

The example that made this concrete was opening a meeting. The learner can say:

> Hello, thanks for joining the meeting. We'd like to discuss…

They want access to expressions that make the opening feel more welcoming, such as:

> Hey everyone, good to see you. Thanks for making the time today. Let's give folks another minute to join.
>
> Alright, shall we get started? Today, I'd like us to talk through…

The teaching opportunity is to explain the purpose of each piece:

- **Good to see you:** acknowledge the people.
- **Thanks for making the time:** appreciate their effort.
- **Let's give folks another minute:** create a relaxed opening while others join.
- **Shall we get started?:** gently transition into the meeting.

These are contextual examples. The learner should have room to choose expressions that fit their relationships and personality. Normal thinking pauses are part of conversation; the proposed learning goal is comfortable expression and easier recall.

## 4. Scenario and expression structure

The proposed organization is:

**Scenario → communication purpose or moment → expressions and reasoning → speaking practice.**

| Scenario                                       | Typical purposes                                                                                       | Example expressions                                                                             |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| Casual talk with colleagues                    | Start a conversation, show interest, share something, follow up, move into a deeper conversation       | "How did your presentation go?" / "That reminds me of…"                                         |
| One-on-one meeting with a manager or colleague | Describe recent work, share progress, explain a blocker, ask for support, discuss next steps           | "I've made some progress on…" / "I'm waiting on… before I can…" / "I could use your help with…" |
| Hosting a meeting                              | Welcome people, introduce the purpose, invite participation, transition, summarize, confirm next steps | "Good to see everyone." / "The goal today is…" / "Before we wrap up…" / "So we've agreed that…" |

An expression entry could contain:

- The purpose it serves.
- One main expression and a small number of alternatives.
- A plain-language explanation of why it works.
- Context about when it fits, including tone where helpful.
- A short example.
- Actions to hear it and practice using it.

The exact content count and entry fields are proposals to refine during design. A large curriculum is unnecessary for the take-home.

## 5. Proposed user experience

The working journey is:

**Choose a scenario → explore useful expressions → practice a conversation → get feedback and retry → leave with a takeaway.**

### Choose a scenario

The home screen asks, "What conversation do you have coming up?" It offers the three scenarios with clear descriptions of what the learner can practice. A direct route into practice for returning learners was also proposed.

### Explore expressions

Inside a scenario, expressions are grouped by what the learner wants to accomplish. For example, hosting a meeting includes welcoming everyone, introducing the purpose, and wrapping up.

Example content:

> **Make people feel welcomed**
>
> Good to see everyone. Thanks for making the time today.
>
> **Why it works:** You acknowledge the people and appreciate their time before introducing the task.
>
> **A more casual version:** Hey everyone, glad you could make it.
>
> Listen · Practice this

Learners can browse briefly and choose an expression to practice. The design should make the connection between an expression and its practice opportunity easy to understand.

### Practice with the voice tutor

The tutor provides a short setup and plays the other person in the conversation.

> You're hosting a weekly team meeting. I'll play a teammate. Welcome everyone and introduce what we're discussing.

The learner speaks, and the tutor responds in character. Proposed support includes an optional expression panel and a "Give me a hint" action that supplies a useful starter when requested.

Tutor turns should be concise and give the learner room to think. The proposed default is feedback after a short exchange. The interface should clearly distinguish the roleplay from the tutor's coaching feedback.

### Feedback and retry

Feedback references what the learner actually said and focuses on one or two useful changes.

During mockup review, the user requested several scoring dimensions, such as fluency and native-like expression. The revised design uses **Fluency, Pronunciation, Naturalness, and Workplace tone**, each out of 5, with one focused spoken suggestion. Naturalness describes idiomatic wording; pronunciation describes intelligibility. The tutor's voice leads the feedback; the transcript and written explanation are optional support. Mockup scores are explicitly illustrative. Real audio-dependent scores require audio evidence and a calibrated rubric; insufficient samples should remain unscored.

> Your purpose was clear. You could add "Good to see everyone" before the agenda to acknowledge the group. Give that opening another try.

A retry lets the learner immediately use the suggestion. A small variation in the situation can create another opportunity to recall the expression independently.

### Session takeaway

At the end, show a compact reminder of what was practiced, an expression to reuse, and its underlying pattern.

> **You practiced:** Welcoming people and introducing the agenda.
>
> **Expression to reuse:** Thanks for making the time.
>
> **Remember:** Acknowledge people → appreciate their time → introduce the purpose.

A takeaway within the practice screen was proposed. Saving expressions and revisiting previous sessions are possible extensions; their scope and identity requirements have not been decided.

## 6. Mobile mockup handoff

The recommended first design pass covers three primary screens, with supporting states where necessary:

| Screen               | What the design should communicate                                                                                   |
| -------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Scenario selection   | The three scenarios and the benefit of practicing each.                                                              |
| Scenario exploration | Expressions grouped by purpose, why they work, examples, and a clear path into practice.                             |
| Voice practice       | The situation, voice controls, speaking/listening status, optional help, and the transition into feedback and retry. |

The suggested reference flow is:

**Hosting a meeting → welcome everyone → practice an opening → receive feedback → try again.**

Hosting a meeting is the example for the mockup. The overall product still includes the other scenarios.

Design the practice screen early because it contains the most important interaction questions: how much text fits while speaking, how to request help, and how feedback appears. On a phone, the desktop idea of a panel "alongside" the conversation needs an appropriate mobile treatment. The designer should choose that treatment.

Use realistic expression content and dialogue in the mockups. Prioritize readable text, comfortable touch targets, accessible voice controls, and a clear main action. The exact navigation, layouts, transcript visibility, and treatment of microphone or connection problems still need design decisions.

### Skills discussed for the design session

- **imagegen-frontend-mobile:** recommended for generating portrait phone mockups and consistent mobile screen concepts.
- **minimalist-ui:** recommended as a possible visual direction, with restrained styling and readable layouts.
- Other available options discussed included **high-end-visual-design**, **design-taste-frontend**, **gpt-taste**, and **image-to-code**.

These were recommendations for the initial design session. The subsequent mockup and applied skills are recorded in the [mockup summary](workplace-english-mockup-handoff.md).

### Suggested opening message for the separate design session

> Read `docs/product/workplace-english-brainstorm.md` and `docs/requirements/general-take-home-project.md`. Create portrait phone UI mockups for the workplace English AI tutor described in the brief. Explore the three main screens, starting with the voice-practice experience, and use the meeting-opening example to keep the flow concrete. Review the available mobile mockup and visual-design skills before choosing an approach. Treat the visual style and interaction details marked as proposals as design decisions to resolve. Keep this session focused on mockups.

## 7. Take-home requirements and scope

The [original requirement document](../requirements/general-take-home-project.md) remains the source of truth. Its major constraints are:

- A real-time voice AI tutor using LiveKit, with a backend and frontend.
- Redis as the backing state store for conversations.
- Services runnable with Docker and Docker Compose after cloning the repository and supplying a root `.env` file.
- All secrets and configuration read from the root `.env`; an `.env.example` listing every required variable.
- Clear separation between session management, conversation handling, and the voice/AI layer.
- A README explaining architecture, decisions, tradeoffs, and what would change for 10,000 concurrent sessions.
- `PROMPT.md` containing the assignment prompt exactly.
- `workflow.md` recording the actual workflow, AI tools, models, and harnesses used.
- A short video showing the interface and functioning agent.
- Submission as a zip of the git repository, including `.git`.

The assignment gives an expected time of two hours and prioritizes working software. The proposed small product scope is three scenarios, a curated expression collection, one reusable practice experience, and a compact takeaway. Mockup work should stay focused enough to leave time for voice integration and a reliable runnable submission.

No frontend framework, backend language, speech or LLM provider, Redis schema, account system, or deployment setup has been selected. Technical design should resolve how the chosen frontend remains accessible to reviewers through the required Docker Compose workflow.

## 8. Research context and next steps

[Learner-interest research](../research/voice-tutor-learner-interest.md) contains the supporting sources. Coursera's popular career and workplace English courses and Duolingo's broad English-learning demand helped inform subject selection. Google Trends was rate-limited, so no live Trends ranking was obtained. These are interest signals, not validation of this exact product concept.

That research note records the earlier subject-selection stage. Workplace English and the three-scenario direction have since been selected, as recorded here.

The planned sequence is:

1. Create and review the portrait mobile mockups (revision 02 is now available).
2. Consolidate the chosen experience, tutor behavior, architecture, state handling, and failure behavior into a written specification.
3. Create an implementation plan around a working voice session and the required runnable delivery.
4. Implement, verify the conversation experience and Docker Compose startup, and prepare the submission materials.

A clickable mobile design study was also created, including the voice-first scoring revision. At this stage, it was still a mockup and product implementation had not started. The prototype and its assets are not included in the submission; the [handoff notes](workplace-english-mockup-handoff.md) preserve the design decisions.
