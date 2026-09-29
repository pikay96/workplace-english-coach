# Project documentation

Start with the guides below to understand or run Workplace English Coach. The development history records how the product and implementation took shape.

## Choose a starting point

- **See the product:** the [main README](../README.md) and [walkthrough guide](../demo/README.md) introduce the practice and coaching flow.
- **Run or change the app:** the [development guide](development.md) covers configuration, provider checks, and tests.
- **Explore the code:** the [engineering notes](engineering.md) explain component boundaries, session ownership, feedback evidence, recovery, and scaling.
- **Review the evidence:** the [verification record](verification/workplace-english-release-checks.md) lists completed checks, dates, and remaining limits.
- **Understand the build process:** [How I built this](../workflow.md) describes the AI tools, models, milestones, and decisions I reviewed.

## Development history

These documents preserve the process as it happened. Some contain earlier voices, scoring dimensions, and milestone statuses that were later revised. Use the main README and engineering notes for current behavior.

- **Brainstorming:** [subject research](research/voice-tutor-learner-interest.md) and the [workplace English brief](product/workplace-english-brainstorm.md) explain the audience and initial learning flow.
- **Design mockup:** the [handoff notes](product/workplace-english-mockup-handoff.md) record the interaction choices and questions carried into the product spec. The prototype and its assets remain outside the tracked project.
- **Product specification:** the [product spec](product/workplace-english-product-spec.md) records requirements for practice, feedback, controls, retries, and temporary history.
- **Technical specification:** the [technical spec](technical/workplace-english-technical-spec.md) covers the voice pipeline, Redis state, API boundaries, and recovery. The shared vocabulary is in [CONTEXT.md](../CONTEXT.md).
- **Implementation plan:** the [milestone plan](technical/workplace-english-implementation-plan.md) breaks the work into stages with checks at each step.
- **Implementation checkpoints:** the [milestone 2](technical/workplace-english-milestone-2-checkpoint.md) and [milestone 4](technical/workplace-english-milestone-4-checkpoint.md) notes record progress, tests, and open issues at those points.
- **Trying and refining the experience:** the [audio investigation](technical/workplace-english-audio-diagnosis.md) follows speech delivery, voice, and pacing changes. The later [verification record](verification/workplace-english-release-checks.md) documents the walkthrough's speech-content checks.
- **Original brief:** the project began as a [take-home exercise](requirements/general-take-home-project.md). [PROMPT.md](../PROMPT.md) retains the submitted copy of that brief.
