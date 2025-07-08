# Blender to GLSL Material Translator

A Blender addon that translates Blender material node trees into GLSL shader code.

## Features

- Convert Blender material nodes to GLSL fragment shaders
- Support for common material nodes
- Export functionality integrated into Blender's UI
- HTML shader viewer for testing generated GLSL code

## Installation

1. Download the addon files
2. In Blender, go to Edit > Preferences > Add-ons
3. Click "Install..." and select the addon folder
4. Enable the "Material to GLSL" addon

## Usage

1. Create or select a material with node setup in Blender
2. Use the export options in the Shader Editor or Properties panel
3. The addon will generate corresponding GLSL code
4. Use the included HTML viewer to test the generated shaders

## Files

- `material_to_glsl_addon/` - Main addon directory
  - `__init__.py` - Addon initialization
  - `material_nodes_compiler.py` - Core node compilation logic
  - `exporter_operators.py` - Export operators
  - `ui_panels.py` - UI panel definitions
- `shader_viewer.html` - HTML viewer for testing GLSL shaders
- `create_zip.ps1` - PowerShell script to package the addon
- `nodes_test.blend` - Test Blender file with sample materials

## Development

To package the addon for distribution, run:

```powershell
.\create_zip.ps1
```

This will create a zip file ready for installation in Blender.

## License

[Add your license information here]
