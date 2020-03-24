class ValidationError(ValueError):
    '''Base class for all exceptions raised by ``fits_schema``'''


class RequiredMissing(ValidationError):
    '''Raised when a required element is missing'''


class UnitError(ValidationError):
    '''Raised when an element does not have the correct unit'''


class DimError(ValidationError):
    '''Raised when an element does not have the correct dimensions'''


class ShapeError(ValidationError):
    '''Raised when an element does not have the correct shape'''


class DataTypeError(ValidationError):
    '''Raised when an element does not have the correct data type'''


class PositionError(ValidationError):
    '''Raised when an element is not at the correct position'''


class WrongKeyword(ValidationError):
    '''Raised when a HeaderCards is validated and keywords don't match'''


class WrongValue(ValidationError):
    '''Raised when a HeaderCards has not the right value'''


class AdditionalHeaderCard(UserWarning):
    '''Issued when a header has a card not mentioned in the schema'''
