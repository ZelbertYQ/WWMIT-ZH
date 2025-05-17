import time
import re
import numpy
import bpy

from typing import Tuple, List, Dict, Optional


from ...migoto_io.data_model.dxgi_format import DXGIFormat, DXGIType
from ...migoto_io.data_model.byte_buffer import Semantic, AbstractSemantic, BufferSemantic, BufferLayout, NumpyBuffer
from ...migoto_io.data_model.data_model import DataModel


class DataModelWWMI(DataModel):
    buffers_format: Dict[str, BufferLayout] = {
        'Index': BufferLayout([
            BufferSemantic(AbstractSemantic(Semantic.Index), DXGIFormat.R32_UINT, stride=12)
        ]),
        'Position': BufferLayout([
            BufferSemantic(AbstractSemantic(Semantic.Position, 0), DXGIFormat.R32G32B32_FLOAT)
        ]),
        'Blend': BufferLayout([
            BufferSemantic(AbstractSemantic(Semantic.Blendindices, 0), DXGIFormat.R8_UINT, stride=4),
            BufferSemantic(AbstractSemantic(Semantic.Blendweight, 0), DXGIFormat.R8_UINT, stride=4),
        ]),
        'Vector': BufferLayout([
            BufferSemantic(AbstractSemantic(Semantic.Tangent, 0), DXGIFormat.R8G8B8A8_SNORM),
            BufferSemantic(AbstractSemantic(Semantic.Normal, 0), DXGIFormat.R8G8B8_SNORM),
            BufferSemantic(AbstractSemantic(Semantic.BitangentSign, 0), DXGIFormat.R8_SNORM),
        ]),
        'Color': BufferLayout([
            BufferSemantic(AbstractSemantic(Semantic.Color, 0), DXGIFormat.R8G8B8A8_UNORM),
        ]),
        'TexCoord': BufferLayout([
            BufferSemantic(AbstractSemantic(Semantic.TexCoord, 0), DXGIFormat.R16G16_FLOAT),
            BufferSemantic(AbstractSemantic(Semantic.Color, 1), DXGIFormat.R16G16_UNORM),
            BufferSemantic(AbstractSemantic(Semantic.TexCoord, 1), DXGIFormat.R16G16_FLOAT),
            BufferSemantic(AbstractSemantic(Semantic.TexCoord, 2), DXGIFormat.R16G16_FLOAT),
        ]),
        'ShapeKeyOffset': BufferLayout([
            BufferSemantic(AbstractSemantic(Semantic.ShapeKey, 0), DXGIFormat.R32G32B32A32_UINT),
        ]),
        'ShapeKeyVertexId': BufferLayout([
            BufferSemantic(AbstractSemantic(Semantic.ShapeKey, 1), DXGIFormat.R32_UINT),
        ]),
        'ShapeKeyVertexOffset': BufferLayout([
            BufferSemantic(AbstractSemantic(Semantic.ShapeKey, 2), DXGIFormat.R16_FLOAT),
        ]),
    }

    def __init__(self):
        self.flip_winding = True
        self.flip_bitangent_sign = True
        self.flip_texcoord_v = True
        self.semantic_converters = {
            # Reshape flat array [[0,0,0],[0,0,0]] to [[0,0,0,1],[0,0,0,1]]
            AbstractSemantic(Semantic.Tangent, 0): [lambda data: self.converter_resize_second_dim(data, 4, fill=1)],
        }
        self.format_converters = {
            # Reshape flat array [0,1,2,3,4,5] to [[0,1,2],[3,4,5]]
            AbstractSemantic(Semantic.Index): [lambda data: self.converter_reshape_second_dim(data, 3)],
            # Trim color array [[1,1,0,0],[1,1,0,0]] to [[1,1],[1,1]]
            AbstractSemantic(Semantic.Color, 1): [lambda data: self.converter_resize_second_dim(data, 2)],
        }

    def get_data(self, 
                 context: bpy.types.Context, 
                 collection: bpy.types.Collection, 
                 obj: bpy.types.Object, 
                 mesh: bpy.types.Mesh, 
                 excluded_buffers: List[str],
                 buffers_format: Optional[Dict[Semantic, DXGIFormat]] = None,
                 mirror_mesh: bool = False) -> Tuple[Dict[str, NumpyBuffer], int]:
        
        if buffers_format is None:
            buffers_format = self.buffers_format

        index_data, vertex_buffer = self.export_data(context, collection, mesh, excluded_buffers, buffers_format, mirror_mesh)

        buffers = self.build_buffers(index_data, vertex_buffer, excluded_buffers, buffers_format)

        vertex_ids = vertex_buffer.get_field(AbstractSemantic(Semantic.VertexId).get_name())

        shapekeys = self.export_shapekeys(obj, vertex_ids, excluded_buffers, mirror_mesh)
        buffers.update(shapekeys)

        return buffers, len(vertex_ids)

    def export_shapekeys(self, 
                         obj: bpy.types.Object,  
                         vertex_ids: numpy.ndarray, 
                         excluded_buffers: List[str],
                         mirror_mesh: bool = False) -> Dict[str, NumpyBuffer]:
        
        start_time = time.time()

        if obj.data.shape_keys is None or len(getattr(obj.data.shape_keys, 'key_blocks', [])) == 0:
            print(f'No shapekeys found to process!')
            return {}

        buffers = {}
        for buffer_name, buffer_layout in self.buffers_format.items():
            if buffer_name in excluded_buffers:
                continue
            for semantic in buffer_layout.semantics:
                if semantic.abstract.enum == Semantic.ShapeKey:
                    buffers[buffer_name] = NumpyBuffer(buffer_layout)
                    break

        if len(buffers) == 0:
            print(f'Skipped shapekeys fetching!')
            return {}

        shapekey_offsets, shapekey_vertex_ids, shapekey_vertex_offsets = [], [], []

        shapekey_pattern = re.compile(r'.*(?:deform|custom)[_ -]*(\d+).*')
        shapekey_ids = {}
        
        for shapekey in obj.data.shape_keys.key_blocks:
            match = shapekey_pattern.findall(shapekey.name.lower())
            if len(match) == 0:
                continue
            shapekey_id = int(match[0])
            shapekey_ids[shapekey_id] = shapekey.name

        shapekeys = self.data_extractor.get_shapekey_data(obj, names_filter=list(shapekey_ids.values()), deduct_basis=True)

        shapekey_verts_count = 0
        for group_id in range(128):

            shapekey = shapekeys.get(shapekey_ids.get(group_id, -1), None)
            if shapekey is None or not (-0.00000001 > numpy.min(shapekey) or numpy.max(shapekey) > 0.00000001):
                shapekey_offsets.extend([shapekey_verts_count if shapekey_verts_count != 0 else 0])
                continue

            shapekey_offsets.extend([shapekey_verts_count])

            shapekey = shapekey[vertex_ids]

            shapekey_vert_ids = numpy.where(numpy.any(shapekey != 0, axis=1))[0]

            shapekey_vertex_ids.extend(shapekey_vert_ids)
            shapekey_vertex_offsets.extend(shapekey[shapekey_vert_ids])
            shapekey_verts_count += len(shapekey_vert_ids)
            
        if len(shapekey_vertex_ids) == 0:
            return {}

        shapekey_offsets = numpy.array(shapekey_offsets)
        
        shapekey_vertex_offsets_np = numpy.zeros(len(shapekey_vertex_offsets), dtype=(numpy.float16, 6))
        # shapekey_vertex_offsets = numpy.zeros(len(shapekey_vertex_offsets), dtype=numpy.float16)
        shapekey_vertex_offsets_np[:, 0:3] = shapekey_vertex_offsets

        if mirror_mesh:
            shapekey_vertex_offsets_np[:, 0] *= -1

        shapekey_vertex_ids = numpy.array(shapekey_vertex_ids, dtype=numpy.uint32)

        buffers['ShapeKeyOffset'].set_data(shapekey_offsets)
        buffers['ShapeKeyVertexId'].set_data(shapekey_vertex_ids)
        buffers['ShapeKeyVertexOffset'].set_data(shapekey_vertex_offsets_np)

        print(f'Shape Keys formatting time: {time.time() - start_time :.3f}s ({len(shapekey_vertex_ids)} shapekeyed vertices)')

        return buffers
