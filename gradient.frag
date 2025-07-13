#iChannel0 "file://shapes.frag"
#include "utils/utils.glsl"

vec2 getGradient(sampler2D sdfTexture, vec2 uv, float epsilon) {
    // Sample the SDF at offset positions
    float left  = texture(sdfTexture, uv + vec2(-epsilon, 0.0)).r;
    float right = texture(sdfTexture, uv + vec2( epsilon, 0.0)).r;
    float down  = texture(sdfTexture, uv + vec2(0.0, -epsilon)).r;
    float up    = texture(sdfTexture, uv + vec2(0.0,  epsilon)).r;
    
    // Calculate the gradient using finite differences
    vec2 gradient = vec2(
        (right - left) / (2.0 * epsilon),
        (up - down) / (2.0 * epsilon)
    );
    
    return gradient;
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 p = fragCoord / iResolution.xy;
    
    vec2 texelSize = 1.0 / iResolution.xy;
    vec2 gradient = getGradient(iChannel0, p, 0.005);
    
    vec2 normalizedGrad = normalize(gradient + vec2(0.00001));
    fragColor = vec4(normalizedGrad, 0.0, 1.0);

    // float arrows = drawArrowField(p, 0.03, 0.01, normalizedGrad);
    // vec4 color = mix(vec4(normalizedGrad, 0.0, 1.0), vec4(1.0), arrows);
    // fragColor = color;
}