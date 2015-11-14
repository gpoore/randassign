# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2015, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


import sys
import os
# Get a version of open() that can handle encoding
if sys.version_info.major == 2:
    from io import open
import collections


if (sys.version_info < (2,7) or
        (sys.version_info.major == 3 and sys.version_info < (3,2))):
    sys.exit('RandAssign requires Python 2.7 or 3.2+')


try:
    from setuptools import setup
    setup_package_dependent_keywords = dict(
        entry_points = {
            'console_scripts': ['randassign = randassign.make:make'],
        },
    )
except ImportError:
    from distutils.core import setup
    setup_package_dependent_keywords = dict(
        scripts = ['bin/randassign'],
    )


# Extract the version from version.py
# First load functions from fmtversion.py that are needed by version.py
fname = os.path.join(os.path.dirname(__file__), 'randassign', 'fmtversion.py')
with open(fname, 'rb') as f:
    c = compile(f.read(), 'randassign/fmtversion.py', 'exec')
    exec(c)
fname = os.path.join(os.path.dirname(__file__), 'randassign', 'version.py')
with open(fname, 'r', encoding='utf8') as f:
    t = ''.join([line for line in f.readlines() if line.startswith('__version__')])
    if not t:
        raise RuntimeError('Failed to extract version from "version.py"')
    c = compile(t, 'randassign/version.py', 'exec')
    exec(c)
version = __version__

fname = os.path.join(os.path.dirname(__file__), 'README.rst')
with open(fname, encoding='utf8') as f:
    long_description = f.read()


setup(name='randassign',
      version=version,
      py_modules = [],
      packages=['randassign'],
      description='Create randomized assignments with PythonTeX',
      long_description = long_description,
      author = 'Geoffrey M. Poore',
      author_email = 'gpoore@gmail.com',
      url = 'http://github.com/gpoore/randassign',
      license = 'BSD',
      keywords = ['education', 'PythonTeX'],
      # https://pypi.python.org/pypi?:action=list_classifiers
      classifiers = [
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console',
          'Intended Audience :: Education',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Topic :: Education',
          'Topic :: Education :: Testing'
      ],
      **setup_package_dependent_keywords
)
