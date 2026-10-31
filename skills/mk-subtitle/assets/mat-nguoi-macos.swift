// Khung mặt người trong ảnh bằng bộ nhận diện có sẵn của macOS (Vision, chạy trên máy, không gửi ảnh đi).
// Cách gọi: swift mat-nguoi-macos.swift <ảnh.png>… > mat.tsv
// Mỗi dòng: tên ảnh<TAB>x<TAB>y<TAB>w<TAB>h (tỉ lệ 0–1, gốc trên-trái); ảnh không có mặt: tên ảnh<TAB>NONE.
// Chỉ đọc ảnh; in ra stdout. Dùng cho: burn.py layout DIR --faces mat.tsv
import Foundation
import ImageIO
import Vision

if CommandLine.arguments.count < 2 {
    FileHandle.standardError.write("Cách gọi: swift mat-nguoi-macos.swift <ảnh.png>…\n".data(using: .utf8)!)
    exit(2)
}
for path in CommandLine.arguments.dropFirst() {
    let name = (path as NSString).lastPathComponent
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        FileHandle.standardError.write("Không đọc được ảnh \(path)\n".data(using: .utf8)!)
        exit(1)
    }
    let request = VNDetectFaceRectanglesRequest()
    try VNImageRequestHandler(cgImage: image).perform([request])
    let faces = (request.results ?? []).sorted { $0.boundingBox.minX < $1.boundingBox.minX }
    if faces.isEmpty { print("\(name)\tNONE") }
    for face in faces {
        let b = face.boundingBox  // Vision: gốc dưới-trái
        print(String(format: "%@\t%.3f\t%.3f\t%.3f\t%.3f", name, b.minX, 1 - b.maxY, b.width, b.height))
    }
}
