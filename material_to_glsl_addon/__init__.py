bl_info = {
    "name": "Material to GLSL Exporter",
    "author": "Based on Bentschi's Blender-GLSL-translator",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "Material Properties > GLSL Export",
    "description": "Export material node trees as GLSL fragment shaders",
    "warning": "",
    "doc_url": "",
    "category": "Material",
}

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator, Panel
import os

from . import material_nodes_compiler
from . import exporter_operators
from . import ui_panels

def register():
    exporter_operators.register()
    ui_panels.register()
    
def unregister():
    ui_panels.unregister()
    exporter_operators.unregister()

if __name__ == "__main__":
    register()
