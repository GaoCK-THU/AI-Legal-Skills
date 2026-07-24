#!/usr/bin/env swift

import AppKit
import AVFoundation
import Foundation

enum ToolError: Error, CustomStringConvertible {
    case message(String)

    var description: String {
        switch self {
        case .message(let text): return text
        }
    }
}

struct CLIArguments {
    let command: String
    var values: [String: [String]] = [:]
    var flags: Set<String> = []

    func value(_ name: String) throws -> String {
        guard let value = values[name]?.last else {
            throw ToolError.message("Missing required option: \(name)")
        }
        return value
    }

    func optionalValue(_ name: String) -> String? {
        values[name]?.last
    }

    func allValues(_ name: String) -> [String] {
        values[name] ?? []
    }
}

struct FrameRow {
    let id: String
    let sourceVideo: String
    let timecode: String
    let seconds: Double
    let filename: String
    let kind: String
}

let usage = """
Usage:
  video_frames.swift probe --video VIDEO
  video_frames.swift sample --video VIDEO --out-dir DIR [--start SEC] [--end SEC]
      [--interval SEC] [--max-width PX] [--format jpg|png] [--overwrite]
      [--make-overview] [--columns N] [--rows N] [--cell-width PX]
  video_frames.swift extract --video VIDEO --out-dir DIR --time SEC [--time SEC ...]
      [--format png|jpg] [--overwrite]
  video_frames.swift overview --manifest CSV --out-dir DIR [--columns N] [--rows N]
      [--cell-width PX] [--overwrite]

Outputs:
  sample   writes review frames and review_manifest.csv
  extract  writes original-resolution frames and extracted_frames.csv
  overview writes overview_001.jpg, overview_002.jpg, ...
"""

func parseCLI() throws -> CLIArguments {
    let raw = Array(CommandLine.arguments.dropFirst())
    guard let command = raw.first, ["probe", "sample", "extract", "overview"].contains(command) else {
        throw ToolError.message(usage)
    }

    let booleanFlags: Set<String> = ["--overwrite", "--make-overview"]
    var parsed = CLIArguments(command: command)
    var index = 1
    while index < raw.count {
        let token = raw[index]
        guard token.hasPrefix("--") else {
            throw ToolError.message("Unexpected argument: \(token)")
        }
        if booleanFlags.contains(token) {
            parsed.flags.insert(token)
            index += 1
            continue
        }
        guard index + 1 < raw.count, !raw[index + 1].hasPrefix("--") else {
            throw ToolError.message("Missing value for option: \(token)")
        }
        parsed.values[token, default: []].append(raw[index + 1])
        index += 2
    }
    return parsed
}

func parseDouble(_ text: String, option: String) throws -> Double {
    guard let value = Double(text), value.isFinite else {
        throw ToolError.message("Invalid number for \(option): \(text)")
    }
    return value
}

func parseInt(_ text: String, option: String) throws -> Int {
    guard let value = Int(text) else {
        throw ToolError.message("Invalid integer for \(option): \(text)")
    }
    return value
}

func checkedFile(_ path: String) throws -> URL {
    let url = URL(fileURLWithPath: path).standardizedFileURL
    var isDirectory: ObjCBool = false
    guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDirectory), !isDirectory.boolValue else {
        throw ToolError.message("Input file not found: \(url.path)")
    }
    return url
}

func checkedOutputDirectory(_ path: String) throws -> URL {
    let url = URL(fileURLWithPath: path).standardizedFileURL
    try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
    return url
}

func ensureMayWrite(_ url: URL, overwrite: Bool) throws {
    if FileManager.default.fileExists(atPath: url.path), !overwrite {
        throw ToolError.message("Output already exists; pass --overwrite to replace it: \(url.path)")
    }
}

func assetInfo(_ videoURL: URL) throws -> (asset: AVURLAsset, duration: Double, displaySize: CGSize, fps: Float) {
    let asset = AVURLAsset(url: videoURL)
    let duration = CMTimeGetSeconds(asset.duration)
    guard duration.isFinite, duration > 0 else {
        throw ToolError.message("Could not determine a positive video duration: \(videoURL.path)")
    }
    guard let track = asset.tracks(withMediaType: .video).first else {
        throw ToolError.message("No video track found: \(videoURL.path)")
    }
    let transformed = CGRect(origin: .zero, size: track.naturalSize).applying(track.preferredTransform)
    let size = CGSize(width: abs(transformed.width), height: abs(transformed.height))
    return (asset, duration, size, track.nominalFrameRate)
}

func formatTime(_ seconds: Double, filenameSafe: Bool = false) -> String {
    let totalMilliseconds = max(0, Int((seconds * 1000).rounded()))
    let hours = totalMilliseconds / 3_600_000
    let minutes = (totalMilliseconds / 60_000) % 60
    let secs = (totalMilliseconds / 1000) % 60
    let millis = totalMilliseconds % 1000
    let separator = filenameSafe ? "-" : ":"
    return String(format: "%02d%@%02d%@%02d.%03d", hours, separator, minutes, separator, secs, millis)
}

func imageData(_ image: CGImage, format: String) throws -> Data {
    let representation = NSBitmapImageRep(cgImage: image)
    switch format.lowercased() {
    case "jpg", "jpeg":
        guard let data = representation.representation(using: .jpeg, properties: [.compressionFactor: 0.88]) else {
            throw ToolError.message("Could not encode JPEG image")
        }
        return data
    case "png":
        guard let data = representation.representation(using: .png, properties: [:]) else {
            throw ToolError.message("Could not encode PNG image")
        }
        return data
    default:
        throw ToolError.message("Unsupported image format: \(format). Use jpg or png.")
    }
}

func csvEscape(_ value: String) -> String {
    if value.contains(",") || value.contains("\"") || value.contains("\n") || value.contains("\r") {
        return "\"" + value.replacingOccurrences(of: "\"", with: "\"\"") + "\""
    }
    return value
}

func writeFrameManifest(_ rows: [FrameRow], to url: URL, overwrite: Bool) throws {
    try ensureMayWrite(url, overwrite: overwrite)
    var lines = ["id,source_video,timecode,seconds,filename,kind"]
    for row in rows {
        lines.append([
            row.id,
            row.sourceVideo,
            row.timecode,
            String(format: "%.6f", row.seconds),
            row.filename,
            row.kind,
        ].map(csvEscape).joined(separator: ","))
    }
    try (lines.joined(separator: "\n") + "\n").write(to: url, atomically: true, encoding: .utf8)
}

func makeGenerator(asset: AVAsset, maxWidth: Int?) throws -> AVAssetImageGenerator {
    let generator = AVAssetImageGenerator(asset: asset)
    generator.appliesPreferredTrackTransform = true
    generator.requestedTimeToleranceBefore = .zero
    generator.requestedTimeToleranceAfter = .zero

    if let maxWidth {
        guard maxWidth > 0 else { throw ToolError.message("--max-width must be greater than zero") }
        guard let track = asset.tracks(withMediaType: .video).first else {
            throw ToolError.message("No video track found")
        }
        let transformed = CGRect(origin: .zero, size: track.naturalSize).applying(track.preferredTransform)
        let displayWidth = max(1, abs(transformed.width))
        let displayHeight = max(1, abs(transformed.height))
        let scale = CGFloat(maxWidth) / displayWidth
        generator.maximumSize = CGSize(width: CGFloat(maxWidth), height: ceil(displayHeight * scale))
    }
    return generator
}

func captureFrame(generator: AVAssetImageGenerator, at seconds: Double) throws -> (CGImage, Double) {
    var actualTime = CMTime.invalid
    let requestedTime = CMTime(seconds: seconds, preferredTimescale: 6000)
    let image = try generator.copyCGImage(at: requestedTime, actualTime: &actualTime)
    let actualSeconds = CMTimeGetSeconds(actualTime)
    return (image, actualSeconds.isFinite ? actualSeconds : seconds)
}

func runProbe(_ cli: CLIArguments) throws {
    let videoURL = try checkedFile(cli.value("--video"))
    let info = try assetInfo(videoURL)
    let object: [String: Any] = [
        "source_video": videoURL.path,
        "duration_seconds": info.duration,
        "width": Int(info.displaySize.width.rounded()),
        "height": Int(info.displaySize.height.rounded()),
        "nominal_fps": info.fps,
    ]
    let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
    print(String(decoding: data, as: UTF8.self))
}

func runSample(_ cli: CLIArguments) throws {
    let videoURL = try checkedFile(cli.value("--video"))
    let outputDirectory = try checkedOutputDirectory(cli.value("--out-dir"))
    let info = try assetInfo(videoURL)
    let start = try parseDouble(cli.optionalValue("--start") ?? "0", option: "--start")
    let end = try parseDouble(cli.optionalValue("--end") ?? String(info.duration), option: "--end")
    let interval = try parseDouble(cli.optionalValue("--interval") ?? "1", option: "--interval")
    let maxWidth = try parseInt(cli.optionalValue("--max-width") ?? "480", option: "--max-width")
    let format = (cli.optionalValue("--format") ?? "jpg").lowercased()
    let overwrite = cli.flags.contains("--overwrite")

    guard start >= 0, start < info.duration else { throw ToolError.message("--start must fall within the video") }
    guard end > start, end <= info.duration + 0.001 else { throw ToolError.message("--end must be after --start and within the video") }
    guard interval > 0 else { throw ToolError.message("--interval must be greater than zero") }

    let manifestURL = outputDirectory.appendingPathComponent("review_manifest.csv")
    try ensureMayWrite(manifestURL, overwrite: overwrite)
    let generator = try makeGenerator(asset: info.asset, maxWidth: maxWidth)
    var rows: [FrameRow] = []
    var requested = start
    var index = 1

    while requested < end - 0.000_001 {
        let (image, actualSeconds) = try captureFrame(generator: generator, at: requested)
        let id = String(format: "R%04d", index)
        let ext = format == "jpeg" ? "jpg" : format
        let filename = "\(id)_\(formatTime(actualSeconds, filenameSafe: true)).\(ext)"
        let fileURL = outputDirectory.appendingPathComponent(filename)
        try ensureMayWrite(fileURL, overwrite: overwrite)
        try imageData(image, format: format).write(to: fileURL, options: .atomic)
        rows.append(FrameRow(
            id: id,
            sourceVideo: videoURL.lastPathComponent,
            timecode: formatTime(actualSeconds),
            seconds: actualSeconds,
            filename: filename,
            kind: "review"
        ))
        requested += interval
        index += 1
    }

    guard !rows.isEmpty else { throw ToolError.message("No review frames were extracted") }
    try writeFrameManifest(rows, to: manifestURL, overwrite: overwrite)
    print("Wrote \(rows.count) review frames and \(manifestURL.path)")

    if cli.flags.contains("--make-overview") {
        try buildOverview(
            manifestURL: manifestURL,
            outputDirectory: outputDirectory,
            columns: try parseInt(cli.optionalValue("--columns") ?? "4", option: "--columns"),
            rowsPerPage: try parseInt(cli.optionalValue("--rows") ?? "5", option: "--rows"),
            cellWidth: try parseInt(cli.optionalValue("--cell-width") ?? "320", option: "--cell-width"),
            overwrite: overwrite
        )
    }
}

func runExtract(_ cli: CLIArguments) throws {
    let videoURL = try checkedFile(cli.value("--video"))
    let outputDirectory = try checkedOutputDirectory(cli.value("--out-dir"))
    let timeValues = cli.allValues("--time")
    guard !timeValues.isEmpty else { throw ToolError.message("Provide at least one --time value") }
    let format = (cli.optionalValue("--format") ?? "png").lowercased()
    let overwrite = cli.flags.contains("--overwrite")
    let info = try assetInfo(videoURL)
    let generator = try makeGenerator(asset: info.asset, maxWidth: nil)
    let manifestURL = outputDirectory.appendingPathComponent("extracted_frames.csv")
    try ensureMayWrite(manifestURL, overwrite: overwrite)
    var rows: [FrameRow] = []

    for (offset, text) in timeValues.enumerated() {
        let requested = try parseDouble(text, option: "--time")
        guard requested >= 0, requested < info.duration else {
            throw ToolError.message("--time must fall within the video: \(text)")
        }
        let (image, actualSeconds) = try captureFrame(generator: generator, at: requested)
        let id = String(format: "S%04d", offset + 1)
        let ext = format == "jpeg" ? "jpg" : format
        let filename = "\(id)_\(formatTime(actualSeconds, filenameSafe: true)).\(ext)"
        let fileURL = outputDirectory.appendingPathComponent(filename)
        try ensureMayWrite(fileURL, overwrite: overwrite)
        try imageData(image, format: format).write(to: fileURL, options: .atomic)
        rows.append(FrameRow(
            id: id,
            sourceVideo: videoURL.lastPathComponent,
            timecode: formatTime(actualSeconds),
            seconds: actualSeconds,
            filename: filename,
            kind: "full_resolution"
        ))
    }

    try writeFrameManifest(rows, to: manifestURL, overwrite: overwrite)
    print("Wrote \(rows.count) full-resolution frames and \(manifestURL.path)")
}

func parseCSVLine(_ line: String) -> [String] {
    let characters = Array(line)
    var fields: [String] = []
    var current = ""
    var quoted = false
    var index = 0
    while index < characters.count {
        let character = characters[index]
        if character == "\"" {
            if quoted, index + 1 < characters.count, characters[index + 1] == "\"" {
                current.append("\"")
                index += 2
                continue
            }
            quoted.toggle()
        } else if character == ",", !quoted {
            fields.append(current)
            current = ""
        } else {
            current.append(character)
        }
        index += 1
    }
    fields.append(current)
    return fields
}

func readManifest(_ url: URL) throws -> [[String: String]] {
    let content = try String(contentsOf: url, encoding: .utf8)
    let lines = content.split(whereSeparator: \.isNewline).map(String.init)
    guard let headerLine = lines.first else { throw ToolError.message("Manifest is empty: \(url.path)") }
    let headers = parseCSVLine(headerLine)
    guard headers.contains("id"), headers.contains("timecode"), headers.contains("filename") else {
        throw ToolError.message("Manifest must contain id, timecode, and filename columns")
    }
    return lines.dropFirst().map { line in
        let values = parseCSVLine(line)
        return Dictionary(uniqueKeysWithValues: headers.enumerated().map { index, header in
            (header, index < values.count ? values[index] : "")
        })
    }
}

func cgImage(at url: URL) throws -> CGImage {
    let data = try Data(contentsOf: url)
    guard let representation = NSBitmapImageRep(data: data), let image = representation.cgImage else {
        throw ToolError.message("Could not read image: \(url.path)")
    }
    return image
}

func buildOverview(
    manifestURL: URL,
    outputDirectory: URL,
    columns: Int,
    rowsPerPage: Int,
    cellWidth: Int,
    overwrite: Bool
) throws {
    guard columns > 0, rowsPerPage > 0, cellWidth >= 120 else {
        throw ToolError.message("Overview columns/rows must be positive and cell width must be at least 120")
    }
    let entries = try readManifest(manifestURL)
    guard !entries.isEmpty else { throw ToolError.message("Manifest contains no frame rows") }

    let padding = 12
    let labelHeight = 30
    let pageCapacity = columns * rowsPerPage
    let pageCount = Int(ceil(Double(entries.count) / Double(pageCapacity)))
    let paragraphStyle = NSMutableParagraphStyle()
    paragraphStyle.alignment = .center
    let attributes: [NSAttributedString.Key: Any] = [
        .font: NSFont.monospacedSystemFont(ofSize: 16, weight: .medium),
        .foregroundColor: NSColor.black,
        .paragraphStyle: paragraphStyle,
    ]

    for pageIndex in 0..<pageCount {
        let pageEntries = Array(entries.dropFirst(pageIndex * pageCapacity).prefix(pageCapacity))
        let pageImages: [CGImage] = try pageEntries.map { entry in
            guard let filename = entry["filename"] else {
                throw ToolError.message("Manifest row is missing filename")
            }
            return try cgImage(at: manifestURL.deletingLastPathComponent().appendingPathComponent(filename))
        }
        let imageAreaHeight = max(1, pageImages.map { image in
            Int((Double(image.height) * Double(cellWidth) / Double(image.width)).rounded())
        }.max() ?? cellWidth)
        let cellHeight = labelHeight + imageAreaHeight + padding
        let usedRows = Int(ceil(Double(pageEntries.count) / Double(columns)))
        let canvasWidth = padding + columns * (cellWidth + padding)
        let canvasHeight = padding + usedRows * (cellHeight + padding)
        guard let bitmap = NSBitmapImageRep(
            bitmapDataPlanes: nil,
            pixelsWide: canvasWidth,
            pixelsHigh: canvasHeight,
            bitsPerSample: 8,
            samplesPerPixel: 4,
            hasAlpha: true,
            isPlanar: false,
            colorSpaceName: .deviceRGB,
            bytesPerRow: 0,
            bitsPerPixel: 32
        ) else {
            throw ToolError.message("Could not allocate overview bitmap")
        }
        guard let context = NSGraphicsContext(bitmapImageRep: bitmap) else {
            throw ToolError.message("Could not create overview graphics context")
        }

        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = context
        NSColor.white.setFill()
        NSRect(x: 0, y: 0, width: canvasWidth, height: canvasHeight).fill()

        for (localIndex, entry) in pageEntries.enumerated() {
            guard let id = entry["id"], let timecode = entry["timecode"] else {
                throw ToolError.message("Manifest row is missing id, timecode, or filename")
            }
            let image = pageImages[localIndex]
            let column = localIndex % columns
            let row = localIndex / columns
            let cellX = padding + column * (cellWidth + padding)
            let cellTop = canvasHeight - padding - row * (cellHeight + padding)
            let scale = min(Double(cellWidth) / Double(image.width), Double(imageAreaHeight) / Double(image.height))
            let drawWidth = max(1, Int((Double(image.width) * scale).rounded()))
            let drawHeight = max(1, Int((Double(image.height) * scale).rounded()))
            let drawX = cellX + (cellWidth - drawWidth) / 2
            let imageAreaBottom = cellTop - labelHeight - imageAreaHeight
            let drawY = imageAreaBottom + (imageAreaHeight - drawHeight) / 2

            context.cgContext.draw(image, in: CGRect(x: drawX, y: drawY, width: drawWidth, height: drawHeight))
            let label = "\(id)  \(timecode)" as NSString
            label.draw(
                in: NSRect(x: cellX, y: cellTop - labelHeight, width: cellWidth, height: labelHeight),
                withAttributes: attributes
            )
        }

        NSGraphicsContext.restoreGraphicsState()
        guard let data = bitmap.representation(using: .jpeg, properties: [.compressionFactor: 0.9]) else {
            throw ToolError.message("Could not encode overview JPEG")
        }
        let outputURL = outputDirectory.appendingPathComponent(String(format: "overview_%03d.jpg", pageIndex + 1))
        try ensureMayWrite(outputURL, overwrite: overwrite)
        try data.write(to: outputURL, options: .atomic)
        print("Wrote \(outputURL.path)")
    }
}

func runOverview(_ cli: CLIArguments) throws {
    let manifestURL = try checkedFile(cli.value("--manifest"))
    let outputDirectory = try checkedOutputDirectory(cli.value("--out-dir"))
    try buildOverview(
        manifestURL: manifestURL,
        outputDirectory: outputDirectory,
        columns: try parseInt(cli.optionalValue("--columns") ?? "4", option: "--columns"),
        rowsPerPage: try parseInt(cli.optionalValue("--rows") ?? "5", option: "--rows"),
        cellWidth: try parseInt(cli.optionalValue("--cell-width") ?? "320", option: "--cell-width"),
        overwrite: cli.flags.contains("--overwrite")
    )
}

do {
    let cli = try parseCLI()
    switch cli.command {
    case "probe": try runProbe(cli)
    case "sample": try runSample(cli)
    case "extract": try runExtract(cli)
    case "overview": try runOverview(cli)
    default: throw ToolError.message(usage)
    }
} catch {
    fputs("Error: \(error)\n", stderr)
    exit(1)
}
