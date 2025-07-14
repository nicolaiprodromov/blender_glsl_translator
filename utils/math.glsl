vec2 linearLight(vec2 base, vec2 blend, float factor) {
    vec2 linearBurn = max(base + 2.0 * blend - 1.0, vec2(0.0));
    vec2 linearDodge = min(base + 2.0 * (blend - 0.5), vec2(1.0));
    vec2 result = mix(linearBurn, linearDodge, step(0.5, blend));
    return mix(base, result, factor);
}

float random(float seed) {
    return fract(sin(seed) * 43758.5453);
}

// make a function to return random float between a and b
float randomRange(float a, float b, float seed) {
    return a + (b - a) * random(seed);
}   

mat2 rotate2D(float angle) {
    float c = cos(angle);
    float s = sin(angle);
    return mat2(c, -s, s, c);
}

vec2 rotateVector(vec2 v, vec3 rotation) {
    float cx = cos(rotation.x), sx = sin(rotation.x);
    float cy = cos(rotation.y), sy = sin(rotation.y);
    float cz = cos(rotation.z), sz = sin(rotation.z);
    
    // Combined rotation matrix (ZYX order)
    mat3 rot = mat3(
        cy*cz, -cy*sz, sy,
        sx*sy*cz + cx*sz, -sx*sy*sz + cx*cz, -sx*cy,
        -cx*sy*cz + sx*sz, cx*sy*sz + sx*cz, cx*cy
    );
    
    vec3 v3 = rot * vec3(v, 0.0);
    return v3.xy;
}

float toRadians(float degrees) {
    return degrees * (3.14159265359 / 180.0);
}

float dot2( in vec2 v ){
    return dot(v,v);
}

float ndot(vec2 a, vec2 b ){
    return a.x*b.x - a.y*b.y;
}

vec3 hash3(vec3 p) {
    p = vec3(dot(p, vec3(127.1, 311.7, 74.7)),
             dot(p, vec3(269.5, 183.3, 246.1)),
             dot(p, vec3(113.5, 271.9, 124.6)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

vec4 hash4(vec4 p) {
    p = vec4(dot(p, vec4(127.1, 311.7, 74.7, 269.5)),
             dot(p, vec4(269.5, 183.3, 246.1, 113.5)),
             dot(p, vec4(113.5, 271.9, 124.6, 311.7)),
             dot(p, vec4(271.9, 124.6, 127.1, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

float quintic(float t) {
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

float perlin4D(vec4 p) {
    vec4 i = floor(p);
    vec4 f = fract(p);
    
    // Smooth the fractional parts
    vec4 u = vec4(quintic(f.x), quintic(f.y), quintic(f.z), quintic(f.w));
    
    // Generate gradients for the 16 corners of the 4D hypercube
    float n0000 = dot(hash4(i + vec4(0,0,0,0)), f - vec4(0,0,0,0));
    float n1000 = dot(hash4(i + vec4(1,0,0,0)), f - vec4(1,0,0,0));
    float n0100 = dot(hash4(i + vec4(0,1,0,0)), f - vec4(0,1,0,0));
    float n1100 = dot(hash4(i + vec4(1,1,0,0)), f - vec4(1,1,0,0));
    float n0010 = dot(hash4(i + vec4(0,0,1,0)), f - vec4(0,0,1,0));
    float n1010 = dot(hash4(i + vec4(1,0,1,0)), f - vec4(1,0,1,0));
    float n0110 = dot(hash4(i + vec4(0,1,1,0)), f - vec4(0,1,1,0));
    float n1110 = dot(hash4(i + vec4(1,1,1,0)), f - vec4(1,1,1,0));
    
    float n0001 = dot(hash4(i + vec4(0,0,0,1)), f - vec4(0,0,0,1));
    float n1001 = dot(hash4(i + vec4(1,0,0,1)), f - vec4(1,0,0,1));
    float n0101 = dot(hash4(i + vec4(0,1,0,1)), f - vec4(0,1,0,1));
    float n1101 = dot(hash4(i + vec4(1,1,0,1)), f - vec4(1,1,0,1));
    float n0011 = dot(hash4(i + vec4(0,0,1,1)), f - vec4(0,0,1,1));
    float n1011 = dot(hash4(i + vec4(1,0,1,1)), f - vec4(1,0,1,1));
    float n0111 = dot(hash4(i + vec4(0,1,1,1)), f - vec4(0,1,1,1));
    float n1111 = dot(hash4(i + vec4(1,1,1,1)), f - vec4(1,1,1,1));
    
    // Interpolate along x for each y,z,w
    float nx00 = mix(n0000, n1000, u.x);
    float nx10 = mix(n0100, n1100, u.x);
    float nx01 = mix(n0010, n1010, u.x);
    float nx11 = mix(n0110, n1110, u.x);
    
    float nx001 = mix(n0001, n1001, u.x);
    float nx101 = mix(n0101, n1101, u.x);
    float nx011 = mix(n0011, n1011, u.x);
    float nx111 = mix(n0111, n1111, u.x);
    
    // Interpolate along y
    float nxy0 = mix(nx00, nx10, u.y);
    float nxy1 = mix(nx01, nx11, u.y);
    float nxy01 = mix(nx001, nx101, u.y);
    float nxy11 = mix(nx011, nx111, u.y);
    
    // Interpolate along z
    float nxyz0 = mix(nxy0, nxy1, u.z);
    float nxyz1 = mix(nxy01, nxy11, u.z);
    
    // Interpolate along w
    return mix(nxyz0, nxyz1, u.w) * 0.87;
}

vec3 distort(vec3 p, float amount, float w) {
    if (amount < 0.001) return p;
    
    vec3 offset = vec3(
        perlin4D(vec4(p * 2.0, w)),
        perlin4D(vec4(p * 2.0 + 100.0, w)),
        perlin4D(vec4(p * 2.0 + 200.0, w))
    );
    
    return p + offset * amount;
}

float perlinNoise(vec3 position, float w, float scale, float distortion, float roughness, int detail) {
    // Apply scale
    vec3 p = position * scale;
    
    // Apply distortion
    p = distort(p, distortion, w);
    
    float noise = 0.0;
    float amplitude = 1.0;
    float frequency = 1.0;
    float maxValue = 0.0;
    
    // Octave loop for detail
    for (int i = 0; i < detail; i++) {
        noise += perlin4D(vec4(p * frequency, w)) * amplitude;
        maxValue += amplitude;
        
        amplitude *= roughness;
        frequency *= 2.0;
    }
    
    // Normalize to [0, 1]
    return (noise / maxValue) * 0.5 + 0.5;
}
