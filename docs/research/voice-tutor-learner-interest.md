# Subject ideas for the voice AI tutor

Researched 2026-09-26. This is a brainstorming research note, not an approved product specification.

## Decision context

The [take-home brief](../requirements/general-take-home-project.md) asks for a real-time voice AI tutor using LiveKit, a frontend and backend, Redis conversation state, and Docker Compose. Expected time is two hours, with working software valued over polish. A useful subject should have an identifiable learner, a reason to practice aloud, and a small learning outcome that can be demonstrated in a few minutes.

## Evidence from primary sources

### English learning and career relevance

- Duolingo's **2025 Duolingo Language Report**, published December 1, 2025, says English was the most studied language on its platform in **154 countries**, or **79% of countries** in its analysis. The reporting period is October 1, 2024 through September 30, 2025. Rankings exclude countries with fewer than 5,000 Duolingo learners, and the analysis excludes learners under 13.
- This supports broad interest in learning English among Duolingo learners. It does not establish the size of a workplace-English or interview-coaching market.
- Source: https://blog.duolingo.com/2025-duolingo-language-report/
- Coursera's **2026's Fastest-Growing Skills and Top Learning Trends From 2025**, published December 16, 2025, includes **English for Career Development** and **English for Common Interactions in the Workplace: Basic Level** in its list of most popular university-partner courses in 2025.
- This provides a more specific signal for professional English. The article does not provide enrollment counts for these individual courses.
- Source: https://blog.coursera.org/2026s-fastest-growing-skills-and-top-learning-trends-from-2025/

### Japanese and Korean

- Duolingo's 2025 report says Japanese rose to **fourth** among languages studied globally on Duolingo, and Korean rose to **sixth**.
- Duolingo also expanded course availability: speakers of more than 20 languages could newly study Japanese and Korean directly from their own language. The report explicitly links expanded access with the ranking changes, so these shifts cannot be attributed solely to increased underlying demand.
- Language interest does not by itself establish travel motivation. A travel tutor is a product hypothesis built on this broader signal.
- Source: https://blog.duolingo.com/2025-duolingo-language-report/

### Practical AI literacy

- Coursera's December 16, 2025 article reports **5.4 million generative-AI enrollments**, nearly double the prior year's total, with data **as of September 30, 2025**.
- Its popular industry-partner courses include **AI For Everyone**, **Introduction to Generative AI**, and **Generative AI: Prompt Engineering Basics**.
- Enrollments are not unique learners; this is evidence about Coursera's audience, rather than the whole population or demand for a voice tutor.
- Source: https://blog.coursera.org/2026s-fastest-growing-skills-and-top-learning-trends-from-2025/

### General willingness to use AI for learning

- Google's **Learners and educators are AI's new "super users"**, published January 15, 2026, describes a Google/Ipsos survey conducted in late 2025 across **21 countries and 21,000 participants**.
- Google reports **74% of AI users** use it to learn something new or understand a complex topic. This is a self-reported motivation, not evidence of learning effectiveness or preference for voice.
- Source: https://blog.google/products-and-platforms/products/education/our-life-with-ai-2025/

## Google Trends limitations and follow-up

The public Google Trends Explore page returned HTTP 429 during this research. No live query comparison or search-volume ranking was obtained. Google Search also showed an unusual-traffic page; no verification challenge was attempted.

Google's official Trends FAQ explains that Trends uses sampled search requests and normalizes results by geography and time, then scales them from 0 to 100. These are relative search-interest values, not absolute search counts or polling results.

Source: https://support.google.com/trends/answer/4365533?hl=en

If we later use Trends to narrow the topic, first choose the learner geography and search language. Compare a small set of relevant topics or consistently defined query groups over the same period. Keep seasonal travel interest, course launches, and curiosity about AI separate from demonstrated learning intent. The current recommendation does not depend on an unverified Trends ranking.

## Candidate concepts and product judgment

The following are design hypotheses, not conclusions established by the reports.

| Concept | Intended learner | Small learning outcome | Why voice helps | Main scope concern |
| --- | --- | --- | --- | --- |
| Workplace English: explain a project clearly | Early-career professionals with intermediate English | Give a clear, structured 60-second explanation and improve it after feedback | Speaking under follow-up questions is the skill being practiced | Keep to one scenario; assess understandable language and structure without implying validated pronunciation scoring |
| Travel Japanese: order a meal and handle a follow-up | Beginners preparing for a trip to Japan | Complete one restaurant exchange using a few useful phrases | Real-time listening and responses resemble the target situation | Beginner scaffolding and multilingual recognition need care; demand for travel specifically is unverified |
| Practical AI literacy: evaluate an AI answer | Nontechnical adults using AI at work | Explain why a plausible answer may need checking and propose a verification step | Teach-back and follow-up questions can expose misunderstandings | Practical prompting often benefits from text; voice is less central than in language practice |

## Recommendation for discussion

Start with **workplace English for early-career professionals**, using one scenario such as explaining a project to a colleague. This combines broad language-learning interest with a more specific career-English signal and a task that naturally benefits from spoken practice.

A candidate demonstration is: the tutor asks for a short explanation, the learner attempts it, the tutor identifies one concrete improvement, the learner retries, and the tutor points out what improved. This keeps the learning outcome observable and the content small enough to fit the take-home constraints.

Travel Japanese offers a playful alternative if the builder is more interested in that subject. Practical AI literacy offers strong topical interest, but needs a deliberate teach-back interaction to make voice valuable.

The subject and learner are still open decisions. No product implementation was performed.
