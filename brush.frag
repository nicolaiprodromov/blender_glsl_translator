
#include "sdf/sdf_shapes.glsl"

void mainImage(out vec4 fragColor, in vec2 fragCoord) {

    vec2 uv = fragCoord / iResolution.xy;

    vec2 np = uv;
    np.x *= 10.0;
    vec3 position = vec3(np, 0.0);

    //---------------------------------------------------

    float seed = 666.0;
    float timey = iTime;

    float w          = timey + seed;
    float scale      = 1.0;
    float distortion = 0.6;
    float roughness  = 0.86;
    int   detail     = 6;

    float noise = perlinNoise(position, w, scale, distortion, roughness, detail);

    float w1          = timey + seed + 154.0;;
    float scale1      = .35;
    float distortion1 = 0.3;
    float roughness1  = 0.80;
    int   detail1     = 9;

    float noise1 = perlinNoise(position, w1, scale1, distortion1, roughness1, detail1);

    float w2          = timey + seed + 333.0;
    float scale2      = 1.65;
    float distortion2 = 0.3;
    float roughness2  = 0.80;
    int   detail2     = 9;

    float noise2 = perlinNoise(position, w2, scale2, distortion2, roughness2, detail2);


    float w3          = timey + seed + 444.0;
    float scale3      = 1.65;
    float distortion3 = 0.3;
    float roughness3  = 0.80;
    int   detail3     = 9;

    float noise3 = perlinNoise(position, w3, scale3, distortion3, roughness3, detail3);


    //--------------------------------------------------

    uv.x -= .5;
    uv.y -= .3;
    uv += (noise - 0.5)*.1;
    uv = linearLight(uv, vec2(noise, noise), .05);
    float base_shape = sdUnevenCapsule(uv, .1, 0.12, .4);

    base_shape = base_shape < .1 ? 1.0: 0.0;

    base_shape *= (noise1 > .48 ? 1.0 : .9);

    //base_shape *= (noise2 - .2) * 3.5;

    // base_shape += ((noise1 > .6 ? 1.0 : .1)*base_shape);

    vec4 base_color = vec4(.75 + randomRange(-.5, .5, iTime), 0.1+ randomRange(-.5, .5, iTime + 2133.2), 0.2 + randomRange(-.5, .5, iTime +44.0), 1.0) * vec4(base_shape);
    

    fragColor = base_color;
    fragColor = vec4(vec3(base_shape), base_shape);

}