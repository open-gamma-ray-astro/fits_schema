'''
Schema definitions for FITS binary table extensions

See section 7.3 of the FITS standard:
https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf
'''
from abc import ABCMeta, abstractmethod
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.table import Table
import logging

from .header import HeaderSchema, HeaderCard, HeaderSchemaMeta
from .exceptions import (
    WrongUnit, WrongDims, WrongType, RequiredMissing, WrongShape,
)
from .utils import log_or_raise


log = logging.getLogger(__name__)


class BinaryTableHeader(HeaderSchema):
    '''default binary table header schema'''
    XTENSION = HeaderCard(allowed_values='BINTABLE', position=0)
    BITPIX = HeaderCard(allowed_values=8, position=1)
    NAXIS = HeaderCard(allowed_values=2, position=2)
    NAXIS1 = HeaderCard(type_=int, position=3)
    NAXIS2 = HeaderCard(type_=int, position=4)
    PCOUNT = HeaderCard(type_=int, position=5)
    GCOUNT = HeaderCard(allowed_values=1, position=6)
    TFIELDS = HeaderCard(type_=int, position=7)
    EXTNAME = HeaderCard(required=False, type_=str)


class Column(metaclass=ABCMeta):
    '''Base class for the column descriptors'''

    def __init__(self, *, unit=None, required=True, name=None):
        self.required = required
        self.unit = unit
        self.name = name

    def __get__(self, instance, owner=None):
        # class attribute access
        if instance is None:
            return self

        return instance.__data__.get(self.name)

    def __set__(self, instance, value):
        instance.__data__[self.name] = value

    def __set_name__(self, owner, name):
        # respect user override for names that are not valid identifiers
        if self.name is None:
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
    def validate_data(data):
        '''Validate the data stored in this column'''


class BinaryTableMeta(type):
    '''Metaclass for the BinaryTable class'''
    def __new__(cls, name, bases, dct):
        dct['__columns__'] = {}
        dct['__slots__'] = ('__data__', 'header')

        header_schema = dct.pop('__header__', None)
        if header_schema is not None and not issubclass(header_schema, HeaderSchema):
            raise TypeError(
                '`__header__` must be a class inheriting from `HeaderSchema`'
            )

        # create a new header schema class for this table
        dct['__header__'] = HeaderSchemaMeta.__new__(
            HeaderSchemaMeta, name + 'Header', (BinaryTableHeader, ), {},
        )

        # inherit header schema and  from bases
        for base in reversed(bases):
            if hasattr(base, '__header__'):
                dct['__header__'].update(base.__header__)

            if issubclass(base, BinaryTable):
                dct['__columns__'].update(base.__columns__)

        if header_schema is not None:
            # add user defined header last
            dct['__header__'].update(header_schema)

        # collect columns of this new schema
        for k, v in dct.items():
            if isinstance(v, Column):
                k = v.name or k
                dct['__columns__'][k] = v

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
        self.header = fits.Header()

        for k, v in column_data.items():
            setattr(self, k, v)

    def validate_data(self):
        for k, col in self.__columns__.items():
            validated = col.validate_data(self.__data__.get(k))
            if validated is not None:
                setattr(self, k, validated)

    @classmethod
    def validate_hdu(cls, hdu: fits.BinTableHDU, onerror='raise'):
        if not isinstance(hdu, fits.BinTableHDU):
            raise TypeError('hdu is not a BinTableHDU')

        cls.__header__.validate_header(hdu.header, onerror=onerror)
        required = set(c.name for c in cls.__columns__.values() if c.required)
        missing = required - set(c.name for c in hdu.columns)
        if missing:
            log_or_raise(
                f'The following required columns are missing {missing}',
                RequiredMissing,
                log=log,
                onerror=onerror
            )

        table = Table.read(hdu)
        for k, col in cls.__columns__.items():
            if k in table.columns:
                col.validate_data(table[k])


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

    def validate_data(self, data):
        ''' Validate the data of this column in table '''
        if data is None:
            if self.required:
                raise RequiredMissing('Column {self.name} is required but missing')
            else:
                return

        # let's test first for the datatype
        try:
            # casting = 'safe' makes sure we don't change values
            # e.g. casting doubles to integers will no longer work
            data = np.asanyarray(data).astype(self.dtype, casting='safe')
        except TypeError as e:
            raise WrongType('dtype not convertible to column dtype') from e

        # the rest of the tests is done on a quantity object with correct dtype
        try:
            q = u.Quantity(
                data, self.unit, copy=False, ndmin=1, dtype=self.dtype
            )
        except u.UnitConversionError as e:
            raise WrongUnit(str(e)) from None

        if q.ndim != self.ndim:
            raise WrongDims(
                f'Dimensionality of data is {q.ndim}, should be {self.ndim}'
            )

        shape = q.shape[1:]
        if self.shape is not None and self.shape != shape:
            raise WrongShape(
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
