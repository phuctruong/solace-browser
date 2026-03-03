#!/bin/bash
# marketing/scripts/make-gif.sh — Generate animated GIF from screenshot sequence
# Usage: ./marketing/scripts/make-gif.sh <input_dir_or_glob> <output_name> [delay_centiseconds]
# Example: ./marketing/scripts/make-gif.sh marketing/frames/home /home-walkthrough 80

set -e

INPUT="$1"
NAME="$2"
DELAY="${3:-80}"  # centiseconds between frames (80 = ~12fps)

if [ -z "$INPUT" ] || [ -z "$NAME" ]; then
  echo "Usage: $0 <input_dir> <output_name> [delay]"
  exit 1
fi

OUTDIR="$(dirname "$(realpath "$0")")/../gifs"
mkdir -p "$OUTDIR"
OUTPUT="$OUTDIR/$NAME.gif"

if [ -d "$INPUT" ]; then
  FILES=("$INPUT"/*.png)
else
  FILES=($INPUT)
fi

echo "Creating GIF from ${#FILES[@]} frames..."
convert -delay "$DELAY" -loop 0 "${FILES[@]}" \
  -coalesce \
  -layers optimize-frame \
  -fuzz 2% \
  "$OUTPUT"

SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo "✓ $OUTPUT ($SIZE)"
echo "  Frames: ${#FILES[@]}"
echo "  Delay:  ${DELAY}cs ($(echo "scale=1; 100/$DELAY" | bc)fps)"
