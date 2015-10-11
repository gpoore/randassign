# coding: UTF-8
#
# setup randassign.py
#
# Copyright (c) 2013-2014, Geoffrey M. Poore
# Licensed under the BSD 3-Clause License
# http://opensource.org/licenses/BSD-3-Clause
#

from distutils.core import setup
import sys

version = None
f = open('randassign.py', 'r')
src = f.readlines()
f.close()
for line in src:
    if line.startswith('__version__'):
        version = line.replace('__version__', '').strip(' =\r\n').strip('\'"')
        break
if version is None:
    sys.exit('Failed to extract __version__ from "randassign.py".')

setup(name='randassign',
      version=version,
      description='Random assignment helper class for PythonTeX',
      author='Geoffrey M. Poore',
      url='http://github.com/gpoore',
      py_modules=['randassign'])
