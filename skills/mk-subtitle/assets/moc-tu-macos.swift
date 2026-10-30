// Mốc từng từ bằng bộ đọc chính tả tiếng Việt có sẵn của macOS 26 (chạy trên máy, không gửi âm thanh đi).
// Cách gọi: swift moc-tu-macos.swift <audio.wav> > words.tsv   → mỗi dòng: bắt_đầu<TAB>kết_thúc<TAB>chữ (giây)
// Chỉ đọc file âm thanh; in ra stdout. Lần đầu macOS có thể tự tải dữ liệu nhận giọng tiếng Việt.
import AVFoundation
import Speech

guard CommandLine.arguments.count == 2 else {
    FileHandle.standardError.write("Cách gọi: swift moc-tu-macos.swift <audio.wav>\n".data(using: .utf8)!)
    exit(2)
}
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let transcriber = DictationTranscriber(locale: Locale(identifier: "vi-VN"), preset: .timeIndexedLongDictation)
if let request = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
    try await request.downloadAndInstall()
}
let analyzer = SpeechAnalyzer(modules: [transcriber])
let file = try AVAudioFile(forReading: url)
let collector = Task { () -> [String] in
    var rows: [String] = []
    for try await result in transcriber.results where result.isFinal {
        for run in result.text.runs {
            guard let range = run.audioTimeRange else { continue }
            let word = String(result.text[run.range].characters).trimmingCharacters(in: .whitespaces)
            if !word.isEmpty {
                rows.append(String(format: "%.2f\t%.2f\t%@", range.start.seconds, range.end.seconds, word))
            }
        }
    }
    return rows
}
if let last = try await analyzer.analyzeSequence(from: file) {
    try await analyzer.finalizeAndFinish(through: last)
} else {
    await analyzer.cancelAndFinishNow()
}
for row in try await collector.value { print(row) }
