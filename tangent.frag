#iChannel0 "file://gradient.frag"
#include "utils/utils.glsl"

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{   
    vec2 p = fragCoord / iResolution.xy;

    vec4 tex = texture2D(iChannel0, p);
    vec2 gradient = tex.xy;

    vec2 tangent = vec2(-gradient.y, gradient.x);
    tangent = normalize(tangent + vec2(0.00001));
    fragColor = vec4(tangent, 0.0, 1.0);

    // float arrows = drawArrowField(p, 0.02, 0.01, tangent);
    // vec4 color = mix(vec4(tangent, 0.0, 1.0), vec4(1.0), arrows);
    // fragColor = color;
}