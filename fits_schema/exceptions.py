class ValidationError(ValueError):
    pass


class RequiredMissing(ValidationError):
    pass


class UnitError(ValidationError):
    pass


class DimError(ValidationError):
    pass


class DataTypeError(ValidationError):
    pass
