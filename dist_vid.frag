#iChannel0 "sequence.frag"
#iChannel1 "dist_vid.frag"

// Configuration variables - adjust these to experiment
#define ENLARGEMENT_FACTOR 20.0
#define SELECTION_PERCENTAGE 0.1
#define HUE_SHIFT_PERCENTAGE 0.15  // Percentage of pixels to hue shift
#define HUE_SHIFT_AMOUNT 0.3       // Amount to shift hue (0.0 to 1.0)

// Random function using time for per-frame variation
float random(vec2 st, float time) {
    return fract(sin(dot(st.xy + time, vec2(12.9898, 78.233))) * 43758.5453123);
}

// Convert RGB to HSV
vec3 rgb2hsv(vec3 c) {
    vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
    vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
    vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
    
    float d = q.x - min(q.w, q.y);
    float e = 1.0e-10;
    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

// Convert HSV to RGB
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Function to apply random hue shift effect
vec4 applyRandomHueShift(vec4 color, vec2 uv, float time, float hueShiftPercentage, float hueShiftAmount) {
    // Generate random value for this pixel (changes per frame due to time)
    float randVal = random(uv, time + 100.0); // Add offset to get different randomness than enlargement
    
    // Check if this pixel should have its hue shifted
    if (randVal < hueShiftPercentage) {
        // Convert to HSV, shift hue, convert back to RGB
        vec3 hsv = rgb2hsv(color.rgb);
        hsv.x = fract(hsv.x + hueShiftAmount); // Shift hue and wrap around
        return vec4(hsv2rgb(hsv), color.a);
    } else {
        // Return original color
        return color;
    }
}

// Function to apply random pixel enlargement effect
vec4 applyRandomEnlargement(sampler2D channel, vec2 uv, vec2 resolution, float time, float enlargementFactor, float selectionPercentage) {
    // Generate random value for this pixel (changes per frame due to time)
    float randVal = random(uv, time);
    
    // Check if this pixel should be enlarged
    if (randVal > (1.0 - selectionPercentage)) {
        // Make pixel bigger by scaling UV coordinates
        vec2 center = floor(uv * resolution / enlargementFactor) * enlargementFactor / resolution + (enlargementFactor * 0.5) / resolution;
        return texture(channel, center);
    } else {
        // Normal pixel
        return texture(channel, uv);
    }
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    
    // Apply enlargement effects
    fragColor = applyRandomEnlargement(
        iChannel0, 
        uv, 
        iResolution.xy, 
        iTime, 
        30.0, 
        .05
    );

    fragColor += applyRandomEnlargement(
        iChannel0, 
        uv, 
        iResolution.xy, 
        iTime, 
        ENLARGEMENT_FACTOR, 
        SELECTION_PERCENTAGE
    ) * .3;
    
    // Apply random hue shift effect
    fragColor = applyRandomHueShift(
        fragColor, 
        uv, 
        iTime, 
        HUE_SHIFT_PERCENTAGE, 
        HUE_SHIFT_AMOUNT
    );
}