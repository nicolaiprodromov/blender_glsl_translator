
#include "sdf/sdf_shapes.glsl"

void mainImage(out vec4 fragColor, in vec2 fragCoord) {

    vec2 p = (2.0*fragCoord-iResolution.xy)/iResolution.y;

    vec2 np = p;
    np.x *= 13.0;

    float w          = 666.0;
    float scale      = .65;
    float distortion = 0.6;
    float roughness  = 0.86;
    int   detail     = 11;

    vec3 position = vec3(np, 0.0);
    float noise = perlinNoise(position, w, scale, distortion, roughness, detail);

    float w1          = 154.0;
    float scale1      = .65;
    float distortion1 = 0.7;
    float roughness1  = 0.90;
    int   detail1     = 11;

    vec3 position1 = vec3(np, 0.0);
    float noise1 = perlinNoise(position1, w1, scale1, distortion1, roughness1, detail1);

    p.y += .5;
    p += (noise - 0.5) * 1.2;

    float base_shape = sdUnevenCapsule(p, .2, 0.3, 1.0);

    base_shape = base_shape < .1 ? 1.0 : 0.0;

    base_shape *= (noise1 > .48 ? 1.0 : .0);
    
    fragColor = vec4(vec3(base_shape), 1.0);

}