################################################################################
# Copyright (c) 2011-2016, National Research Foundation (Square Kilometre Array)
#
# Licensed under the BSD 3-Clause License (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy
# of the License at
#
#   https://opensource.org/licenses/BSD-3-Clause
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################

"""Base class for accessing a store of chunks (i.e. N-dimensional arrays)."""


class ChunkStore(object):
    """Base class for accessing a store of chunks (i.e. N-dimensional arrays).

    A *chunk* is a simple (i.e. unit-stride) slice of an N-dimensional array
    known as its *parent array*. The array is identified by a string name,
    while the chunk within the array is identified by a sequence of slice
    objects which may be used to extract the chunk from the array. The array
    is a :class:`numpy.ndarray` object with an associated *dtype*.

    The basic idea is that the chunk store contains multiple arrays addressed
    by name. The list of available arrays and all array metadata (shape,
    chunks and dtype) are stored elsewhere. The metadata is used to identify
    chunks, while the chunk store takes care of storing and retrieving
    bytestrings of actual chunk data. These are packaged back into NumPy
    arrays for the user. Each array can only be stored once, with a unique
    chunking scheme (i.e. different chunking of the same data is disallowed).

    The naming scheme for arrays and chunks is reasonably generic but has
    some restrictions:

    - Names are treated like paths with components and a standard separator
    - The chunk name is formed by appending a string of indices to the array name
    - It is discouraged to have an array name that is a prefix of another name
    - Each chunk store has its own restrictions on valid characters in names:
      some treat names as URLs while others treat them as filenames. A safe
      choice for name components should be the valid characters for S3 buckets:

      VALID_BUCKET = re.compile(r'^[a-zA-Z0-9.\-_]{1,255}$')
    """

    def get(self, array_name, slices, dtype):
        """Get chunk from the store.

        Parameters
        ----------
        array_name : string
            Identifier of parent array `x` of chunk
        slices : sequence of slice objects
            Identifier of individual chunk, to be extracted as `x[slices]`
        dtype : :class:`numpy.dtype` object
            Dtype of array `x`

        Returns
        -------
        chunk : :class:`numpy.ndarray` object
            Chunk as ndarray with dtype `dtype` and shape dictated by `slices`

        Raises
        ------
        OSError
            If requested chunk was not found in store (or connection failed)
        ValueError
            If requested `dtype` does not match underlying parent array dtype
        """
        raise NotImplementedError

    def put(self, array_name, slices, chunk):
        """Put chunk into the store.

        Parameters
        ----------
        array_name : string
            Identifier of parent array `x` of chunk
        slices : sequence of slice objects
            Identifier of individual chunk, to be extracted as `x[slices]`
        chunk : :class:`numpy.ndarray` object
            Chunk as ndarray with shape commensurate with `slices`
        """
        raise NotImplementedError

    NAME_SEP = '/'
    # Width sufficient to store any dump / channel / corrprod index for MeerKAT
    NAME_INDEX_WIDTH = 5

    @classmethod
    def join(cls, *names):
        """Join components of chunk name with supported separator."""
        return cls.NAME_SEP.join(names)

    @classmethod
    def split(cls, name, maxsplit=-1):
        """Split chunk name into components based on supported separator."""
        return name.split(cls.NAME_SEP, maxsplit)

    @classmethod
    def chunk_name(cls, array_name, slices):
        """Form chunk name from array name and `slices` chunk identifier."""
        index = [s.start for s in slices]
        idx = '_'.join(["{:0{width}d}".format(i, width=cls.NAME_INDEX_WIDTH)
                        for i in index])
        return ChunkStore.join(array_name, idx)


class DictChunkStore(ChunkStore):
    """A store of chunks (i.e. N-dimensional arrays) based on a dict of arrays.

    This interprets all keyword arguments as NumPy arrays and stores them in
    an `arrays` dict. Each array is identified by its corresponding keyword.
    """

    def __init__(self, **kwargs):
        self.arrays = kwargs

    def get(self, array_name, slices, dtype):
        """See the docstring of :meth:`ChunkStore.get`."""
        try:
            chunk = self.arrays[array_name][slices]
        except KeyError:
            raise OSError('Array %r not found in DictChunkStore which has %s' %
                          (array_name, self.arrays.keys()))
        if dtype != chunk.dtype:
            raise ValueError('Requested dtype %s differs from chunk dtype %s'
                             % (dtype, chunk.dtype))
        return chunk

    def put(self, array_name, slices, chunk):
        """See the docstring of :meth:`ChunkStore.put`."""
        self.get(array_name, slices, chunk.dtype)[:] = chunk

    get.__doc__ = ChunkStore.get.__doc__
    put.__doc__ = ChunkStore.put.__doc__
