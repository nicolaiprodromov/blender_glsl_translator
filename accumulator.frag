#iChannel0 "accumulator.frag"      // Self-reference for feedback
#iChannel1 "brush_renderer.frag"   // Current frame's brush

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    
    // Use texelFetch for more predictable performance
    ivec2 pixelCoord = ivec2(fragCoord);
    
    // Get previous accumulation
    vec4 previousAccumulation = texelFetch(iChannel0, pixelCoord, 0);
    
    // Get current brush
    vec4 currentBrush = texture(iChannel1, uv);
    
    // Skip blending if current brush has no contribution
    if (currentBrush.a < 0.001) {
        fragColor = previousAccumulation;
        return;
    }
    
    // Optimized blending that avoids feedback issues
    float invAlpha = 1.0 - currentBrush.a;
    fragColor.rgb = previousAccumulation.rgb * invAlpha + currentBrush.rgb * currentBrush.a;
    fragColor.a = previousAccumulation.a * invAlpha + currentBrush.a;
    
    // Clamp to prevent precision drift
    fragColor = clamp(fragColor, 0.0, 1.0);
}