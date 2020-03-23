from abc import ABCMeta, abstractmethod
import numpy as np
import astropy.units as u
from .exceptions import (
    UnitError, DimError, DataTypeError, RequiredMissing, ShapeError,
)


class Column(metaclass=ABCMeta):
    '''Base class for the column descriptors'''

    def __init__(self, unit=None, required=True):
        self.required = required
        self.unit = unit
        self.name = None

    def __get__(self, instance, owner=None):
        # class attribute access
        if instance is None:
            return self

        return instance.__data__.get(self.name)

    def __set__(self, instance, value):
        instance.__data__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name

    def __delete__(self, instance):
        '''clear data of this column'''
        if self.name in instance.__data__:
            del instance.__data__[self.name]

    def __repr__(self):
        unit = f'\'{self.unit.to_string("fits")}\'' if self.unit is not None else None
        return (
            f'{self.__class__.__name__}('
            f"name={self.name!r}, required={self.required}, unit={unit}"
            ')'
        )

    @property
    @abstractmethod
    def tform_code():
        ''' The TFORM code of this column, e.g. D for double'''

    @abstractmethod
    def validate_data():
        '''Validate the data stored in this column'''


class BinaryTableMeta(type):
    '''Metaclass for the BinaryTable class'''
    def __new__(cls, name, bases, dct):
        dct['columns'] = []

        for k, v in dct.items():
            if isinstance(v, Column):
                dct['columns'].append(v)

        new_cls = super().__new__(cls, name, bases, dct)
        return new_cls


class BinaryTable(metaclass=BinaryTableMeta):
    '''
    Schema definition class for a binary table

    Attributes
    ----------
    validate_column_order: bool
        If True, validate that the columns are in the same order
        as in the schema definition.
    '''
    validate_column_order = False

    def __init__(self, **column_data):
        self.__data__ = {}

        for k, v in column_data.items():
            setattr(self, k, v)

    def validate(self):
        for col in self.columns:
            validated = col.validate_data(self)
            if validated is not None:
                setattr(self, col.name, validated)


class PrimitiveColumn(Column):
    '''
    A column consisting of a primitive data type or fixed shape array.
    All non-variable-length array column types
    '''
    def __init__(self, unit=None, required=True, ndim=None, shape=None):
        super().__init__(required=required, unit=unit)

        self.shape = tuple(shape) if shape is not None else None

        if self.shape is not None:
            # Dimensionality of the table is one more than that of a single row
            self.ndim = len(self.shape) + 1
        else:
            self.ndim = 1

    @property
    @abstractmethod
    def dtype():
        '''Equivalent numpy dtype'''

    def validate_data(self, table):
        ''' Validate the data of this column in table '''

        # check if column has data
        if self.name not in table.__data__:
            if self.required:
                raise RequiredMissing(
                    'Table is missing required column {self}'
                )
            else:
                return

        # we have data, so we validate it
        data = table.__data__[self.name]

        # let's test first for the datatype
        try:
            # casting = 'safe' makes sure we don't change values
            # e.g. casting doubles to integers will no longer work
            np.asanyarray(data).astype(self.dtype, casting='safe')
        except TypeError as e:
            raise DataTypeError('dtype not convertible to column dtype') from e

        # the rest of the tests is done on a quantity object with correct dtype
        try:
            q = u.Quantity(
                data, self.unit, copy=False, ndmin=1, dtype=self.dtype
            )
        except u.UnitConversionError as e:
            raise UnitError(str(e)) from None

        if q.ndim != self.ndim:
            raise DimError(
                f'Dimensionality of data is {q.ndim}, should be {self.ndim}'
            )

        shape = q.shape[1:]
        if self.shape is not None and self.shape != shape:
            raise ShapeError(
                'Shape {shape} does not match required shape {self.shape}'
            )

        return q


class Bool(PrimitiveColumn):
    '''A Boolean binary table column'''
    tform_code = 'L'
    dtype = np.bool


class BitField(PrimitiveColumn):
    '''Bitfield binary table column'''
    tform_code = 'X'
    dtype = np.bool


class Byte(PrimitiveColumn):
    '''Byte binary table column'''
    tform_code = 'B'
    dtype = np.uint8


class Int16(PrimitiveColumn):
    '''16 Bit signed integer binary table column'''
    tform_code = 'I'
    dtype = np.int16


class Int32(PrimitiveColumn):
    '''32 Bit signed integer binary table column'''
    tform_code = 'J'
    dtype = np.int32


class Int64(PrimitiveColumn):
    '''64 Bit signed integer binary table column'''
    tform_code = 'K'
    dtype = np.int64


class Char(PrimitiveColumn):
    '''Single byte character binary table column'''
    tform_code = 'A'
    dtype = np.dtype('S1')


class Float(PrimitiveColumn):
    '''Single precision floating point binary table column'''
    tform_code = 'E'
    dtype = np.float32


class Double(PrimitiveColumn):
    '''Single precision floating point binary table column'''
    tform_code = 'D'
    dtype = np.float64


class ComplexFloat(PrimitiveColumn):
    '''Single precision complex binary table column'''
    tform_code = 'C'
    dtype = np.csingle


class ComplexDouble(PrimitiveColumn):
    '''Single precision complex binary table column'''
    tform_code = 'M'
    dtype = np.cdouble
