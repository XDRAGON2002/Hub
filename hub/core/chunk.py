from hub.core.index.index import Index
from hub.core.storage.cachable import Cachable
from hub.core.compression import decompress_array
from typing import List, Optional, Sequence, Tuple, Union
import numpy as np
from io import BytesIO
from math import ceil

from hub.core.meta.encode.shape import ShapeEncoder
from hub.core.meta.encode.byte_positions import BytePositionsEncoder


class Chunk(Cachable):
    """A Chunk should only be provided data to store in bytes form, alongside the meta information (like shape/num_samples). The
    byte ranges are to be generated by this chunk, and it can also spawn new chunks as needed."""

    def __init__(self, id: int, max_data_bytes: int, min_data_bytes_target: int):
        self.id = id

        # no need to load these encoders, if `frombuffer` is called, it will override them.
        self.index_shape_encoder = ShapeEncoder()
        self.index_byte_range_encoder = BytePositionsEncoder()

        self.max_data_bytes = max_data_bytes
        self.min_data_bytes_target = min_data_bytes_target

        self._data: Union[bytearray, memoryview] = bytearray()

        self.num_new_samples = 0

    @property
    def memoryview_data(self):
        return memoryview(self._data)

    @property
    def num_data_bytes(self):
        return len(self._data)

    @property
    def is_under_min_space(self):
        return self.num_data_bytes < self.min_data_bytes_target

    def has_space_for(self, num_bytes: int):
        return self.num_data_bytes + num_bytes < self.max_data_bytes

    def append(
        self,
        incoming_buffer: memoryview,
    ) -> Tuple["Chunk"]:
        # TODO: docstring

        incoming_num_bytes = len(incoming_buffer)

        if not self.has_space_for(incoming_num_bytes):
            # TODO: exceptions.py
            raise Exception(
                f"Chunk does not have space for the incoming bytes ({incoming_num_bytes})."
            )

        # note: incoming_num_bytes can be 0 (empty sample)
        self._data += incoming_buffer
        self.num_new_samples += 1

    def update_headers(
        self, incoming_num_bytes: int, num_samples: int, sample_shape: Sequence[int]
    ):
        # TODO: docstring

        if self.num_new_samples <= 0:
            # TODO: exceptions.py
            raise Exception("Cannot update headers when no new data was added.")

        num_bytes_per_sample = incoming_num_bytes // num_samples
        self.index_shape_encoder.add_shape(sample_shape, num_samples)
        self.index_byte_range_encoder.add_byte_position(
            num_bytes_per_sample, num_samples
        )

    def get_sample(
        self, local_sample_index: int, dtype: np.dtype, expect_compressed=False
    ) -> np.ndarray:
        shape = self.index_shape_encoder[local_sample_index]
        sb, eb = self.index_byte_range_encoder.get_byte_position(local_sample_index)
        buffer = self.memoryview_data[sb:eb]
        if expect_compressed:
            return decompress_array(buffer, shape)
        else:
            return np.frombuffer(buffer, dtype=dtype).reshape(shape)

    def __len__(self):
        # this should not call `tobytes` because it will be slow. should calculate the amount of bytes this chunk takes up in total. (including headers)

        shape_nbytes = self.index_shape_encoder.nbytes
        range_nbytes = self.index_byte_range_encoder.nbytes
        error_bytes = 32  # to account for any extra delimeters/stuff that `np.savez` may create in excess

        return shape_nbytes + range_nbytes + self.num_data_bytes + error_bytes

    def tobytes(self) -> memoryview:
        out = BytesIO()

        # TODO: for fault tolerance, we should have a chunk store the ID for the next chunk
        # TODO: in case the index chunk meta gets pwned (especially during a potentially failed transform job merge)
        # TODO: store version in chunk

        np.savez(
            out,
            index_shape_encoder=self.index_shape_encoder,
            index_byte_range_encoder=self.index_byte_range_encoder,
            data=self.memoryview_data,
        )
        out.seek(0)
        return out.getbuffer()

    @classmethod
    def frombuffer(cls, buffer: bytes):
        raise NotImplementedError
