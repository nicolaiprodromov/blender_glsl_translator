#iChannel0 "file://assets/atlas.png"

// Function to get UV coordinates for a specific frame in the atlas
vec2 getFrameUV(vec2 uv, float frameNumber, float totalFrames, float framesPerRow) {
    // Calculate grid position
    float row = floor(frameNumber / framesPerRow);
    float col = mod(frameNumber, framesPerRow);
    
    // Calculate atlas dimensions
    float totalRows = ceil(totalFrames / framesPerRow);
    float frameWidth = 1.0 / framesPerRow;
    float frameHeight = 1.0 / totalRows;
    
    // Calculate UV for this frame
    // FLIP THE Y COORDINATE - atlas is likely stored bottom-to-top
    return vec2(
        col * frameWidth + uv.x * frameWidth,
        (totalRows - 1.0 - row) * frameHeight + uv.y * frameHeight  // Fixed: flip row
    );
}

// Function to calculate UV with proper aspect ratio
vec2 getAspectCorrectedUV(vec2 fragCoord, vec2 resolution, vec2 videoSize) {
    vec2 uv = fragCoord / resolution;
    
    // Calculate aspect ratios
    float screenAspect = resolution.x / resolution.y;
    float videoAspect = videoSize.x / videoSize.y;
    
    // Center the UV coordinates
    uv = (uv - 0.5);
    
    // Apply aspect ratio correction to fit video in screen
    if (screenAspect > videoAspect) {
        // Screen is wider than video - add pillarboxing (black bars on sides)
        uv.x *= screenAspect / videoAspect;
    } else {
        // Screen is taller than video - add letterboxing (black bars on top/bottom)
        uv.y *= videoAspect / screenAspect;
    }
    
    // Return to 0-1 range
    uv += 0.5;
    
    return uv;
}

// Function to sample video frame from atlas
vec4 sampleVideoAtlas(sampler2D atlas, vec2 fragCoord, vec2 resolution, float time, float totalFrames, float fps, vec2 videoSize) {
    const float framesPerRow = 4.0;
    
    // Get aspect-corrected UV
    vec2 uv = getAspectCorrectedUV(fragCoord, resolution, videoSize);
    
    // Return black for areas outside the video frame
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        return vec4(0.0, 0.0, 0.0, 1.0);
    }
    
    // Calculate current frame
    float currentFrame = floor(mod(time * fps, totalFrames));
    
    // Get UV coordinates for current frame in the atlas
    vec2 frameUV = getFrameUV(uv, currentFrame, totalFrames, framesPerRow);
    
    return texture(atlas, frameUV);
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    // Configuration
    float totalFrames = 72.0; // Change this to match your video's frame count
    float fps = 24.0; // Playback speed
    vec2 originalVideoSize = vec2(1920.0, 1080.0); // Original video resolution
    
    // Sample the video atlas
    fragColor = sampleVideoAtlas(iChannel0, fragCoord, iResolution.xy, iTime, totalFrames, fps, originalVideoSize);
}