#!/bin/bash
# Convert all MP4 audio files from NotebookLM to MP3 for podcast distribution.
# Writes MP3 alongside the MP4 in the same folder.
# Usage: ./convert_to_mp3.sh [data/audio]

set -euo pipefail
AUDIO_DIR="${1:-$(dirname "$0")/../data/audio}"
AUDIO_DIR="$(cd "$AUDIO_DIR" && pwd)"

echo "Converting MP4 → MP3 in $AUDIO_DIR"
count=0

find "$AUDIO_DIR" -name "*.mp4" | sort | while read -r mp4; do
    mp3="${mp4%.mp4}.mp3"
    if [ -f "$mp3" ]; then
        echo "  SKIP (exists): $(basename "$mp3")"
        continue
    fi
    echo "  Converting: $(basename "$mp4")"
    ffmpeg -i "$mp4" \
        -vn \
        -acodec libmp3lame \
        -q:a 2 \
        -ar 44100 \
        -ac 2 \
        "$mp3" -y -loglevel error
    echo "  Done: $(basename "$mp3") ($(du -h "$mp3" | cut -f1))"
    count=$((count + 1))
done

echo "Conversion complete."
