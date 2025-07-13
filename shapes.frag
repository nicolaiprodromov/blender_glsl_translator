#include "sdf/sdf_shapes.glsl"
#include "sdf/sdf_op.glsl"

void mainImage( out vec4 fragColor, in vec2 fragCoord ){
    vec2 p = (2.0*fragCoord-iResolution.xy)/iResolution.y;
    float dist = 0.0;

    float curve9 = sdBezierCubic(p,
        vec2(0.494646, 0.433765),
        vec2(0.456857, 0.509984),
        vec2(0.411082, 0.576376),
        vec2(0.359374, 0.628663));
    dist = curve9;

    float curve10 = sdBezierCubic(p,
        vec2(0.359374, 0.628663),
        vec2(0.300482, 0.688248),
        vec2(0.233961, 0.726638),
        vec2(0.165343, 0.747623));
    dist = min(dist, curve10);

    float curve11 = sdBezierCubic(p,
        vec2(0.165343, 0.747623),
        vec2(0.035558, 0.787346),
        vec2(-0.100607, 0.773169),
        vec2(-0.227536, 0.716882));
    dist = min(dist, curve11);

    float curve12 = sdBezierCubic(p,
        vec2(-0.227536, 0.716882),
        vec2(-0.347461, 0.663754),
        vec2(-0.460114, 0.572657),
        vec2(-0.558223, 0.452153));
    dist = min(dist, curve12);

    float curve13 = sdBezierCubic(p,
        vec2(-0.558223, 0.452153),
        vec2(-0.656331, 0.331649),
        vec2(-0.738958, 0.181528),
        vec2(-0.798073, 0.010071));
    dist = min(dist, curve13);

    float curve14 = sdBezierCubic(p,
        vec2(-0.798073, 0.010071),
        vec2(-0.805389, -0.011124),
        vec2(-0.812305, -0.032670),
        vec2(-0.818863, -0.054427));
    dist = min(dist, curve14);

    float curve15 = sdBezierCubic(p,
        vec2(-0.818863, -0.054427),
        vec2(-0.824975, -0.074710),
        vec2(-0.805746, -0.092536),
        vec2(-0.799590, -0.072113));
    dist = min(dist, curve15);

    float curve16 = sdBezierCubic(p,
        vec2(-0.799590, -0.072113),
        vec2(-0.799590, -0.072113),
        vec2(-0.799590, -0.072113),
        vec2(-0.799590, -0.072113));
    dist = min(dist, curve16);

    float curve17 = sdBezierCubic(p,
        vec2(-0.799590, -0.072113),
        vec2(-0.799575, -0.072113),
        vec2(-0.799560, -0.072113),
        vec2(-0.799545, -0.072113));
    dist = min(dist, curve17);

    float curve18 = sdBezierCubic(p,
        vec2(-0.606005, -0.200267),
        vec2(-0.568796, -0.296628),
        vec2(-0.515883, -0.375513),
        vec2(-0.455340, -0.435169));
    dist = min(dist, curve18);

    float curve19 = sdBezierCubic(p,
        vec2(-0.455340, -0.435169),
        vec2(-0.394396, -0.495245),
        vec2(-0.325957, -0.536583),
        vec2(-0.255867, -0.561147));
    dist = min(dist, curve19);

    float curve20 = sdBezierCubic(p,
        vec2(-0.255867, -0.561147),
        vec2(-0.169002, -0.591536),
        vec2(-0.079325, -0.597642),
        vec2(0.009414, -0.593712));
    dist = min(dist, curve20);

    float curve21 = sdBezierCubic(p,
        vec2(0.009414, -0.593712),
        vec2(0.054252, -0.591746),
        vec2(0.099045, -0.587185),
        vec2(0.143749, -0.581851));
    dist = min(dist, curve21);

    fragColor = vec4(dist);
}