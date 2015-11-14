# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2015, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


from .version import __version__
import os
import sys
import inspect
import atexit
import json
import warnings
if sys.version_info.major == 2:
    from io import open
    str = unicode




class RandAssign(object):
    '''
    Manage the creation of solutions/keys for randomized assignments.

    Standard usage:

    * At the beginning of a PythonTeX session::

          from randassign import RandAssign
          ra = RandAssign()

    * Within the session, add solutions via ``ra.addsoln()``.  This takes
      an arbitrary number of arguments, corresponding to the solutions for a
      single problem; if multiple arguments are received, they are treated as
      the solutions to a multi-part problem.  The optional, keyword argument
      ``info`` is used to pass information about the problem into the
      solutions.  The keyword argument ``number`` may be used to set the
      problem number manually when the problems created in a session are not
      directly sequential.  When solutions are created with ``addsoln()``,
      solution numbering and formatting are automatically managed by
      ``randassign.make()``; only the actual answers and any accompanying info
      need be provided.

    * Alternately, solutions may be created by appending text to the list
      ``ra.soln``.  Solutions created in this way will not be automatically
      numbered and formatted by ``randassign.make()``; the user has complete,
      direct control over the form of the solution text.  Any desired
      linebreaks must be included explicitly as ``\n`` in the text that is
      appended to ``ra.soln``.  This method of creating solutions may not be
      mixed with ``ra.addsoln()``.
    '''
    def __init__(self, msgdir='.', msgfile=None, msgid=None):
        # Where temp file containing solutions will be written; typically, the
        # directory where the .tex files are located
        self.msgdir = msgdir

        # Unique ID for solutions
        # By default, this is derived from the name of the importing script,
        # which is being executed by PythonTeX.  This script is guaranteed to
        # have a unique name.  A unique ID is needed so that if multiple
        # PythonTeX sessions are in use, they don't all try to use the same
        # solution file.
        if msgid is None:
            unique_id = os.path.split(inspect.stack()[1][1])[1]
            if unique_id.endswith('.py'):
                unique_id = unique_id.rsplit('.', 1)[0]
            self.id = unique_id
        else:
            self.id = str(msgid)

        # File name of solution file
        if msgfile is None:
            self.msgfile = '_randassign.{0}.json'.format(self.id)
        else:
            self.msgfile = msgfile

        self.msgfilewithpath = os.path.expanduser(os.path.expandvars(os.path.join(self.msgdir, self.msgfile)))

        self.soln = []
        self._addsoln_list = []
        self._number = 0

        atexit.register(self._cleanup)
        self._iscleanedup = False

    def _cleanup(self):
        '''
        Make sure all accumulated data is saved into message files before exit
        '''
        if not self._iscleanedup:
            self.cleanup()

    def cleanup(self):
        '''
        Save accumulated solutions in json format
        '''
        if self._iscleanedup:
            warnings.warn('cleanup() has already been called')
            return
        if not self.soln and not self._addsoln_list:
            return
        elif self.soln and self._addsoln_list:
            raise RuntimeError('The list "soln" and the method "addsoln" cannot both be used')
        if self.soln:
            solutions = ''.join(self.soln)
        else:
            solutions = self._addsoln_list

        d = {'type': 'randassign.solutions',
             'id': self.id,
             'format': 'soln' if self.soln else 'addsoln',
             'solutions': solutions,
            }

        with open(self.msgfilewithpath, 'w', encoding='utf8') as f:
            # Need `ensure_ascii=False` to get Unicode from `json.dumps()`
            f.write(json.dumps(d, indent=2, ensure_ascii=False))
            f.write('\n')

        self._iscleanedup = True

    def addsoln(self, *args, **kwargs):
        '''
        Add a solution.
        '''
        # Process args
        if not args:
            raise RuntimeError('The addsoln() function requires as least one solution')
        else:
            soln = list(str(x) if isinstance(x, bytes) else x for x in args)
        number = kwargs.pop('number', None)
        info = kwargs.pop('info', '')
        if isinstance(info, bytes):
            info = str(info)
        if kwargs:
            raise RuntimeError('Unknown keyword arguments given to addsoln(): {0}'.format(', '.join(k for k in kwargs)))

        if number is None:
            self._number += 1
            number = self._number
        else:
            number = int(number)
        d = {'number': number, 'info': info, 'solution': soln}
        self._addsoln_list.append(d)
