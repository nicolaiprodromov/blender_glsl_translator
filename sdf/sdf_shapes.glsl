#include "utils/math.glsl"

float sdCircle( vec2 p, float r ){
    return length(p) - r;
}

float sdRoundedBox( in vec2 p, in vec2 b, in vec4 r ){
    r.xy = (p.x>0.0)?r.xy : r.zw;
    r.x  = (p.y>0.0)?r.x  : r.y;
    vec2 q = abs(p)-b+r.x;
    return min(max(q.x,q.y),0.0) + length(max(q,0.0)) - r.x;
}

float sdChamferBox( in vec2 p, in vec2 b, in float chamfer ){
    p = abs(p)-b;

    p = (p.y>p.x) ? p.yx : p.xy;
    p.y += chamfer;
    
    const float k = 1.0-sqrt(2.0);
    if( p.y<0.0 && p.y+p.x*k<0.0 )
        return p.x;
    
    if( p.x<p.y )
        return (p.x+p.y)*sqrt(0.5);    
    
    return length(p);
}

float sdBox( in vec2 p, in vec2 b ){
    vec2 d = abs(p)-b;
    return length(max(d,0.0)) + min(max(d.x,d.y),0.0);
}

float sdSegment( in vec2 p, in vec2 a, in vec2 b ){
    vec2 pa = p-a, ba = b-a;
    float h = clamp( dot(pa,ba)/dot(ba,ba), 0.0, 1.0 );
    return length( pa - ba*h );
}

float sdRhombus( in vec2 p, in vec2 b ) {
    p = abs(p);
    float h = clamp( ndot(b-2.0*p,b)/dot(b,b), -1.0, 1.0 );
    float d = length( p-0.5*b*vec2(1.0-h,1.0+h) );
    return d * sign( p.x*b.y + p.y*b.x - b.x*b.y );
}

float sdTriangle( in vec2 p, in vec2 p0, in vec2 p1, in vec2 p2 ){
    vec2 e0 = p1-p0, e1 = p2-p1, e2 = p0-p2;
    vec2 v0 = p -p0, v1 = p -p1, v2 = p -p2;
    vec2 pq0 = v0 - e0*clamp( dot(v0,e0)/dot(e0,e0), 0.0, 1.0 );
    vec2 pq1 = v1 - e1*clamp( dot(v1,e1)/dot(e1,e1), 0.0, 1.0 );
    vec2 pq2 = v2 - e2*clamp( dot(v2,e2)/dot(e2,e2), 0.0, 1.0 );
    float s = sign( e0.x*e2.y - e0.y*e2.x );
    vec2 d = min(min(vec2(dot(pq0,pq0), s*(v0.x*e0.y-v0.y*e0.x)),
                     vec2(dot(pq1,pq1), s*(v1.x*e1.y-v1.y*e1.x))),
                     vec2(dot(pq2,pq2), s*(v2.x*e2.y-v2.y*e2.x)));
    return -sqrt(d.x)*sign(d.y);
}

float sdPentagon( in vec2 p, in float r ){
    const vec3 k = vec3(0.809016994,0.587785252,0.726542528);
    p.x = abs(p.x);
    p -= 2.0*min(dot(vec2(-k.x,k.y),p),0.0)*vec2(-k.x,k.y);
    p -= 2.0*min(dot(vec2( k.x,k.y),p),0.0)*vec2( k.x,k.y);
    p -= vec2(clamp(p.x,-r*k.z,r*k.z),r);    
    return length(p)*sign(p.y);
}

float sdHexagon( in vec2 p, in float r ){
    const vec3 k = vec3(-0.866025404,0.5,0.577350269);
    p = abs(p);
    p -= 2.0*min(dot(k.xy,p),0.0)*k.xy;
    p -= vec2(clamp(p.x, -k.z*r, k.z*r), r);
    return length(p)*sign(p.y);
}

float sdEllipse( in vec2 p, in vec2 ab ){
    p = abs(p); if( p.x > p.y ) {p=p.yx;ab=ab.yx;}
    float l = ab.y*ab.y - ab.x*ab.x;
    float m = ab.x*p.x/l;      float m2 = m*m; 
    float n = ab.y*p.y/l;      float n2 = n*n; 
    float c = (m2+n2-1.0)/3.0; float c3 = c*c*c;
    float q = c3 + m2*n2*2.0;
    float d = c3 + m2*n2;
    float g = m + m*n2;
    float co;
    if( d<0.0 )
    {
        float h = acos(q/c3)/3.0;
        float s = cos(h);
        float t = sin(h)*sqrt(3.0);
        float rx = sqrt( -c*(s + t + 2.0) + m2 );
        float ry = sqrt( -c*(s - t + 2.0) + m2 );
        co = (ry+sign(l)*rx+abs(g)/(rx*ry)- m)/2.0;
    }
    else
    {
        float h = 2.0*m*n*sqrt( d );
        float s = sign(q+h)*pow(abs(q+h), 1.0/3.0);
        float u = sign(q-h)*pow(abs(q-h), 1.0/3.0);
        float rx = -s - u - c*4.0 + 2.0*m2;
        float ry = (s - u)*sqrt(3.0);
        float rm = sqrt( rx*rx + ry*ry );
        co = (ry/sqrt(rm-rx)+2.0*g/rm-m)/2.0;
    }
    vec2 r = ab * vec2(co, sqrt(1.0-co*co));
    return length(r-p) * sign(p.y-r.y);
}

float sdBezier( in vec2 pos, in vec2 A, in vec2 B, in vec2 C ){    
    vec2 a = B - A;
    vec2 b = A - 2.0*B + C;
    vec2 c = a * 2.0;
    vec2 d = A - pos;
    float kk = 1.0/dot(b,b);
    float kx = kk * dot(a,b);
    float ky = kk * (2.0*dot(a,a)+dot(d,b)) / 3.0;
    float kz = kk * dot(d,a);      
    float res = 0.0;
    float p = ky - kx*kx;
    float p3 = p*p*p;
    float q = kx*(2.0*kx*kx-3.0*ky) + kz;
    float h = q*q + 4.0*p3;
    if( h >= 0.0) 
    { 
        h = sqrt(h);
        vec2 x = (vec2(h,-h)-q)/2.0;
        vec2 uv = sign(x)*pow(abs(x), vec2(1.0/3.0));
        float t = clamp( uv.x+uv.y-kx, 0.0, 1.0 );
        res = dot2(d + (c + b*t)*t);
    }
    else
    {
        float z = sqrt(-p);
        float v = acos( q/(p*z*2.0) ) / 3.0;
        float m = cos(v);
        float n = sin(v)*1.732050808;
        vec3  t = clamp(vec3(m+m,-n-m,n-m)*z-kx,0.0,1.0);
        res = min( dot2(d+(c+b*t.x)*t.x),
                   dot2(d+(c+b*t.y)*t.y) );
        // the third root cannot be the closest
        // res = min(res,dot2(d+(c+b*t.z)*t.z));
    }
    return sqrt( res );
}

float sdBezierCubic( in vec2 pos, in vec2 A, in vec2 B, in vec2 C, in vec2 D ){
    // Cubic Bezier: P(t) = (1-t)³·A + 3·(1-t)²·t·B + 3·(1-t)·t²·C + t³·D
    
    float min_dist = 1e10;
    
    // Initial sampling to find good starting points
    const int INITIAL_SAMPLES = 16;
    float best_t = 0.0;
    
    for(int i = 0; i <= INITIAL_SAMPLES; i++) {
        float t = float(i) / float(INITIAL_SAMPLES);
        
        // Evaluate cubic Bezier at t
        float t2 = t * t;
        float t3 = t2 * t;
        float mt = 1.0 - t;
        float mt2 = mt * mt;
        float mt3 = mt2 * mt;
        
        vec2 p = mt3 * A + 3.0 * mt2 * t * B + 3.0 * mt * t2 * C + t3 * D;
        float dist = length(p - pos);
        
        if(dist < min_dist) {
            min_dist = dist;
            best_t = t;
        }
    }
    
    // Newton-Raphson refinement
    const int NEWTON_ITERATIONS = 5;
    float t = best_t;
    
    for(int i = 0; i < NEWTON_ITERATIONS; i++) {
        float t2 = t * t;
        float t3 = t2 * t;
        float mt = 1.0 - t;
        float mt2 = mt * mt;
        float mt3 = mt2 * mt;
        
        // Point on curve
        vec2 p = mt3 * A + 3.0 * mt2 * t * B + 3.0 * mt * t2 * C + t3 * D;
        
        // First derivative
        vec2 dp = 3.0 * mt2 * (B - A) + 
                  6.0 * mt * t * (C - B) + 
                  3.0 * t2 * (D - C);
        
        // Second derivative
        vec2 ddp = 6.0 * mt * (C - 2.0*B + A) + 
                   6.0 * t * (D - 2.0*C + B);
        
        // Vector from curve to point
        vec2 diff = p - pos;
        
        // Newton's method: minimize |P(t) - pos|²
        float f = dot(diff, dp);
        float df = dot(dp, dp) + dot(diff, ddp);
        
        if(abs(df) > 0.00001) {
            t = t - f / df;
            t = clamp(t, 0.0, 1.0);
        }
    }
    
    // Final evaluation
    float t2 = t * t;
    float t3 = t2 * t;
    float mt = 1.0 - t;
    float mt2 = mt * mt;
    float mt3 = mt2 * mt;
    
    vec2 p = mt3 * A + 3.0 * mt2 * t * B + 3.0 * mt * t2 * C + t3 * D;
    
    return length(p - pos);
}

float sdUnevenCapsule( vec2 p, float r1, float r2, float h ){
    p.x = abs(p.x);
    float b = (r1-r2)/h;
    float a = sqrt(1.0-b*b);
    float k = dot(p,vec2(-b,a));
    if( k < 0.0 ) return length(p) - r1;
    if( k > a*h ) return length(p-vec2(0.0,h)) - r2;
    return dot(p, vec2(a,b) ) - r1;
}