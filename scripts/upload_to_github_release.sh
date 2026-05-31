#!/bin/bash
# Upload MP3 files to a GitHub Release so they are publicly accessible.
# The release URLs become the base-url for the podcast RSS feed.
#
# Prerequisites:
#   gh auth login (already done)
#   gh repo create <user>/<repo> --public (if not exists)
#
# Usage:
#   ./upload_to_github_release.sh <github-repo> <tag> [audio-dir]
#
# Example:
#   ./upload_to_github_release.sh rahuldev3160/ies-2026-audio ies-2026-v1 data/audio

set -euo pipefail

REPO="${1:?Usage: $0 <user/repo> <tag> [audio-dir]}"
TAG="${2:?Usage: $0 <user/repo> <tag> [audio-dir]}"
AUDIO_DIR="${3:-$(dirname "$0")/../data/audio}"
AUDIO_DIR="$(cd "$AUDIO_DIR" && pwd)"

RELEASE_TITLE="IES 2026 General Economics Audio Podcast — ${TAG}"
RELEASE_NOTES="AI-generated deep-dive podcast covering IES General Economics GE-01 to GE-04.
19 episodes across 4 papers, each targeting a specific topic cluster at DSE/JNU masters level.
Generated using NotebookLM with structured IES past-year questions and model answers as sources."

echo "=== GitHub Release Upload ==="
echo "Repo:      $REPO"
echo "Tag:       $TAG"
echo "Audio dir: $AUDIO_DIR"
echo ""

# Create release if it doesn't exist
if gh release view "$TAG" --repo "$REPO" &>/dev/null; then
    echo "Release $TAG already exists — uploading to it."
else
    echo "Creating release $TAG..."
    gh release create "$TAG" \
        --repo "$REPO" \
        --title "$RELEASE_TITLE" \
        --notes "$RELEASE_NOTES" \
        --latest
fi

# Upload all MP3 files
echo "Uploading MP3 files..."
find "$AUDIO_DIR" -name "*.mp3" | sort | while read -r mp3; do
    filename="$(basename "$mp3")"
    echo "  Uploading: $filename"
    gh release upload "$TAG" "$mp3" \
        --repo "$REPO" \
        --clobber
    echo "  Done: https://github.com/${REPO}/releases/download/${TAG}/${filename}"
done

BASE_URL="https://github.com/${REPO}/releases/download/${TAG}"
echo ""
echo "All files uploaded."
echo "Base URL for RSS feed: $BASE_URL"
echo ""
echo "Next step — generate RSS feed:"
echo "  python3 scripts/generate_podcast_rss.py \\"
echo "    --base-url '$BASE_URL' \\"
echo "    --output docs/podcast.xml"
