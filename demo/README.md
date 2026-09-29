# Walkthrough

The 3:22 video shows the running application: choose a workplace situation, answer Alex, receive feedback on the words used, and reopen the saved takeaway.

The learner uses simple wording and a slower synthetic voice. Alex's replies, transcripts, and coaching are generated during the conversation. No personal learner recording is used.

This replaces the earlier recording with clipped speech. All four tutor replies passed a transcription comparison, including their sentence endings. The MP4 also passed full decoding, audio/video alignment, and a visual review. No dialogue or waiting time was cut, and playback was not sped up. Voice naturalness still needs human judgment.

## Try the flow yourself

1. Start the app with the root README's Docker Compose instructions.
2. Choose **Hosting a meeting → Welcome everyone**, read the situation, and start practice.
3. Let Alex finish. When **Your turn** appears, welcome the group in your own words.
4. Answer the next question, then listen to the coaching and inspect **Based on your words**.
5. Optionally try the suggestion in a focused retry.
6. Finish practice and reopen the saved feedback. Completed review does not request microphone access.

The app prepares complete replies before playback, which adds waiting time. Temporary history expires within 24 hours and is lost when Redis restarts. Physical phone microphones and echo behavior still need evaluation.

Video-production scripts and raw recordings are retained locally and excluded from the submitted working tree. They are not needed to run the app. See the [verification notes](../docs/verification/workplace-english-release-checks.md) for the recording checks and remaining limits.
