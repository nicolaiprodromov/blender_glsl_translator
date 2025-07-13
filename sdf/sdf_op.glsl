float opUnion( float d1, float d2 ){
    return min(d1,d2);
}
float opSubtraction( float d1, float d2 ){
    return max(-d1,d2);
}
float opIntersection( float d1, float d2 ){
    return max(d1,d2);
}
float opXor(float d1, float d2 ){
    return max(min(d1,d2),-max(d1,d2));
}