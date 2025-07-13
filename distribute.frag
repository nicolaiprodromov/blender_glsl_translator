#include "utils/math.glsl"
#iChannel0 "file://arrow.png"
#iChannel1 "file://tangent.frag"
#iChannel2 "file://shapes.frag"

vec4 distributeRandomly(vec2 uv, sampler2D inputTexture, float density, float size, 
                       float minIndividualSize, float maxIndividualSize, float seed,
                       float overlapThreshold, vec2 vectorField) {
    vec4 result = vec4(0.0);
    
    // Calculate grid resolution based on density
    float pointsPer100Px = density;
    float pointsPerPixel = pointsPer100Px / 10000.0;
    float avgPointSpacing = 1.0 / sqrt(pointsPerPixel);
    
    // Grid cell size in UV space
    float cellSize = avgPointSpacing / min(iResolution.x, iResolution.y);
    
    // Check neighboring cells
    vec2 centerCell = floor(uv / cellSize);
    
    for (int dx = -2; dx <= 2; dx++) {
        for (int dy = -2; dy <= 2; dy++) {
            vec2 cellCoord = centerCell + vec2(dx, dy);
            
            // Each cell can have multiple points based on density
            int pointsInCell = int(density * 0.1);
            pointsInCell = max(1, pointsInCell);
            
            for (int p = 0; p < pointsInCell; p++) {
                vec4 rand = hash4(vec4(cellCoord.x, cellCoord.y, float(p), seed));
                
                // Only place point if random value says so (for fractional densities)
                float fractionalPart = fract(density * 0.1);
                if (p == pointsInCell - 1 && rand.w * 0.5 + 0.5 > fractionalPart) {
                    continue;
                }
                
                // Initial random position within cell
                vec2 initialPos = (cellCoord + vec2(rand.x, rand.y) * 0.5 + 0.5) * cellSize;
                
                // Individual size for this point
                float t = rand.z * 0.5 + 0.5;
                float individualSize = mix(minIndividualSize, maxIndividualSize, t);
                float imageSize = size * individualSize;
                
                // Collision avoidance: adjust position based on nearby points
                vec2 pointPos = initialPos;
                
                // Multiple iterations for stronger avoidance
                for (int iter = 0; iter < 3; iter++) {
                    vec2 totalDisplacement = vec2(0.0);
                    int collisionCount = 0;
                    
                    // Check nearby cells for collision
                    for (int cdx = -3; cdx <= 3; cdx++) {
                        for (int cdy = -3; cdy <= 3; cdy++) {
                            vec2 checkCell = cellCoord + vec2(cdx, cdy);
                            
                            int checkPointsInCell = int(density * 0.1);
                            checkPointsInCell = max(1, checkPointsInCell);
                            
                            for (int cp = 0; cp < checkPointsInCell; cp++) {
                                // Skip self
                                if (cdx == 0 && cdy == 0 && cp == p) continue;
                                
                                vec4 otherRand = hash4(vec4(checkCell.x, checkCell.y, float(cp), seed));
                                
                                // Check if other point exists
                                float otherFractional = fract(density * 0.1);
                                if (cp == checkPointsInCell - 1 && otherRand.w * 0.5 + 0.5 > otherFractional) {
                                    continue;
                                }
                                
                                // Other point properties
                                vec2 otherPos = (checkCell + vec2(otherRand.x, otherRand.y) * 0.5 + 0.5) * cellSize;
                                float otherT = otherRand.z * 0.5 + 0.5;
                                float otherIndividualSize = mix(minIndividualSize, maxIndividualSize, otherT);
                                float otherImageSize = size * otherIndividualSize;
                                
                                // Calculate overlap
                                vec2 diff = pointPos - otherPos;
                                float dist = length(diff);
                                float combinedRadius = (imageSize + otherImageSize) * 0.5;
                                float minAllowedDist = combinedRadius * (1.0 - overlapThreshold);
                                
                                // If overlapping too much, calculate required displacement
                                if (dist < minAllowedDist && dist > 0.001) {
                                    // Calculate how much we need to move to respect the threshold
                                    float moveDistance = minAllowedDist - dist;
                                    vec2 moveDirection = normalize(diff);
                                    
                                    // Move half the required distance (other point would move the other half)
                                    totalDisplacement += moveDirection * moveDistance * 0.6;
                                    collisionCount++;
                                }
                            }
                        }
                    }
                    
                    // Apply displacement
                    if (collisionCount > 0) {
                        pointPos += totalDisplacement;
                    }
                }
                
                // Sample the vector field at this point's position
                // Note: vectorField is already mapped to UV, we just need to interpolate
                // In a real implementation, you might sample from a texture here
                vec2 fieldVector = vectorField; // For now, using the passed vector directly
                
                // Calculate rotation angle from the vector
                float rotation = atan(fieldVector.y, fieldVector.x);
                
                // Check if current pixel is inside this adjusted image position
                vec2 localPos = uv - pointPos;
                
                // Apply rotation to align with vector field
                float cosR = cos(rotation);
                float sinR = sin(rotation);
                mat2 rotMatrix = mat2(cosR, -sinR, sinR, cosR);
                vec2 rotatedPos = rotMatrix * localPos;
                
                if (abs(rotatedPos.x) < imageSize * 0.5 && abs(rotatedPos.y) < imageSize * 0.5) {
                    vec2 localUV = (rotatedPos + imageSize * 0.5) / imageSize;
                    vec4 sampledColor = texture(inputTexture, localUV);
                    
                    float edgeSoftness = 0.002;
                    float edgeX = smoothstep(imageSize * 0.5 - edgeSoftness, imageSize * 0.5, abs(rotatedPos.x));
                    float edgeY = smoothstep(imageSize * 0.5 - edgeSoftness, imageSize * 0.5, abs(rotatedPos.y));
                    float alpha = sampledColor.a * (1.0 - max(edgeX, edgeY));
                    
                    if (alpha > result.a) {
                        result = vec4(sampledColor.rgb, alpha);
                    }
                }
            }
        }
    }
    
    return result;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    
    float density = 5.0;
    float size    = 0.1;
    float minSize = 0.25;
    float maxSize = 1.0;
    float seed    = 1666.0;
    float overlap = 0.0;
    float rot     = 45.0;

    vec2 vectorField = texture(iChannel1, uv).xy;
    
    vec4 distributed = distributeRandomly(uv, iChannel0, density, size, minSize, maxSize, seed, overlap, vectorField);

    vec4 arrows = distributed.a > 0.95 ? vec4(1.0) : vec4(0.0);

    vec4 shapes = texture(iChannel2, uv);

    vec4 color = mix(shapes, vec4(1.0), arrows);
    
    fragColor = color;
}