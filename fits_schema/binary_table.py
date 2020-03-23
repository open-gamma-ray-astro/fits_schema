from abc import ABCMeta, abstractmethod
import numpy as np
import astropy.units as u
from .exceptions import UnitError, DimError, DataTypeError, RequiredMissing


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

        return instance.__data__[self.name]

    def __set__(self, instance, value):
        instance.__data__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name

    def __delete__(self, instance):
        '''clear data of this column'''
        del instance.__data__[self.name]

    def __repr__(self):
        return (
            f'{self.__class__.__name__}('
            f'name={self.name}, required={self.required}, unit={self.unit}'
            ')'
        )

    @property
    @abstractmethod
    def tform_code():
        ''' The TFORM code of this column, e.g. D for double'''

    @abstractmethod
    def validate_data():
        pass


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
    A column consisting of a primitive data type.
    All non-array column types
    '''

    @property
    @abstractmethod
    def dtype():
        '''Equivalent numpy dtype'''

    def validate_data(self, table):
        ''' Validate the data of this column in table '''

        if self.name not in table.__data__:
            if self.required:
                raise RequiredMissing('Table is missing required column {self}')
            else:
                return

        data = table.__data__[self.name]
        try:
            q = u.Quantity(data, self.unit, copy=False, ndmin=1)
        except u.UnitConversionError as e:
            raise UnitError(str(e)) from None
        except TypeError as e:
            raise DataTypeError(str(e)) from None

        if q.ndim != 1:
            raise DimError('Data of primitive columns must be 1d')

        try:
            q = q.astype(self.dtype)
        except ValueError as e:
            raise DataTypeError('dtype not convertible to column dtype') from e

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


class Array32(Column):
    '''32 bit array descriptor'''
    tform_code = 'P'


class Array64(Column):
    '''64 bit array descriptor'''
    tform_code = 'Q'
