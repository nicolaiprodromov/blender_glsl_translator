#iChannel0 "accumulator.frag"      // Self-reference for feedback
#iChannel1 "brush_renderer.frag"   // Current frame's brush

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // uv
    vec2 uv = fragCoord / iResolution.xy;
    
    // Get the previous accumulated result
    vec4 previousAccumulation = texture(iChannel0, uv);
    
    // Get the current frame's brush
    vec4 currentBrush = texture(iChannel1, uv);
    
    // Accumulate using max
    fragColor = mix(previousAccumulation, currentBrush, currentBrush.a);
    //fragColor = mix(vec4(1.0), fragColor, fragColor.a); // Blend with white for visibility
    
}