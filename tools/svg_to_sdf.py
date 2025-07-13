import xml.etree.ElementTree as ET
import re
import numpy as np
from typing import List, Tuple, Optional

class SVGToGLSLBezier:
    def __init__(self, svg_file: str, scale: float = 1.0, center: bool = True):
        """
        Initialize the converter.
        
        Args:
            svg_file: Path to SVG file
            scale: Scale factor for the output coordinates
            center: Whether to center the shape around origin
        """
        self.svg_file = svg_file
        self.scale = scale
        self.center = center
        self.bezier_curves = []
        self.bounds = {'min_x': float('inf'), 'min_y': float('inf'), 
                      'max_x': float('-inf'), 'max_y': float('-inf')}
        
    def parse_svg(self):
        """Parse SVG file and extract path data."""
        tree = ET.parse(self.svg_file)
        root = tree.getroot()
        
        # Handle SVG namespace
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        
        # Get viewBox if present for proper scaling
        viewbox = root.get('viewBox')
        if viewbox:
            vb = list(map(float, viewbox.split()))
            self.svg_width = vb[2] - vb[0]
            self.svg_height = vb[3] - vb[1]
        else:
            self.svg_width = float(root.get('width', '100').replace('px', ''))
            self.svg_height = float(root.get('height', '100').replace('px', ''))
        
        # Find all path elements
        paths = root.findall('.//svg:path', namespace) or root.findall('.//path')
        
        for path in paths:
            d = path.get('d', '')
            if d:
                self.parse_path(d)
    
    def tokenize_path(self, d: str) -> List[str]:
        """Tokenize SVG path data properly handling numbers without spaces."""
        # First, add spaces around command letters
        d = re.sub(r'([MmLlHhVvCcSsQqTtAaZz])', r' \1 ', d)
        
        # Replace commas with spaces
        d = re.sub(r',', ' ', d)
        
        # Handle cases where we have patterns like "0.86.86" or "71.71.23"
        # This captures any number followed by a dot and another number
        # The key insight is that ".86" should be "0.86"
        
        # First handle the case where we have number.number.number
        # This replaces "71.71.23" with "71.71 0.23"
        d = re.sub(r'(\d+\.\d+)\.(\d+)', r'\1 0.\2', d)
        
        # Handle the case where we have just .number.number  
        # This replaces "0.86.86" with "0.86 0.86"
        d = re.sub(r'(\d*\.\d+)\.(\d+)', r'\1 0.\2', d)
        
        # Add spaces before minus signs that follow numbers
        d = re.sub(r'(\d)-', r'\1 -', d)
        
        # Handle exponential notation
        d = re.sub(r'(\d)e-(\d)', r'\1e-\2', d)
        d = re.sub(r'(\d)e\+(\d)', r'\1e+\2', d)
        
        # Split and filter empty strings
        tokens = [t for t in d.strip().split() if t]
        
        # Debug: Print problematic tokens
        for token in tokens:
            if token.count('.') > 1:
                print(f"Warning: Token '{token}' has multiple dots, may need manual inspection")
        
        return tokens
    
    def parse_path(self, d: str):
        """Parse SVG path data and extract cubic Bezier curves."""
        tokens = self.tokenize_path(d)
        
        i = 0
        current_pos = np.array([0.0, 0.0])
        start_pos = np.array([0.0, 0.0])
        last_control = None
        
        while i < len(tokens):
            cmd = tokens[i]
            i += 1
            
            if cmd.upper() == 'M':  # Move to
                x, y = float(tokens[i]), float(tokens[i+1])
                i += 2
                if cmd.isupper():
                    current_pos = np.array([x, y])
                else:
                    current_pos += np.array([x, y])
                start_pos = current_pos.copy()
                
                # Handle implicit line commands after M
                while i + 1 < len(tokens) and not tokens[i].isalpha():
                    x, y = float(tokens[i]), float(tokens[i+1])
                    i += 2
                    if cmd.isupper():
                        end_pos = np.array([x, y])
                    else:
                        end_pos = current_pos + np.array([x, y])
                    self.add_line_as_bezier(current_pos, end_pos)
                    current_pos = end_pos
                
            elif cmd.upper() == 'L':  # Line to
                while i + 1 < len(tokens) and not tokens[i].isalpha():
                    x, y = float(tokens[i]), float(tokens[i+1])
                    i += 2
                    if cmd.isupper():
                        end_pos = np.array([x, y])
                    else:
                        end_pos = current_pos + np.array([x, y])
                    
                    # Convert line to cubic Bezier
                    self.add_line_as_bezier(current_pos, end_pos)
                    current_pos = end_pos
                
            elif cmd.upper() == 'H':  # Horizontal line
                while i < len(tokens) and not tokens[i].isalpha():
                    x = float(tokens[i])
                    i += 1
                    if cmd.isupper():
                        end_pos = np.array([x, current_pos[1]])
                    else:
                        end_pos = np.array([current_pos[0] + x, current_pos[1]])
                    
                    self.add_line_as_bezier(current_pos, end_pos)
                    current_pos = end_pos
                    
            elif cmd.upper() == 'V':  # Vertical line
                while i < len(tokens) and not tokens[i].isalpha():
                    y = float(tokens[i])
                    i += 1
                    if cmd.isupper():
                        end_pos = np.array([current_pos[0], y])
                    else:
                        end_pos = np.array([current_pos[0], current_pos[1] + y])
                    
                    self.add_line_as_bezier(current_pos, end_pos)
                    current_pos = end_pos
                
            elif cmd.upper() == 'C':  # Cubic Bezier
                while i + 5 < len(tokens) and not tokens[i].isalpha():
                    points = []
                    for _ in range(3):
                        x, y = float(tokens[i]), float(tokens[i+1])
                        i += 2
                        if cmd.isupper():
                            points.append(np.array([x, y]))
                        else:
                            points.append(current_pos + np.array([x, y]))
                    
                    self.add_bezier(current_pos, points[0], points[1], points[2])
                    last_control = points[1]
                    current_pos = points[2]
                
            elif cmd.upper() == 'S':  # Smooth cubic Bezier
                while i + 3 < len(tokens) and not tokens[i].isalpha():
                    points = []
                    for _ in range(2):
                        x, y = float(tokens[i]), float(tokens[i+1])
                        i += 2
                        if cmd.isupper():
                            points.append(np.array([x, y]))
                        else:
                            points.append(current_pos + np.array([x, y]))
                    
                    # Calculate first control point as reflection
                    if last_control is not None:
                        control1 = 2 * current_pos - last_control
                    else:
                        control1 = current_pos
                    
                    self.add_bezier(current_pos, control1, points[0], points[1])
                    last_control = points[0]
                    current_pos = points[1]
                
            elif cmd.upper() == 'Q':  # Quadratic Bezier
                while i + 3 < len(tokens) and not tokens[i].isalpha():
                    points = []
                    for _ in range(2):
                        x, y = float(tokens[i]), float(tokens[i+1])
                        i += 2
                        if cmd.isupper():
                            points.append(np.array([x, y]))
                        else:
                            points.append(current_pos + np.array([x, y]))
                    
                    # Convert quadratic to cubic
                    self.add_quadratic_as_cubic(current_pos, points[0], points[1])
                    last_control = points[0]
                    current_pos = points[1]
                    
            elif cmd.upper() == 'T':  # Smooth quadratic Bezier
                while i + 1 < len(tokens) and not tokens[i].isalpha():
                    x, y = float(tokens[i]), float(tokens[i+1])
                    i += 2
                    if cmd.isupper():
                        end_pos = np.array([x, y])
                    else:
                        end_pos = current_pos + np.array([x, y])
                    
                    # Calculate control point as reflection
                    if last_control is not None:
                        control = 2 * current_pos - last_control
                    else:
                        control = current_pos
                    
                    self.add_quadratic_as_cubic(current_pos, control, end_pos)
                    last_control = control
                    current_pos = end_pos
                
            elif cmd.upper() == 'Z':  # Close path
                if not np.array_equal(current_pos, start_pos):
                    self.add_line_as_bezier(current_pos, start_pos)
                current_pos = start_pos
                
            elif cmd.upper() == 'A':  # Arc (skip for now, would need arc to bezier conversion)
                # Skip arc parameters (7 values)
                if i + 7 <= len(tokens):
                    i += 7
                print(f"Warning: Arc commands are not yet supported, skipping...")
            
    def add_line_as_bezier(self, start: np.ndarray, end: np.ndarray):
        """Convert a line to a cubic Bezier curve."""
        # For a line, control points are at 1/3 and 2/3 of the way
        control1 = start + (end - start) / 3.0
        control2 = start + 2.0 * (end - start) / 3.0
        self.add_bezier(start, control1, control2, end)
        
    def add_quadratic_as_cubic(self, start: np.ndarray, control: np.ndarray, end: np.ndarray):
        """Convert a quadratic Bezier to cubic."""
        # Quadratic to cubic conversion formula
        control1 = start + 2.0/3.0 * (control - start)
        control2 = end + 2.0/3.0 * (control - end)
        self.add_bezier(start, control1, control2, end)
        
    def add_bezier(self, p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray):
        """Add a cubic Bezier curve and update bounds."""
        self.bezier_curves.append((p0.copy(), p1.copy(), p2.copy(), p3.copy()))
        
        # Update bounds
        for p in [p0, p1, p2, p3]:
            self.bounds['min_x'] = min(self.bounds['min_x'], p[0])
            self.bounds['min_y'] = min(self.bounds['min_y'], p[1])
            self.bounds['max_x'] = max(self.bounds['max_x'], p[0])
            self.bounds['max_y'] = max(self.bounds['max_y'], p[1])
            
    def transform_coordinates(self, point: np.ndarray) -> np.ndarray:
        """Transform SVG coordinates to GLSL coordinates."""
        # Avoid division by zero
        width = self.bounds['max_x'] - self.bounds['min_x']
        height = self.bounds['max_y'] - self.bounds['min_y']
        
        if width == 0 or height == 0:
            return np.array([0.0, 0.0])
        
        # First normalize to [0, 1]
        x = (point[0] - self.bounds['min_x']) / width
        y = (point[1] - self.bounds['min_y']) / height
        
        # SVG has Y pointing down, GLSL has Y pointing up
        y = 1.0 - y
        
        if self.center:
            # Center around origin
            x = (x - 0.5) * 2.0
            y = (y - 0.5) * 2.0
        
        # Apply scale
        x *= self.scale
        y *= self.scale
        
        return np.array([x, y])
        
    def generate_glsl_code(self) -> str:
        """Generate GLSL code for all Bezier curves."""
        code = []
        
        # Add header comment
        code.append(f"// Generated from SVG file: {self.svg_file}")
        code.append(f"// Total curves: {len(self.bezier_curves)}")
        code.append("")
        
        # Add the distance calculation code
        code.append("float dist = 1e10;")
        code.append("")
        
        # Generate code for each curve
        for i, (p0, p1, p2, p3) in enumerate(self.bezier_curves):
            # Transform coordinates
            p0_t = self.transform_coordinates(p0)
            p1_t = self.transform_coordinates(p1)
            p2_t = self.transform_coordinates(p2)
            p3_t = self.transform_coordinates(p3)
            
            code.append(f"// Curve {i}")
            code.append(f"float curve{i} = sdBezierCubic(p, ")
            code.append(f"    vec2({p0_t[0]:.6f}, {p0_t[1]:.6f}),")
            code.append(f"    vec2({p1_t[0]:.6f}, {p1_t[1]:.6f}),")
            code.append(f"    vec2({p2_t[0]:.6f}, {p2_t[1]:.6f}),")
            code.append(f"    vec2({p3_t[0]:.6f}, {p3_t[1]:.6f}));")
            code.append(f"dist = min(dist, curve{i});")
            code.append("")
        
        return '\n'.join(code)

def main():
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert SVG to GLSL cubic Bezier SDF')
    parser.add_argument('svg_file', help='Path to SVG file')
    parser.add_argument('--scale', type=float, default=1.0, help='Scale factor')
    parser.add_argument('--no-center', action='store_true', help='Don\'t center the shape')
    parser.add_argument('--output', '-o', help='Output file (default: print to stdout)')
    
    args = parser.parse_args()
    
    try:
        converter = SVGToGLSLBezier(args.svg_file, scale=args.scale, center=not args.no_center)
        converter.parse_svg()
        
        output = converter.generate_glsl_code()
        
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Output written to {args.output}")
        else:
            print(output)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()