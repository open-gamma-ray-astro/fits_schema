# fits_schema [![Build Status](https://travis-ci.com/open-gamma-ray-astro/fits_schema.svg?branch=master)](https://travis-ci.com/open-gamma-ray-astro/fits_schema) [![codecov](https://codecov.io/gh/open-gamma-ray-astro/fits_schema/branch/master/graph/badge.svg)](https://codecov.io/gh/open-gamma-ray-astro/fits_schema) [![PyPI version](https://badge.fury.io/py/fits-schema.svg)](https://badge.fury.io/py/fits-schema)



A python package to define and validate schemata for FITS files.


```python
from fits_schema.binary_table import BinaryTable, Double
from fits_schema.header import HeaderSchema, HeaderCard
import astropy.units as u
from astropy.io import fits


class Events(BinaryTable):
    '''A Binary Table of Events'''
    energy = Double(unit=u.TeV)
    ra     = Double(unit=u.deg)
    dec    = Double(unit=u.deg)

    class __header__(HeaderSchema):
        EXTNAME = HeaderCard(allowed_values='events')


hdulist = fits.open('events.fits')
Events.validate_hdu(hdulist['events'])
```
