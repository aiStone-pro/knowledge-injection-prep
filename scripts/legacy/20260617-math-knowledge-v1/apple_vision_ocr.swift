import AppKit
import Foundation
import Vision

struct TextObservation: Codable {
  let text: String
  let confidence: Float
  let x: Double
  let y: Double
  let width: Double
  let height: Double
}

if CommandLine.arguments.count < 2 {
  fputs("usage: apple_vision_ocr.swift <image-path>\n", stderr)
  exit(2)
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
guard let image = NSImage(contentsOf: imageURL) else {
  fputs("failed to load image: \(imageURL.path)\n", stderr)
  exit(1)
}

var proposedRect = CGRect(origin: .zero, size: image.size)
guard let cgImage = image.cgImage(forProposedRect: &proposedRect, context: nil, hints: nil) else {
  fputs("failed to create CGImage: \(imageURL.path)\n", stderr)
  exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
if let supported = try? request.supportedRecognitionLanguages() {
  let preferred = ["zh-Hans", "zh-Hant", "en-US"].filter { supported.contains($0) }
  if !preferred.isEmpty {
    request.recognitionLanguages = preferred
  }
}
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
  try handler.perform([request])
} catch {
  fputs("vision OCR failed for \(imageURL.path): \(error)\n", stderr)
  exit(1)
}

let observations = (request.results ?? [])
  .compactMap { observation -> TextObservation? in
    guard let candidate = observation.topCandidates(1).first else {
      return nil
    }
    return TextObservation(
      text: candidate.string,
      confidence: candidate.confidence,
      x: observation.boundingBox.origin.x,
      y: observation.boundingBox.origin.y,
      width: observation.boundingBox.size.width,
      height: observation.boundingBox.size.height
    )
  }
  .sorted {
    let yDelta = abs($0.y - $1.y)
    if yDelta > 0.01 {
      return $0.y > $1.y
    }
    return $0.x < $1.x
  }

let encoder = JSONEncoder()
encoder.outputFormatting = [.withoutEscapingSlashes]
let data = try encoder.encode(observations)
FileHandle.standardOutput.write(data)
print("")
