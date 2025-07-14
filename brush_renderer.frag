#iChannel0 "brush.frag"
#iChannel1 "tangent.frag"
#iChannel2 "file://assets/face2.jpg"
#include "sdf/sdf_shapes.glsl"

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    
    // Start with transparent black
    fragColor = vec4(0.0);
    
    // Number of strokes per frame (change this to adjust)
    const int STROKES_PER_FRAME = 200;
    
    // Loop through all strokes for this frame
    for(int strokeIndex = 0; strokeIndex < STROKES_PER_FRAME; strokeIndex++) {
        // Use stroke index to create unique random seeds
        float strokeSeed = float(iFrame * STROKES_PER_FRAME + strokeIndex);
        
        // Define plane dimensions in pixels
        float planeWidth = randomRange(10.0, 50.0, iTime*60.0 + float(strokeIndex));
        float planeHeight = randomRange(10.0, 40.0, iTime*60.0+1.0 + float(strokeIndex));
        
        // Generate random position for the new plane (in UV space)
        vec2 randomPos = vec2(random(strokeSeed), random(strokeSeed + 1.0));
        
        // Convert random position to pixel coordinates
        vec2 planePos = randomPos * iResolution.xy;
        
        // Sample the flow field at the plane's center position
        vec2 flowVector = texture(iChannel1, randomPos).xy;
        
        // Calculate rotation angle from the flow vector
        float rotationAngle = atan(flowVector.y, flowVector.x);
        
        // Create rotation matrix
        mat2 rotMat = rotate2D(rotationAngle);
        
        // Check if current pixel might be inside the rotated plane
        float maxDim = max(planeWidth, planeHeight) * 0.7071; // sqrt(2)/2
        vec2 expandedMin = planePos - vec2(maxDim);
        vec2 expandedMax = planePos + vec2(maxDim);
        
        if (fragCoord.x >= expandedMin.x && fragCoord.x <= expandedMax.x &&
            fragCoord.y >= expandedMin.y && fragCoord.y <= expandedMax.y) {
            
            // Transform pixel coordinates to plane-local coordinates
            vec2 relativePos = fragCoord - planePos;
            
            // Apply inverse rotation to check if point is inside the plane
            vec2 localPos = rotMat * relativePos;
            
            // Check if the rotated point is inside the original plane bounds
            if (abs(localPos.x) <= planeWidth * 0.5 && abs(localPos.y) <= planeHeight * 0.5) {
                // Calculate local UV coordinates within the plane (0-1 range)
                vec2 localUV = (localPos + vec2(planeWidth, planeHeight) * 0.5) / vec2(planeWidth, planeHeight);

                vec4 input_brush = texture(iChannel0, rotateVector(localUV, vec3(0.0, 0.0, toRadians(90.0))));

                // Only process if this stroke has opacity and we haven't already drawn here
                if(input_brush.a > 0.0 && fragColor.a < 1.0) {
                    // Calculate average color of the image within the brush bounds
                    vec3 avgColor = vec3(0.0);
                    float sampleCount = 0.0;
                    
                    // Sample grid for averaging (adjust for quality vs performance)
                    const int samples = 8;
                    for(int i = 0; i < samples; i++) {
                        for(int j = 0; j < samples; j++) {
                            vec2 sampleUV = vec2(float(i), float(j)) / float(samples - 1);
                            
                            // Transform sample point to world space
                            vec2 sampleLocal = sampleUV * vec2(planeWidth, planeHeight) - vec2(planeWidth, planeHeight) * 0.5;
                            vec2 sampleWorld = planePos + rotMat * sampleLocal;
                            vec2 sampleWorldUV = sampleWorld / iResolution.xy;
                            
                            // Sample the brush at this position to check if we should include this sample
                            vec4 brushSample = texture(iChannel0, rotateVector(sampleUV, vec3(0.0, 0.0, toRadians(90.0))));
                            
                            if(brushSample.a > 0.1) { // Only sample where brush has opacity
                                avgColor += texture(iChannel2, sampleWorldUV).rgb * brushSample.a;
                                sampleCount += brushSample.a;
                            }
                        }
                    }
                    
                    if(sampleCount > 0.0) {
                        avgColor /= sampleCount;
                    }
                    
                    float mix_trs = 0.02; // Adjust this threshold to control blending
                    avgColor = vec3(avgColor.r + randomRange(-mix_trs, mix_trs, iTime + float(strokeIndex)*0.1),
                                    avgColor.g + randomRange(-mix_trs, mix_trs, iTime + 1.0 + float(strokeIndex)*0.1),
                                    avgColor.b + randomRange(-mix_trs, mix_trs, iTime + 2.0 + float(strokeIndex)*0.1)
                                    );
                    
                    // Blend the new stroke with existing color using alpha blending
                    vec4 newStroke = vec4(avgColor, input_brush.a);
                    fragColor = mix(fragColor, newStroke, newStroke.a);
                }
            }
        }
    }
}