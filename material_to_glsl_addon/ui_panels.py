import bpy
from bpy.types import Panel


class MATERIAL_PT_glsl_export(Panel):
    """Material N-panel for GLSL export"""
    bl_label = "GLSL Export"
    bl_idname = "MATERIAL_PT_glsl_export"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Material"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        return (context.space_data.type == 'NODE_EDITOR' and 
                context.space_data.tree_type == 'ShaderNodeTree' and
                context.material is not None)
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon='SCRIPT')
    
    def draw(self, context):
        layout = self.layout
        material = context.material
        
        if not material:
            layout.label(text="No active material", icon='ERROR')
            return
        
        if not material.use_nodes:
            layout.label(text="Material doesn't use nodes", icon='INFO')
            row = layout.row()
            row.operator("material.new", text="New Material", icon='ADD')
            return
        
        if not material.node_tree:
            layout.label(text="No node tree found", icon='ERROR')
            return
        
        # Check if material has valid output
        has_output = False
        output_connected = False
        
        for node in material.node_tree.nodes:
            if node.type == 'OUTPUT_MATERIAL':
                has_output = True
                if node.inputs.get('Surface') and node.inputs.get('Surface').is_linked:
                    output_connected = True
                break
        
        # Material info section
        box = layout.box()
        col = box.column(align=True)
        col.label(text=f"Material: {material.name}", icon='MATERIAL')
        col.label(text=f"Nodes: {len(material.node_tree.nodes)}")
        
        if not has_output:
            col.label(text="No Material Output node", icon='ERROR')
        elif not output_connected:
            col.label(text="Material Output not connected", icon='ERROR')
        else:
            col.label(text="Ready for export", icon='CHECKMARK')
        
        # Export buttons
        layout.separator()
        
        col = layout.column(align=True)
        col.scale_y = 1.2
        
        # Main export button
        if has_output and output_connected:
            col.operator("material.export_glsl", text="Export to GLSL File", icon='EXPORT')
            col.operator("material.preview_glsl", text="Preview GLSL Code", icon='TEXT')
        else:
            col.enabled = False
            col.operator("material.export_glsl", text="Export to GLSL File", icon='EXPORT')
            col.operator("material.preview_glsl", text="Preview GLSL Code", icon='TEXT')
        
        # Info section
        layout.separator()
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Supported Nodes:", icon='INFO')
        
        # Create a scrollable list of supported nodes
        col.label(text="• Input: Value, RGB")
        col.label(text="• Texture: Image Texture")
        col.label(text="• Color: Bright/Contrast, Gamma, Mix RGB")
        col.label(text="• Vector: Normal Map, Mapping")
        col.label(text="• Converter: Math, Vector Math")
        col.label(text="• Converter: Combine/Separate RGB/XYZ/HSV")
        col.label(text="• Converter: RGB to BW, Map Range")
        col.label(text="• Shader: Principled BSDF, Emission")
        col.label(text="• Group nodes")


def register():
    bpy.utils.register_class(MATERIAL_PT_glsl_export)


def unregister():
    bpy.utils.unregister_class(MATERIAL_PT_glsl_export)
