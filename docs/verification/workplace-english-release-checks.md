# Verification notes

This record covers the initial Workplace English Coach build and walkthrough, verified on September 27, 2026 using Windows, Microsoft Edge, and four Linux containers. The checks establish a working demonstration; production reliability and broader learner evaluation remain open. For commands to run today, see the [development guide](../development.md).

## Application checks

Previously recorded verification on September 27, 2026:

- An extracted submission built and started through Docker Compose with a root `.env`; web, API, agent, and Redis became healthy. Existing Docker build caches were available.
- Provider preflight completed real conversation, speech synthesis, streaming transcription, and evidence-validated assessment calls.
- The ZIP review recorded 63 backend tests, 9 frontend tests, 6 browser tests, and the frontend production build passing.
- A real WebRTC journey exercised practice, generated feedback, and saved review. An earlier, longer journey also covered a focused retry with separate evidence and unchanged original scores.
- History checks verified that records belonged to the current browser guest and disappeared after deletion. Completed review did not request a microphone.

These are records of those runs. Individual provider timings are not latency percentiles, and synthetic learner audio is not a physical microphone test.

## Walkthrough audio correction

Listening feedback identified clipped speech in the earlier 1:49 walkthrough. A transcription of that recording confirmed that an opening saved as “Could you get us started?” ended after “Could.” The following tutor reply was complete. Synthesizing the same opening directly produced its full text.

The earlier checks established file decoding, waveform alignment, and successful application state transitions. They did not prove that all intended words reached the recording. A separate check now compares recorded speech with saved tutor text, in order and including sentence endings.

The replacement recording was verified on September 27, 2026:

- The real browser journey completed two learner answers, generated coaching, and saved review. Reloading the completed review preserved the assessment and did not request microphone access.
- The learner uses simpler wording and the slower Skylar synthetic voice. This take does not include a focused retry.
- All four tutor replies passed the exported-audio comparison. The first three matched every expected word; the coaching matched 97.4%, with “opened” transcribed as “open.” Every checked sentence ending was present.
- The 202.28-second MP4 passed full FFmpeg decoding. Audio/video alignment differed by 16 ms between the two learner speech anchors. Six frames covering selection, practice, coaching, and saved feedback were visually reviewed.
- No dialogue or waiting time was removed, and the export was not sped up.

The old cutoff's root cause was not conclusively established. A fresh browser probe captured a complete opening, and this replacement passed the content check. These results verify this recording; they do not establish that intermittent speech failures are resolved in the application.

## Original submission startup check

The selected submission files built and started in a separate Compose project on port 8083. Web, API, agent, and Redis were healthy, and the readiness endpoint returned `ready`. Existing dependency and model caches were available. All 121 runtime/configuration files compared with that built copy were unchanged during the recording work. The successful recording used the existing app on port 8080; its 32 backend Python source files matched the submission after normalizing line endings.

## Original submission archive

The submitted archive contained the application source, runtime assets and licenses, dependency locks, Compose configuration, tests, required documents, and the final walkthrough. It also included the written workflow records listed in the [documentation guide](../README.md). The design prototype and its assets, video-production tools, and raw recordings were excluded from the submitted working tree.

The archive retained the original Git history, including earlier planning documents. It was assembled in a separate local repository to preserve the source repository's branch and staging area during submission preparation. Credentials and generated environments were excluded from submitted files and container build context.

## Remaining limits

- Full-reply speech preparation adds waiting time. Response-latency percentiles have not been established.
- A speech-provider failure occurred during a discarded recording attempt. The successful take is not a reliability benchmark.
- Coaching quality, varied accents, physical microphones, acoustic echo, and the phone/browser matrix need human evaluation.
- Redis persistence is disabled; restarting Redis loses temporary history.
- Explicit **I wasn't finished** preserves the remaining answer allowance. Model-inferred continuation checks the combined time after capture and can therefore record beyond that allowance before rejecting it.
- The demo defaults to four active voice sessions. There is no 10,000-session load-test result; the [engineering notes](../engineering.md#scaling-to-10000-concurrent-sessions) describe proposed changes for that scale.
