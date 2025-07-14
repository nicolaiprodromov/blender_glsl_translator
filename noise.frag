#include "utils/math.glsl"

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;

    float w          = iTime * .15;
    float scale      = 1.0;
    float distortion = 0.4;
    float roughness  = 0.86;
    int   detail     = 15;

    vec3 position = vec3(uv, 0.0);
    float noise = perlinNoise(position, w, scale, distortion, roughness, detail);
    
    fragColor = vec4(vec3(noise > .5 ? 1.0 : 0.0), 1.0);
}