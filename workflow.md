# How I built this

I used AI throughout the project, from shaping the idea to debugging the voice experience. I worked in stages so I could review the product and try a working conversation before adding more features.

## AI setup

- **Codex app with GPT-6-Astra and Extra high reasoning.** This was my development assistant for discussing the product, creating mockups, writing specifications and code, investigating failures, and preparing the submission.
- **Codex skills.** I used brainstorming to work through product decisions, minimalist-ui for the phone layout, LiveKit skills for documentation and integration guidance, and diagnosing-bugs for focused investigations.
- **LiveKit documentation and SDK source.** I had Codex check integration details against the documentation and the pinned LiveKit Agents 1.8.2 source, especially when an API behaved differently from the generated code.

## My process

1. **Brainstorming.** I worked through the audience, workplace situations, and what a useful practice session should achieve. The [brainstorming brief](docs/product/workplace-english-brainstorm.md) gave the project a clear focus: short conversations with feedback the learner could use immediately.
2. **Design mockup.** I explored the flow in a clickable phone mockup: choosing a situation, speaking with Alex, reading feedback, and trying again. Reviewing it made the interaction decisions more concrete before implementation. The [handoff notes](docs/product/workplace-english-mockup-handoff.md) record what I took into the product spec.
3. **Product specification.** I turned those decisions into a [product spec](docs/product/workplace-english-product-spec.md) covering the learning journey, controls, feedback, retries, and temporary history. This became the reference for what the app should do.
4. **Technical specification.** I worked through the voice pipeline, Redis state, session ownership, API boundaries, and failure recovery in the [technical spec](docs/technical/workplace-english-technical-spec.md). This connected the product behavior to an implementation that could be tested.
5. **Implementation plan.** I split the work into a [milestone plan](docs/technical/workplace-english-implementation-plan.md) with checks at each stage. Configuration, provider access, and one complete voice journey came early, so integration problems would show up before the full interface was built.
6. **Implementation by milestone.** I used Codex to build and check each part: the runnable Compose setup, session rules, voice conversation, then the interface and learning features. The [milestone 2](docs/technical/workplace-english-milestone-2-checkpoint.md) and [milestone 4](docs/technical/workplace-english-milestone-4-checkpoint.md) checkpoints record progress and the issues to address next.
7. **Try it and refine it.** I tried the experience and gave feedback on what I saw and heard. That led to changes in turn-taking, Alex's voice and pacing, and speech buffering. The [audio investigation](docs/technical/workplace-english-audio-diagnosis.md) records how we checked transcription, model output, synthesis, playback, and recording.
8. **Demo video and submission.** I used a scripted learner to record the running app, reviewed the exported video, and prepared the README, workflow notes, and repository ZIP. The [demo notes](demo/README.md) and [verification record](docs/verification/workplace-english-release-checks.md) describe the walkthrough and packaging checks.

The [documentation guide](docs/README.md) collects the written records and supporting research. They preserve the process as it happened, including decisions that were later revised. The design prototype and its assets are not included in the submission.

## How AI helped me work

- **Make decisions concrete.** I used Codex to turn discussions into mockups, specifications, and an ordered plan that I could review and revise.
- **Keep changes manageable.** Milestones gave each implementation pass a clear goal and a way to check whether it worked.
- **Shorten the debugging loop.** Codex could read the relevant code, inspect SDK behavior, run a focused check, and make a correction in the same session.
- **Check the experience as well as the code.** Passing tests didn't always mean the audio sounded right. Listening feedback caught issues that required another round of investigation, including clipped speech in a recording.

## Tests and harnesses

- **pytest, pytest-asyncio, and real Redis:** checked session transitions, repeated commands, competing tabs, expiry, deletion, and the evidence used in assessments.
- **Vitest:** checked frontend logic, including how microphone and playback controls share access to audio.
- **Playwright with Microsoft Edge:** checked the interface, browser-specific history, saved review, and a full conversation over real WebRTC. The ordinary UI tests use fixtures; separate opt-in tests call the real models.
- **Provider preflight:** made small, real calls to transcription, conversation, speech, and assessment before testing the whole flow.
- **Docker Compose:** checked that a separate checkout could build and start all four services using a root `.env`.
- **FFmpeg and Python recording tools:** assembled the walkthrough and checked decoding and audio/video alignment. After listening feedback identified clipped speech, I added a comparison between recorded speech and the expected tutor text.

## Models used by the tutor

The running app uses these models through LiveKit Inference:

- **`google/gemini-3.5-flash`:** conversation and a separate assessment of the saved exchange.
- **`deepgram/nova-3`:** speech transcription.
- **`cartesia/sonic-3`:** spoken replies, examples, hints, and review playback.

GPT-6-Astra was used for development. The models above power the learner's session.

## What still needs human evaluation

- The walkthrough uses scripted synthetic learner speech. Alex's replies and coaching are generated by the running application.
- Synthetic speech makes checks repeatable, but it doesn't establish coaching quality across accents or behavior with physical microphones and echo.
- A video that decodes successfully can still contain incomplete speech. Recording checks need listening and content review as well as technical validation.

The [verification notes](docs/verification/workplace-english-release-checks.md) record completed checks and remaining limits.
