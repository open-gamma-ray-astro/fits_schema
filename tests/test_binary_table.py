import astropy.units as u
import pytest

from fits_schema.exceptions import UnitError, DataTypeError, RequiredMissing, DimError


def test_validation():
    from fits_schema.binary_table import BinaryTable, Double

    class MyTable(BinaryTable):
        E_EST = Double(unit=u.m)

    assert len(MyTable.columns) == 1

    table = MyTable(E_EST=[1, 2, 3])
    table.validate()
    assert (table.E_EST == u.Quantity([1, 2, 3], u.m)).all()

    # wrong unit
    table = MyTable(E_EST=5 * u.deg)
    with pytest.raises(UnitError):
        table.validate()

    # 2d table
    table = MyTable(E_EST=[[2, 2], [1, 2]])
    with pytest.raises(DimError):
        table.validate()

    table = MyTable(E_EST='abc')
    with pytest.raises(DataTypeError):
        table.validate()
