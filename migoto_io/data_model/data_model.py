import time
import json
import numpy
import copy
import bpy

from typing import Tuple, List, Dict, Optional, Union

from .dxgi_format import DXGIFormat, DXGIType
from .byte_buffer import Semantic, AbstractSemantic, BufferSemantic, BufferLayout, NumpyBuffer
from .data_extractor import BlenderDataExtractor
from .data_importer import BlenderDataImporter


class DataModel:
    flip_winding: bool = False
    flip_normal: bool = False
    flip_tangent: bool = False
    flip_bitangent_sign: bool = False
    flip_texcoord_v: bool = False

    data_extractor = BlenderDataExtractor()
    buffers_format: Dict[str, BufferLayout] = {}
    semantic_converters: Dict[AbstractSemantic, List[callable]] = {}
    format_converters: Dict[AbstractSemantic, List[callable]] = {}

    blender_data_formats: Dict[Semantic, DXGIFormat] = {
        Semantic.Index: DXGIFormat.R32_UINT,
        Semantic.VertexId: DXGIFormat.R32_UINT,
        Semantic.Normal: DXGIFormat.R16G16B16_FLOAT,
        Semantic.Tangent: DXGIFormat.R16G16B16_FLOAT,
        Semantic.BitangentSign: DXGIFormat.R16_FLOAT,
        Semantic.Color: DXGIFormat.R32G32B32A32_FLOAT,
        Semantic.TexCoord: DXGIFormat.R32G32_FLOAT,
        Semantic.Position: DXGIFormat.R32G32B32_FLOAT,
        Semantic.Blendindices: DXGIFormat.R32_UINT,
        Semantic.Blendweight: DXGIFormat.R32_FLOAT,
        Semantic.ShapeKey: DXGIFormat.R32G32B32_FLOAT,
    }

    def set_data(self, 
                 obj: bpy.types.Mesh, 
                 mesh: bpy.types.Mesh, 
                 index_buffer: NumpyBuffer,
                 vertex_buffer: NumpyBuffer,
                 vg_remap: Optional[numpy.ndarray],
                 mirror_mesh: bool = False):

        # Copy default converters
        semantic_converters, format_converters = {}, {}
        semantic_converters.update(self.semantic_converters)
        format_converters.update(self.format_converters)

        # Add generic converters

        # Swap first and third index for each triangle in index buffer
        flip_winding = self.flip_winding if not mirror_mesh else not self.flip_winding
        if flip_winding:
            self._insert_converter(semantic_converters, AbstractSemantic(Semantic.Index), self.converter_rgb_to_bgr_vector)

        for semantic in vertex_buffer.layout.semantics:
            # Skip tangents import, we'll recalc them on export
            if semantic.abstract.enum in [Semantic.Tangent, Semantic.BitangentSign]:
                continue
            # Invert X coord of every vector in arrays required to mirror mesh
            if mirror_mesh and semantic.abstract.enum in [Semantic.Position, Semantic.ShapeKey, Semantic.Normal]:
                self._insert_converter(semantic_converters, semantic.abstract, self.converter_mirror_vector)
            # Flip V component of UV maps
            if self.flip_texcoord_v and semantic.abstract.enum == Semantic.TexCoord:
                self._insert_converter(semantic_converters, semantic.abstract, self.converter_flip_texcoord_v)
            # Flip normals
            if self.flip_normal and semantic.abstract.enum == Semantic.Normal:
                self._insert_converter(semantic_converters, semantic.abstract, self.converter_flip_vector)
            # Remap indicies of VG groups
            if vg_remap is not None:
                if semantic.abstract.enum == Semantic.Blendindices:
                    self._insert_converter(semantic_converters, semantic.abstract, lambda data: vg_remap[data])
            # Auto-resize second dimension of data array to match Blender format
            if semantic.abstract.enum not in [Semantic.Blendindices, Semantic.Blendweight]:
                blender_num_values = self.blender_data_formats[semantic.abstract.enum].get_num_values()
                if semantic.get_num_values() != blender_num_values:
                    converter = lambda data, width=blender_num_values: self.converter_resize_second_dim(data, width)
                    self._insert_converter(format_converters, semantic.abstract, converter)

        data_importer = BlenderDataImporter()

        data_importer.set_data(obj, mesh, index_buffer, vertex_buffer, semantic_converters, format_converters)

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

        return buffers, len(vertex_buffer)

    def build_buffers(self,
                      index_data: numpy.ndarray, 
                      vertex_buffer: NumpyBuffer, 
                      excluded_buffers: List[str],
                      buffers_format: Dict[Semantic, DXGIFormat]) -> Dict[str, NumpyBuffer]:
        
        start_time = time.time()

        result = {}
        for buffer_name, buffer_layout in buffers_format.items():
            buffer = None
            if buffer_name in excluded_buffers:
                continue
            for semantic in buffer_layout.semantics:
                if semantic.abstract.enum == Semantic.ShapeKey:
                    continue
                if semantic.abstract.enum == Semantic.Index:
                    data = index_data
                else:
                    data = vertex_buffer.get_field(semantic.get_name())
                if buffer is None:
                    buffer = NumpyBuffer(buffer_layout, size=len(data))
                buffer.import_semantic_data(data, semantic)
            if buffer is None:
                continue
            result[buffer_name] = buffer

        print(f'Buffers build time: {time.time() - start_time :.3f}s ({len(result)} buffers)')

        return result

    def export_data(self, 
                    context: bpy.types.Context, 
                    collection: bpy.types.Collection, 
                    mesh: bpy.types.Mesh, 
                    excluded_buffers: List[str], 
                    buffers_format: Dict[Semantic, DXGIFormat],
                    mirror_mesh: bool = False):
        
        export_layout, fetch_loop_data = self.make_export_layout(buffers_format, excluded_buffers)
        index_data, vertex_buffer = self.get_mesh_data(context, collection, mesh, export_layout, fetch_loop_data, mirror_mesh)
        return index_data, vertex_buffer

    def make_export_layout(self, 
                           buffers_format: Dict[Semantic, DXGIFormat],
                           excluded_buffers: List[str]):
        fetch_loop_data = False

        if len(excluded_buffers) == 0:
            fetch_loop_data = True
        else:
            for buffer_name, buffer_layout in buffers_format.items():
                if buffer_name not in excluded_buffers:
                    for semantic in buffer_layout.semantics:
                        if semantic.abstract.enum in self.data_extractor.blender_loop_semantics:
                            fetch_loop_data = True
                            break

        export_layout = BufferLayout([])
        for buffer_name, buffer_layout in buffers_format.items():
            exclude_buffer = buffer_name in excluded_buffers
            for semantic in buffer_layout.semantics:
                if exclude_buffer and semantic.abstract.enum not in self.data_extractor.blender_loop_semantics:
                    continue
                if semantic.abstract.enum == Semantic.ShapeKey:
                    continue
                export_layout.add_element(semantic)

        return export_layout, fetch_loop_data

    def get_mesh_data(self, 
                      context: bpy.types.Context, 
                      collection: bpy.types.Collection,
                      mesh: bpy.types.Mesh, 
                      export_layout: BufferLayout, 
                      fetch_loop_data: bool, 
                      mirror_mesh: bool = False):
        
        vertex_ids_cache, cache_vertex_ids = None, False

        flip_winding = self.flip_winding if not mirror_mesh else not self.flip_winding
        flip_bitangent_sign = self.flip_bitangent_sign if not mirror_mesh else not self.flip_bitangent_sign

        if not fetch_loop_data:
            if collection != context.scene.wwmi_tools_settings.vertex_ids_cached_collection:
                # Cache contains data for different object and must be cleared
                context.scene.wwmi_tools_settings.vertex_ids_cache = ''
                fetch_loop_data = True
                cache_vertex_ids = True
            else:
                # Partial export is enabled
                if context.scene.wwmi_tools_settings.vertex_ids_cache:
                    # Valid vertex ids cache exists, lets load it
                    vertex_ids_cache = numpy.array(json.loads(context.scene.wwmi_tools_settings.vertex_ids_cache))
                else:
                    # Cache is clear, we'll have to fetch loop data once 
                    fetch_loop_data = True
                    cache_vertex_ids = True
        elif context.scene.wwmi_tools_settings.vertex_ids_cache:
            # We're going to fetch loop data, cache must be cleared
            context.scene.wwmi_tools_settings.vertex_ids_cache = ''

        # Copy default converters
        semantic_converters, format_converters = {}, {}
        semantic_converters.update(copy.deepcopy(self.semantic_converters))
        format_converters.update(copy.deepcopy(self.format_converters))

        # Add generic converters
        for semantic in export_layout.semantics:
            # Flip normals
            if self.flip_normal and semantic.abstract.enum == Semantic.Normal:
                self._insert_converter(semantic_converters, semantic.abstract, self.converter_flip_vector)
            # Flip tangents
            if self.flip_tangent and semantic.abstract.enum == Semantic.Tangent:
                self._insert_converter(semantic_converters, semantic.abstract, self.converter_flip_vector)
            # Flip bitangent sign
            if flip_bitangent_sign and semantic.abstract.enum == Semantic.BitangentSign:
                self._insert_converter(semantic_converters, semantic.abstract, self.converter_flip_vector)
            # Invert X coord of every vector in arrays required to mirror mesh
            if mirror_mesh and semantic.abstract.enum in [Semantic.Position, Semantic.Normal, Semantic.Tangent]:
                    self._insert_converter(semantic_converters, semantic.abstract, self.converter_mirror_vector)
            # Flip V component of UV maps
            if self.flip_texcoord_v and semantic.abstract.enum == Semantic.TexCoord:
                self._insert_converter(semantic_converters, semantic.abstract, self.converter_flip_texcoord_v)

        # If vertex_ids_cache is *not* None, get_data method will skip loop data fetching
        index_buffer, vertex_buffer = self.data_extractor.get_data(
            mesh, export_layout, self.blender_data_formats, semantic_converters, format_converters, vertex_ids_cache, flip_winding=flip_winding)

        if cache_vertex_ids:
            # As vertex_ids_cache is None, get_data fetched loop data for us and we can cache vertex ids
            vertex_ids = vertex_buffer.get_field(AbstractSemantic(Semantic.VertexId).get_name())
            context.scene.wwmi_tools_settings.vertex_ids_cache = json.dumps(vertex_ids.tolist())
            context.scene.wwmi_tools_settings.vertex_ids_cached_collection = collection

        return index_buffer, vertex_buffer

    @staticmethod
    def converter_flip_vector(data: numpy.ndarray) -> numpy.ndarray:
        return -data
    
    @staticmethod
    def converter_mirror_vector(data: numpy.ndarray) -> numpy.ndarray:
        data[:, 0] *= -1
        return data
    
    @staticmethod
    def converter_flip_texcoord_v(data: numpy.ndarray) -> numpy.ndarray:
        if data.dtype != numpy.float32:
            data = data.astype(numpy.float32)
        data[:, 1] = 1.0 - data[:, 1]
        return data
    
    @staticmethod
    def converter_reshape_second_dim(data: numpy.ndarray, width: int) -> numpy.ndarray:
        """
        Restructures 2-dim numpy array's 2-nd dimension to given width by regrouping values
        Automatically converts 1-dim array to 2-dim with given width (every `width` elements are getting wrapped in array)
        """
        data = numpy.reshape(data, (-1, width))
        return data
    
    @staticmethod
    def converter_resize_second_dim(data: numpy.ndarray, width: int, fill: Union[int, float] = 0) -> numpy.ndarray:
        """
        Restructures 2-dim numpy array's 2-nd dimension to given width by padding or dropping values
        Automatically converts 1-dim array to 2-dim with given width (every element is getting padded to width)
        """
        num_dimensions, num_values = data.ndim, data.shape[1] if data.ndim > 1 else 0
        if num_dimensions != 2 or num_values != width:
            if num_values < width:
                if num_dimensions == 1:
                    # Array is 1-dim one and requires conversion to 2-dim
                    num_values = 1
                    # Wrap every value into array
                    data = data.reshape(-1, 1)
                    if width == 1:
                        # Requested width is also 1, lets exit early
                        return data
                # Change the size of 2-nd dimension
                new_shape = list(data.shape)
                new_shape[1] = width
                if fill == 1:
                    new_data = numpy.ones(dtype=data.dtype, shape=new_shape)
                else:
                    new_data = numpy.zeros(dtype=data.dtype, shape=new_shape)
                    if fill != 0:
                        new_data.fill(fill)
                # Fill empty array with data
                new_data[:, 0:num_values] = data
                return new_data
            else:
                # Trim excessive values to given width
                return data[:, :-(num_values - width)]
        else:
            # Array structure
            return data

    @staticmethod
    def converter_rgb_to_bgr_vector(data: numpy.ndarray) -> numpy.ndarray:
        data = data.flatten()
        # Create array from 0 to len
        # Creates [0, 1, 2, 3, 4, 5] for len=6
        indices = numpy.arange(len(data))
        # Convert flat array to 2-dim array of index triads
        # [0, 1, 2, 3, 4, 5] -> [[0, 1, 2], [3, 4, 5]]
        indices = indices.reshape(-1, 3)
        # Swap every first with every third element of index triads
        # [[0, 1, 2], [3, 4, 5]] -> [[2, 1, 0], [5, 4, 3]]
        indices[:, [0, 2]] = indices[:, [2, 0]]
        # Destroy first dimension so we could use the array as index for loop data array
        # [[2, 1, 0], [5, 4, 3]] -> [2, 1, 0, 5, 4, 3]
        indices = indices.flatten()
        # Swap every first with every third element of loop data array
        data = data[indices]

        data = data.reshape(-1, 3)

        return data

    @staticmethod
    def _insert_converter(converters, abstract_semantic: AbstractSemantic, converter: callable):
        if abstract_semantic not in converters.keys():
            converters[abstract_semantic] = []
        converters[abstract_semantic].insert(0, converter)
