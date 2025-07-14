#!/bin/bash

# Check arguments
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <input.mp4> <start_seconds> <duration_seconds> <output.png>"
    echo "Example: $0 video.mp4 10.5 5 atlas.png"
    exit 1
fi

INPUT_VIDEO="$1"
START_TIME="$2"
DURATION="$3"
OUTPUT_IMAGE="$4"
COLUMNS=4

# Create video atlas directly with ffmpeg in one command
# This approach extracts and tiles frames in a single pass

# First, let's get the frame count to calculate proper dimensions
FRAME_COUNT=$(ffmpeg -ss "$START_TIME" -t "$DURATION" -i "$INPUT_VIDEO" -vcodec copy -f null - 2>&1 | grep -oP 'frame=\s*\K\d+' | tail -1)

# If frame count detection failed, estimate it
if [ -z "$FRAME_COUNT" ] || [ "$FRAME_COUNT" -eq 0 ]; then
    # Get fps and calculate
    FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$INPUT_VIDEO" | bc -l)
    FRAME_COUNT=$(echo "$FPS * $DURATION" | bc | cut -d. -f1)
fi

# Calculate rows
ROWS=$(( ($FRAME_COUNT + $COLUMNS - 1) / $COLUMNS ))

echo "Processing $DURATION seconds starting at ${START_TIME}s"
echo "Estimated frames: $FRAME_COUNT"
echo "Grid: ${COLUMNS}x${ROWS}"

# Create the atlas in one command with larger frame size
# Changed from 320 to 500 pixels wide (about 56% larger)
ffmpeg -ss "$START_TIME" -t "$DURATION" -i "$INPUT_VIDEO" \
    -vf "fps=fps=source_fps,scale=500:-1,tile=${COLUMNS}x${ROWS}:nb_frames=0:padding=2:margin=2" \
    -frames:v 1 "$OUTPUT_IMAGE" -y

if [ -f "$OUTPUT_IMAGE" ]; then
    # Calculate actual rows from output
    echo "Video atlas created: $OUTPUT_IMAGE"
    echo "Number of rows: $ROWS"
    # With 4 columns at 500px each + padding/margins, total width will be ~2000px
    echo "Approximate size: ${COLUMNS}x500px wide"
else
    echo "Error: Failed to create atlas"
    exit 1
fi