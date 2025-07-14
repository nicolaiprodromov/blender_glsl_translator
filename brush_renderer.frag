#iChannel0 "brush.frag"
#iChannel1 "tangent.frag"
#iChannel2 "sequence.frag"
#include "sdf/sdf_shapes.glsl"

// Mouse effect parameters
const float MOUSE_EFFECT_RADIUS = 800.0;  // Radius of mouse influence in pixels
const float MIN_BRUSH_WIDTH = 20.0;        // Minimum brush width
const float MAX_BRUSH_WIDTH = 120.0;       // Maximum brush width  
const float MIN_BRUSH_HEIGHT = 20.0;       // Minimum brush height
const float MAX_BRUSH_HEIGHT = 60.0;      // Maximum brush height
const float MIN_DENSITY = .1;            // Minimum density (0-1)
const float MAX_DENSITY = 1.0;            // Maximum density (0-1)
const int BASE_STROKES_PER_FRAME = 700;  // Base number of strokes

// PCG-inspired hash function - much better distribution
float hash(float n) {
    // Multiple rounds of mixing for better randomness
    n = fract(n * 0.1031);
    n *= n + 33.33;
    n *= n + n;
    return fract(n);
}

// Improved 2D hash with better mixing
vec2 hash2D(float n) {
    // Generate two independent values with good distribution
    float n2 = n * 127.1;
    return fract(vec2(
        sin(n) * 43758.5453123,
        sin(n2) * 22578.1459123
    ));
}

// Additional mixing function to break up patterns
float mixHash(float a, float b) {
    return hash(a * 73.1 + b * 179.3);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    
    // Start with transparent black
    fragColor = vec4(0.0);
    
    // Get mouse position
    vec2 mousePos = iMouse.xy;
    
    // Pre-compute inverse resolution for faster math
    vec2 invRes = 1.0 / iResolution.xy;
    
    // Loop through all strokes for this frame
    for(int strokeIndex = 0; strokeIndex < BASE_STROKES_PER_FRAME; strokeIndex++) {
        // Ultra early out - skip if we're already mostly opaque
        if(fragColor.a > 0.95) break;
        
        // IMPROVED: Better seed generation with multiple mixing steps
        float frameSeed = float(iFrame);
        float strokeFloat = float(strokeIndex);
        
        // Mix frame and stroke index with prime multipliers to avoid patterns
        float seed1 = mixHash(frameSeed * 0.7919, strokeFloat * 1.3733);
        float seed2 = mixHash(frameSeed * 2.2817, strokeFloat * 0.8923);
        
        // Generate position using improved 2D hash
        vec2 randPos = hash2D(seed1 * 999.7 + seed2 * 444.3);
        
        // Additional scrambling to ensure no patterns
        randPos.x = hash(randPos.x * 17.3 + randPos.y * 31.7);
        randPos.y = hash(randPos.y * 13.5 + seed1 * 7.7);
        
        // Convert to pixel coordinates
        vec2 planePos = randPos * iResolution.xy;
        
        // Calculate distance to mouse
        float mouseDist = length(planePos - mousePos);
        float mouseInfluence = 1.0 - smoothstep(0.0, MOUSE_EFFECT_RADIUS, mouseDist);
        
        // Calculate density based on mouse proximity
        float density = mix(MIN_DENSITY, MAX_DENSITY, mouseInfluence);
        
        // Skip stroke based on density
        if(hash(seed1 * 111.1 + seed2 * 222.2) > density) continue;
        
        // Quick Manhattan distance check - extremely fast
        vec2 diff = abs(fragCoord - planePos);
        if(diff.x > 35.0 || diff.y > 35.0) continue;
        
        // Calculate size based on mouse proximity
        float sizeHash1 = hash(seed1 * 4.567 + seed2 * 8.901);
        float sizeHash2 = hash(seed2 * 5.678 + seed1 * 9.012);
        
        // Interpolate between min and max sizes based on mouse distance
        float planeWidth = mix(
            MIN_BRUSH_WIDTH + (MAX_BRUSH_WIDTH - MIN_BRUSH_WIDTH) * sizeHash1,
            MIN_BRUSH_WIDTH,
            mouseInfluence
        );
        float planeHeight = mix(
            MIN_BRUSH_HEIGHT + (MAX_BRUSH_HEIGHT - MIN_BRUSH_HEIGHT) * sizeHash2,
            MIN_BRUSH_HEIGHT,
            mouseInfluence
        );
        
        // More precise distance check
        float maxDim = max(planeWidth, planeHeight) * 0.71;
        if(diff.x > maxDim || diff.y > maxDim) continue;
        
        // Sample the flow field
        vec2 flowVector = texture(iChannel1, randPos).xy;
        
        // Fast rotation using pre-computed values
        float angle = atan(flowVector.y, flowVector.x);
        vec2 cs = vec2(cos(angle), sin(angle));
        
        // Transform pixel to local space
        vec2 relativePos = fragCoord - planePos;
        vec2 localPos = vec2(
            cs.x * relativePos.x + cs.y * relativePos.y,
            -cs.y * relativePos.x + cs.x * relativePos.y
        );
        
        // Check bounds
        vec2 halfSize = vec2(planeWidth, planeHeight) * 0.5;
        if(abs(localPos.x) > halfSize.x || abs(localPos.y) > halfSize.y) continue;
        
        // Calculate local UV
        vec2 localUV = (localPos + halfSize) / (halfSize * 2.0);
        
        // Fast 90 degree rotation for brush UV
        vec2 brushUV = vec2(localUV.y, 1.0 - localUV.x);
        
        // Single texture fetch for brush
        vec4 brush = texture(iChannel0, brushUV);
        
        // Skip if brush has no opacity
        if(brush.a < 0.01) continue;
        
        // Sample color
        vec3 color = texture(iChannel2, randPos).rgb;
        
        // Optimized blending
        float alpha = brush.a * (1.0 - fragColor.a);
        fragColor.rgb = fragColor.rgb + color * alpha;
        fragColor.a = fragColor.a + alpha;
    }
    
    // Clamp alpha to valid range
    fragColor.a = min(fragColor.a, 1.0);
}