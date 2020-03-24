import astropy.units as u
from astropy.table import Table
from astropy.io import fits
import pytest
import numpy as np

from fits_schema.exceptions import (
    UnitError, DataTypeError, RequiredMissing, DimError, ShapeError,
)


def test_unit():
    from fits_schema.binary_table import BinaryTable, Double

    class TestTable(BinaryTable):
        test = Double(unit=u.m)

    table = TestTable(test=[1, 2, 3])
    table.validate_data()
    assert (table.test == u.Quantity([1, 2, 3], u.m)).all()

    table = TestTable(test=5 * u.deg)
    with pytest.raises(UnitError):
        table.validate_data()


def test_repr():
    from fits_schema.binary_table import BinaryTable, Double

    class TestTable(BinaryTable):
        test = Double()

    assert repr(TestTable.test) == "Double(name='test', required=True, unit=None)"

    TestTable.test.unit = u.m
    assert repr(TestTable.test) == "Double(name='test', required=True, unit='m')"

    TestTable.test.unit = u.m**-2
    assert repr(TestTable.test) == "Double(name='test', required=True, unit='m-2')"


def test_access():
    from fits_schema.binary_table import BinaryTable, Double

    class TestTable(BinaryTable):
        test = Double(required=False)

    t = TestTable()
    assert t.test is None
    t.test = 5.0
    assert t.test == 5.0

    # assignment does not validate
    t.test == 'foo'

    del t.test
    assert t.test is None

    # test that we can only assign to columns
    with pytest.raises(AttributeError):
        t.foo = 'bar'


def test_shape():
    from fits_schema.binary_table import BinaryTable, Double

    class TestTable(BinaryTable):
        test = Double(shape=(10, ))

    # single number, wrong number of dimensions
    table = TestTable(test=3.14)
    with pytest.raises(DimError):
        table.validate_data()

    # three numbers per row, should be ten
    table = TestTable(test=[[1, 2, 3]])
    with pytest.raises(ShapeError):
        table.validate_data()

    # this should work
    table = TestTable(test=[np.arange(10), np.random.normal(size=10)])
    table.validate_data()


def test_required():
    from fits_schema.binary_table import BinaryTable, Bool

    class TestTable(BinaryTable):
        test = Bool(required=True)

    table = TestTable()

    with pytest.raises(RequiredMissing):
        table.validate_data()

    table.test = [True, False]
    table.validate_data()


def test_data_types():
    from fits_schema.binary_table import BinaryTable, Int16

    class TestTable(BinaryTable):
        test = Int16(required=False)

    table = TestTable()

    # check no data is ok, as column is optional
    assert table.validate_data() is None

    # integer is ok
    table.test = 1
    table.validate_data()

    # double would loose information
    table.test = 3.14
    with pytest.raises(DataTypeError):
        table.validate_data()

    # too large for int16
    table.test = 2**15
    with pytest.raises(DataTypeError):
        table.validate_data()


def test_inheritance():
    from fits_schema.binary_table import BinaryTable, Bool

    class BaseTable(BinaryTable):
        foo = Bool()
        bar = Bool()

    class TestTable(BaseTable):
        # make sure it's different from base defintion
        bar = Bool(required=not BaseTable.foo.required)
        baz = Bool()

    assert list(TestTable.__columns__) == ['foo', 'bar', 'baz']
    assert TestTable.bar.required != BaseTable.bar.required


def test_validate_hdu():
    from fits_schema.binary_table import BinaryTable, Double

    class TestTable(BinaryTable):
        energy = Double(unit=u.TeV, required=True)
        ra = Double(unit=u.deg, required=True)
        dec = Double(unit=u.deg, required=True)

    print(TestTable.__header__.__cards__)
    # make sure a correct table passes validation
    t = Table({
        'energy': 10**np.random.uniform(-1, 2, 100) * u.TeV,
        'ra': np.random.uniform(0, 360, 100) * u.deg,
        'dec': np.random.normal(-90, 90, 100) * u.deg,
    })
    hdu = fits.BinTableHDU(t)
    TestTable.validate_hdu(hdu)
