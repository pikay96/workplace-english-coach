# Intermittent Alex audio: diagnostic findings

Updated: 2026-09-27. Status: **stream starvation reproduced and isolated from playback by complete-reply buffering**. The upstream delivery bottleneck remains unidentified.

### Demo voice revision

The user subsequently found Daniel too sleepy. The current default is **Parker**
(`30894953-bcce-41fe-892c-15ce19c843ff`), at the
preferred 0.8× pace. [Cartesia's voice guide](https://docs.cartesia.ai/build-with-cartesia/capability-guides/choosing-a-voice)
lists Parker among its stable English voices; the public catalog describes a
warm, conversational American voice. The live Inference route accepted Parker. Although the public docs list emotion
control, this deployment rejected both `confident` and `neutral` as invalid
emotions. No emotion parameter is sent; Parker uses his natural delivery.
Speed remains synthesis guidance rather than a guarantee of perceived energy. Full-reply buffering and alternating
turns remain unchanged. The demo learner now uses Jacqueline through the same
Inference route, replacing Windows speech synthesis; all recorded waits remain.
The earlier Daniel measurements below are historical, not Parker measurements.

### Voice articulation update

The learner confirmed playback is now smooth. After comparing 0.7× and 0.8×,
they preferred 0.8× and requested clearer articulation instead of a further
speed reduction. The first articulation revision selected **Daniel**
(`47c38ca4-5f35-497b-b1a3-415245fb35e1`) at 0.8×, replacing Blake.
[Cartesia's selection guide](https://docs.cartesia.ai/build-with-cartesia/capability-guides/choosing-a-voice)
lists Daniel among its stable English voices. The
[public voice catalog](https://creativeclaw.co/voices/) maps that ID to Daniel
and describes him as a clear, crisp American voice for assistants and instruction.
An actual LiveKit Inference call accepted the ID and generated the fixed
workplace sample in `backend/tests/live/preview_voice.py` (15.093 seconds).
This establishes compatibility, not a listening judgment: the generated sample
is provided for the learner to assess. Buffering and turn-taking were not changed.

The real browser audition completed the question before opening capture. Its
amplitude-based silence check recorded a 1.001-second quiet interval and failed
the old 750 ms threshold. Inspection of the separately generated preview found
encoded internal sentence pauses of 0.78–2.08 seconds. Amplitude alone cannot
distinguish a source pause from a delivery gap, so the browser test now reports
that measurement without treating it as a continuity verdict. The dedicated
application-delivery diagnostic and delayed-chunk regressions remain the
continuity checks; the browser still asserts audible output, completed delivery,
and microphone ordering.

The rerun passed with 286 audible observations and a largest quiet interval of
540 ms; Alex completed the opening question before the microphone became live.
The deployed Daniel delivery diagnostic also passed: 10.196 seconds to prepare
5.155 seconds of audio, then zero delivery gaps. Five speech/HTTP contract tests
passed. These checks validate delivery and turn order, not perceived articulation.

Subsequent user correction: Alex now finishes playback before learner capture
opens. Speech-triggered interruption was removed and checked with real browser
audio; see the [checkpoint update](workplace-english-milestone-2-checkpoint.md#turn-taking-correction-after-the-checkpoint).
The incoming-stream starvation measured here is a separate issue. The September 27
fix below prevents it from creating gaps during playback.

The incoming speech stream supplies PCM slower than real-time playback. The
original application forwarded those chunks immediately, so its player ran out of audio
and resumes when the next chunk arrives. This reproduces without browser
playback or microphone capture. Speakers may separately trigger interruption,
but are not necessary for the measured failure.

## Measurements

These are individual diagnostic observations, not latency percentiles. All
calls used fixed non-personal text through LiveKit Inference. No generated audio
was written to disk. Gap means time when previously received PCM would already
have finished playing; it excludes initial startup delay and encoded silence.

| Probe | First PCM | Entire stream | PCM duration | Largest delivery gap |
| --- | ---: | ---: | ---: | ---: |
| Configured Cartesia Sonic 3, Docker, 24 kHz, three sentences | 2.131 s | 15.391 s | 3.762 s | 2.038 s |
| Configured Cartesia Sonic 3, Windows host, 24 kHz, short greeting | 3.375 s | 10.109 s | 1.207 s | 2.832 s |
| Comparison Sonic 3.5, Docker, 24 kHz, short greeting | 7.038 s | 12.629 s | 1.120 s | 2.071 s |
| Configured Sonic 3, Docker, 8 kHz, short greeting | 7.720 s | 8.908 s | 1.161 s | 0.908 s |
| Comparison Deepgram Aura 2, Docker, 24 kHz, short greeting | 2.955 s | 9.052 s | 1.400 s | 2.159 s |

A separate short-greeting probe traced SDK WebSocket receipt times and yielded
frame times. Frames were emitted within approximately 1 ms of the relevant
incoming audio message. Incoming audio messages themselves were separated by
up to 2.328 seconds. The configured 24 kHz, mono PCM16 format matches the
adapter and downstream playback configuration in the installed SDK.

This rules out Docker, browser playback, and the microphone as necessary causes
of this reproduced starvation. It also shows that changing only the speech
model is not an established remedy. The measurements locate delay upstream of
local frame processing; they do **not** distinguish the local network path,
LiveKit gateway, or underlying provider as the ultimate cause.

## Repeatable check

From the repository root in PowerShell, with Compose running:

```powershell
Get-Content backend/tests/live/check_speech_continuity.py |
    docker compose exec -T api python -
```

This makes one billable TTS call using the application adapter and exits nonzero
if audio delivery has a gap above 500 ms, produces no audio, or fails. It emits
timings and exception types only. It does not record learner speech or contact
conversation/STT/assessment models. With buffering enabled, first-frame latency
includes complete synthesis; delivery gaps describe the application's output,
not the timing of raw provider chunks.

## September 27 fix and verification

Before the fix, four current-speed (0.8×) fixture calls produced largest delivery
gaps of 452, 189, 185, and 667 ms. The failing call delivered 5.480 seconds of PCM
over 13.515 seconds. This reproduced without a browser or microphone.

`Inference.speech` now collects the entire synthesis in memory before yielding
audio to live practice or HTTP playback. First provider audio retains its
eight-second deadline; full synthesis has a sixty-second deadline and a
4.32 MB PCM limit (ninety seconds at 24 kHz mono PCM16). An incomplete or failed
synthesis plays no partial audio. Cancellation closes the synthesis client.
No audio cache or recording is written to disk.

The HTTP player additionally waits for the explicit successful terminator, then
plays one bounded AudioBuffer. This also prevents network chunk gaps between
the API and browser from reaching playback. Stop still cancels playback.
During preparation the live UI says **Alex is getting ready**; microphone capture
stays closed until playback completes and **Your turn** appears.

The original application diagnostic passed after the fix: 4.836 seconds to
prepare 5.294 seconds of audio, then zero delivery gaps. A real Edge/WebRTC
opening produced 256 audible samples at a 20 ms observation interval, with a
largest quiet gap of 100 ms. The browser verified that the microphone was off
initially, the opening was fully played, no learner answer had been created,
and capture opened afterward. Quiet gaps include encoded pauses and scheduling;
they are different from the PCM-availability gaps in the provider diagnostic.
The second real browser test also passed: speech during Alex's turn was ignored,
Pause stopped output, Resume replayed the question, and manual answer submission
led to the next completed reply. Six portrait/history browser checks passed.

Regression tests cover delayed chunks, a failure after the first provider
chunk, cancellation, and pausing while audio is being prepared. The HTTP test
also verifies that neither incomplete nor failed responses begin playback.

The opening-only real-model check (`backend/tests/live/check_openings.py`)
initially reproduced four instruction-only openings among twelve checks. After
updating the directions and validating the question, all nine purposes and
three focused retries ended in one question. Workplace roles remain unchanged;
casual conversation begins with Alex asking so the learner can answer and ask back.

## Remediation boundaries

Run the same check from a different network or a worker hosted near the speech
service to isolate the delivery path. Hosting the voice worker remotely can
keep PCM synthesis traffic close to the service while the browser continues to
use LiveKit WebRTC. Repeat measurements before claiming that hosting solves it.

A small jitter buffer can absorb brief timing variation but cannot sustain a
stream arriving persistently slower than playback. Buffering the entire reply
avoids these mid-reply stalls at the cost of waiting for the whole synthesis
before speaking. On the measured connection that can add many seconds to startup.
Complete-reply buffering is now implemented. The provider, 24 kHz sample rate,
0.8× speed, and no-interruption rule are preserved. The startup-delay tradeoff
has not been evaluated against release latency targets.

Existing microphone echo cancellation is enabled. A physical-speaker versus
headphone comparison is still needed to check acoustic behavior. The implemented
alternating-turn rule disables capture throughout Alex's playback, including gaps,
so learner speech is no longer an authorized interruption path. These synthetic
stream measurements cannot validate physical devices.

The milestone 4 HTTP player uses explicit end/error frames so upstream truncation
does not look like successful playback. Complete-reply buffering now isolates
playback from the measured stream starvation. See the [current checkpoint](workplace-english-milestone-4-checkpoint.md).
