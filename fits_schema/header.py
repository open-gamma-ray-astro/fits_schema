'''
Schema definitions for FITS Headers.

See section 4 of the FITS Standard:
https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf
'''
from datetime import date, datetime


HEADER_ALLOWED_TYPES = (str, bool, int, float, complex, date, datetime)


class HeaderCard:
    '''
    Schema for the entry of a FITS header

    Attributes
    ----------
    required: bool
        If this card is required
    value: instance of any in ``HEADER_ALLOWED_TYPES``
        ``if value is not None``, the header card must have this fixed value.
        ``if required and value is None``, the card must be present but must not have
        a value.
    position: int or None
        if not None, the card must be at this position in the header,
        starting with the first card at 0
    type: one of ``HEADER_ALLOWED_TYPES``
    '''

    def __init__(self, required=True, value=None, position=None, type_=None):
        self.required = required
        self.value = value
        self.type = type_
        self.position = position

        if value is not None and not isinstance(value, HEADER_ALLOWED_TYPES):
            raise ValueError(f'Value must be an instance of {HEADER_ALLOWED_TYPES}')

        if type_ is not None:
            # check that value and type match if both supplied
            if not (value is None or isinstance(value, type_)):
                raise TypeError(f'`value` must be of type `type_`({type_}) or None')
        else:
            # if only value is supplied, deduce type from value
            if value is not None:
                self.type = type(value)


class HeaderSchemaMeta(type):
    def __new__(cls, name, bases, dct):
        dct['__cards__'] = []

        for k, v in dct.items():
            if isinstance(v, HeaderCard):
                dct['__cards__'].append(v)

        new_cls = super().__new__(cls, name, bases, dct)
        return new_cls


class HeaderSchema(metaclass=HeaderSchemaMeta):
    '''
    Schema definition for the header of a FITS HDU

    To be added as `class __header_schema__(HeaderSchema)` to HDU schema classes.

    Add `Card` class members to define the schema.


    Example
    -------
    >>> from fits_schema import BinaryTable, HeaderSchema, HeaderCard, Integer
    ... class Events(BinaryTable):
    ...     EVENT_ID = Integer()
    ...
    ...     class __header_schema__(HeaderSchema):
    ...         HDUCLASS = Card(required=True, value="Events")
    '''

    validate_order = True
