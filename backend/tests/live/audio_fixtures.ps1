# Non-personal learner fixtures generated entirely in RAM; never use a physical microphone.
Add-Type -AssemblyName System.Speech
$fixtureVoice = [System.Speech.Synthesis.SpeechSynthesizer]::new()
$englishVoice = $fixtureVoice.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq 'en' } | Select-Object -First 1
if (-not $englishVoice) { throw 'An installed English Windows speech voice is required.' }
$fixtureVoice.SelectVoice($englishVoice.VoiceInfo.Name)
$fixtureVoice.Rate = -1
$fixtureFormat = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(24000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$fixturePhrases = [ordered]@{
    welcome = "Good morning, everyone. Thank you for joining our meeting today. I'm Sam and I'll be hosting. Before we begin, let's quickly introduce ourselves."
    goal = "Welcome, everyone. I appreciate you making the time. Today we'll agree on owners and deadlines, so let's get started with a quick round of introductions."
    brief = 'The update is ready. I have sent the files. The report has the details.'
    agenda = 'The report covers June and July. The numbers are in the spreadsheet, and the chart shows the totals for both months.'
    coaching_question = 'Could you explain why that wording sounds more natural?'
    long_answer = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'long_answer.txt') -Raw
}
$fixtureResult = @{}
try {
    foreach ($fixtureName in $fixturePhrases.Keys) {
        $fixtureStream = [System.IO.MemoryStream]::new()
        try {
            $fixtureVoice.SetOutputToAudioStream($fixtureStream, $fixtureFormat)
            $fixtureVoice.Speak($fixturePhrases[$fixtureName])
            $fixtureVoice.SetOutputToNull()
            $fixtureResult[$fixtureName] = [Convert]::ToBase64String($fixtureStream.ToArray())
        } finally { $fixtureStream.Dispose() }
    }
    $fixtureResult | ConvertTo-Json -Compress
} finally { $fixtureVoice.Dispose() }
