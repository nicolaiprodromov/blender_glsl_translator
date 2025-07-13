float drawArrow(in vec2 p, in float size) {
    // Arrow pointing right (positive X direction) centered at origin
    // Arrow shape: triangle head + rectangular body
    
    // Scale by size
    p = p / size;
    
    // Arrow body (rectangle from x=-0.5 to x=0.2, y=-0.1 to y=0.1)
    float body = step(-0.5, p.x) * step(p.x, 0.2) * step(-0.1, p.y) * step(p.y, 0.1);
    
    // Arrow head (triangle from x=0.2 to x=0.5)
    float head = 0.0;
    if (p.x >= 0.2 && p.x <= 0.6) {
        float headX = (p.x - 0.3) / 0.3; // normalize to 0-1
        float maxY = 0.4 * (1.0 - headX); // triangle shape
        head = step(-maxY, p.y) * step(p.y, maxY);
    }
    
    return max(body, head);
}

float drawArrowField(in vec2 p, in float gridSpacing, in float arrowSize, vec2 vectorField) {
    // Create a grid
    vec2 gridPos = floor(p / gridSpacing) * gridSpacing + gridSpacing * 0.5;
    vec2 localPos = p - gridPos;
    
    // Use the provided vector field directly
    vec2 flow = vectorField;
    
    // Handle zero vectors
    if (length(flow) < 0.001) {
        return 0.0;
    }
    
    flow = normalize(flow);
    
    // Rotate the local position to align with flow direction
    // Create rotation matrix for the flow direction
    float angle = atan(flow.y, flow.x);
    float c = cos(-angle); // negative angle to rotate coordinate system
    float s = sin(-angle);
    vec2 rotatedPos = vec2(c * localPos.x - s * localPos.y, 
                          s * localPos.x + c * localPos.y);
    
    return drawArrow(rotatedPos, arrowSize);
}



