#iChannel0 "sequence.frag"
#iChannel1 "dist_vid.frag"
#iChannel2 "tangent.frag"

uint wang_hash(uint seed) {
    seed = (seed ^ 61u) ^ (seed >> 16u);
    seed *= 9u;
    seed = seed ^ (seed >> 4u);
    seed *= 0x27d4eb2du;
    seed = seed ^ (seed >> 15u);
    return seed;
}

float wang_hash_float(vec2 pixelCoord, float seed) {
    uint x = uint(pixelCoord.x);
    uint y = uint(pixelCoord.y);
    uint s = uint(seed);
    uint hash = wang_hash(x + wang_hash(y + wang_hash(s)));
    return float(hash) / float(0xffffffffu);
}

float selectRandomPixels(vec2 fragCoord, float percentage, float seed) {
    vec2 pixelCoord = floor(fragCoord);
    float rand = wang_hash_float(pixelCoord, seed);
    return step(rand, percentage);
}

// Function to rotate a point around a center
vec2 rotatePoint(vec2 point, vec2 center, float angle) {
    vec2 translated = point - center;
    float cosA = cos(angle);
    float sinA = sin(angle);
    vec2 rotated = vec2(
        translated.x * cosA - translated.y * sinA,
        translated.x * sinA + translated.y * cosA
    );
    return rotated + center;
}

// Main function that creates enlarged pixels from randomly selected points
vec4 enlargeRandomPixels(
    vec2 fragCoord,           // Current fragment coordinate
    sampler2D sourceTexture,  // Texture to sample colors from
    sampler2D tangentTexture, // Texture containing tangent vectors
    vec2 resolution,          // Resolution of the screen
    vec2 pixelSize,           // Size of the enlarged pixels (width, height)
    float percentage,         // Percentage of pixels to select (0.0-1.0)
    float seed,              // Random seed
    vec4 backgroundColor     // Color to use for non-selected areas
) {
    // Start with background color
    vec4 outColor = backgroundColor;
    
    // Check a larger area to account for rotation
    float maxDim = max(pixelSize.x, pixelSize.y);
    vec2 searchRadius = vec2(maxDim * 1.5);
    
    // Search in a wider area around the current fragment
    vec2 searchStart = fragCoord - searchRadius;
    vec2 searchEnd = fragCoord + searchRadius;
    
    for(float y = searchStart.y; y <= searchEnd.y; y += 1.0) {
        for(float x = searchStart.x; x <= searchEnd.x; x += 1.0) {
            vec2 checkPos = vec2(x, y);
            
            // Make sure we're not checking outside the screen bounds
            if(checkPos.x < 0.0 || checkPos.x >= resolution.x || 
               checkPos.y < 0.0 || checkPos.y >= resolution.y) {
                continue;
            }
            
            // Check if this position was randomly selected
            float selected = selectRandomPixels(checkPos, percentage, seed);
            
            if(selected > 0.5) {
                // Get the tangent vector at this position
                vec2 tangentUV = checkPos / resolution;
                vec2 tangent = texture(tangentTexture, tangentUV).xy;
                
                // Normalize the tangent if it's not zero
                if(length(tangent) > 0.001) {
                    tangent = normalize(tangent);
                } else {
                    tangent = vec2(0.0, 1.0); // Default to vertical if no tangent
                }
                
                // Calculate the angle to rotate (align height with tangent direction)
                float angle = atan(tangent.x, tangent.y);
                
                // Check if the current fragment is within the rotated rectangle
                vec2 localPos = fragCoord - checkPos;
                vec2 rotatedPos = rotatePoint(fragCoord, checkPos, -angle);
                vec2 rectMin = checkPos - pixelSize * 0.5;
                vec2 rectMax = checkPos + pixelSize * 0.5;
                
                // Check if rotated position is within the rectangle bounds
                if(rotatedPos.x >= rectMin.x && rotatedPos.x <= rectMax.x &&
                   rotatedPos.y >= rectMin.y && rotatedPos.y <= rectMax.y) {
                    // Sample the color from the source texture at the original pixel position
                    vec4 sampledColor = texture(sourceTexture, tangentUV);
                    outColor = sampledColor;
                    return outColor;
                }
            }
        }
    }
    
    return outColor;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec4 originalColor = texture(iChannel0, uv);
    
    fragColor = enlargeRandomPixels(
        fragCoord,
        iChannel0,
        iChannel2,                    // Pass the tangent texture
        iResolution.xy,
        vec2(16.0, 32.0),            // Pixel size (width, height)
        0.001,
        iTime * 60.0,
        vec4(0.0)                 // Use original image as background
    );
}