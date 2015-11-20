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
if sys.version_info.major == 2:
    from io import open
    str = unicode
import shlex
import collections
import shutil
import atexit
import json
import zipfile
try:
    import cpickle as pickle
except ImportError:
    import pickle
import argparse
import subprocess
import fnmatch




# Parser for processing command-line arguments to `make()`
#
# This only covers a subset of possible arguments.  The arguments covered are
# those most likely to be changed between runs, or those absolutely required
# for running the command-line utility `randassign` (for example, `texfile`).
# When any significant number of non-default settings are needed, a custom
# script that imports `make()` and passes it appropriate arguments should be
# used instead of the command-line utility.  That approach ensures that custom
# values remain consistent between runs.
#
# All values are None by default, so that `make()` can determine where values
# came from.  The parsing makes no distinction between `make()` being invoked
# in the `randassign` command-line utility and `make()` being used in a custom
# script.  In both cases, `sys.argv` is used to supplement supplied arguments
# as possible.  This may be turned off with `make(<kwargs>, argv=False)`.
argv_parser = argparse.ArgumentParser()
argv_parser.add_argument('--version', action='version', version=__version__)
argv_parser.add_argument('--verbose', '-v', default=None, action='store_true',
                         help='Verbose output')
argv_parser.add_argument('--silent', '-s', default=None, action='store_true',
                         help='Suppress all output')
argv_parser.add_argument('texfile', nargs='?', default=None,
                         help='Assignment file')
argv_parser.add_argument('--texcmd', default=None,
                         help='Command for running LaTeX')
argv_parser.add_argument('--pythontexcmd', default=None,
                         help='Command for running PythonTeX')
argv_parser.add_argument('--student', default=None,
                         help='Individual student for whom to generate assignment (name must also be in the student file; unique partial matches are accepted)')
argv_parser.add_argument('--onlysolutions', default=None, action='store_true',
                         help='Only generate solutions; useful for regenerating solutions in a different format or with a new template')



def make(**kwargs):
    '''
    Generate randomized assignments and solutions.

    Standard usage::

        from randassign import make
        make(texfile='<tex_file>')

    May also be used from the command line, via the executable that is created
    by a standard installation::

        randassign <tex_file>

    The default configuration should be sufficient for most cases.  All
    typical customization should be able to be accomplished by passing
    arguments to ``make()``.

    By default, ``make()`` checks ``sys.argv`` for arguments, regardless of
    how it is invoked.  This is needed for the command-line ``randassign``,
    and is also useful for running scripts with one-time values.  This behavior
    may be disabled via ``make(<kwargs>, argv=False)``.  Note that only a
    subset of the arguments of ``make()`` are supported via the command line;
    run ``randassing --help`` for a list of supported arguments.
    '''

    a = _process_args(kwargs)
    # Need to do everything while in the same directory as the .tex file
    # This ensures that all output stays with the .tex file, or in subdirectories
    orig_workingdir = os.getcwd()
    if a.texdir:
        os.chdir(a.texdir)

    # Need a way to clean up created files in the event of an error
    createdfiles = []
    def cleanup():
        for f in createdfiles:
            try:
                os.remove(f)
            except:
                pass
    atexit.register(cleanup)

    _check_directory_structure(a.randassigndir, a.solndir, a.assigndir)

    data = _load_data(a.randassigndatafile, a.randassigndatafilefmt)

    s = _load_students(a.student, a.studentfile, a.parsestudentfile, a.parsestudentname)
    students, students_raw, students_raw_str = s

    if not a.onlysolutions:
        _run(data, createdfiles, students, students_raw, students_raw_str,
             a.verbose, a.silent, a.texcmd, a.texfile, a.namefile, a.attemptfile,
             a.pythontexcmd, a.msgfilepattern, a.assigndir, a.multipleattempts)

    # The default `writesoln()` requires all arguments to function correctly,
    # but is written so that all arguments but `data` are keyword arguments.
    # This makes it simple to write custom functions of the form
    # `custom_writesoln(data, **kwargs)`, which can ignore any keyword args
    # that aren't actually used.
    a.writesoln(data, verbose=a.verbose, silent=a.silent,
                solncmd=a.solncmd, solnfile=a.solnfile, solnfmt=a.solnfmt,
                onlylastsoln=a.onlylastsoln,
                multipleattempts=a.multipleattempts,
                solntemplatedoc=a.solntemplatedoc,
                solntemplatestudent=a.solntemplatestudent,
                solntemplatesolnsattempt=a.solntemplatesolnsattempt,
                solntemplatesolnswrapper=a.solntemplatesolnswrapper,
                solntemplatesolnsingle=a.solntemplatesolnsingle,
                solntemplatesolnsingleinfo=a.solntemplatesolnsingleinfo,
                solntemplatesolnmultiwrapper=a.solntemplatesolnmultiwrapper,
                solntemplatesolnmultiwrapperinfo=a.solntemplatesolnmultiwrapperinfo,
                solntemplatesolnmulti=a.solntemplatesolnmulti,
                createdfiles=createdfiles)

    _save_data(data, a.randassigndatafile, a.randassigndatafilefmt)

    # Clear list of created files to keep them, since no errors occurred
    # Using `atexit.unregister(cleanup)` would be cleaner, but Python 2.7
    createdfiles[:] = []
    os.chdir(orig_workingdir)




def _process_args(kwargs):
    '''
    Process args for ``make()``, updating default args first with keyword args
    passed to ``make()`` and second (optionally) with ``sys.argv``.

    Return a namedtuple of final args.

    Args:
        argv:  Whether to supplement supplied arguments from ``sys.argv``
        verbose:  Verbose output
        silent:  Suppress all output
        texfile:  LaTeX file from which to generate assignments
        texcmd:  Command for compiling LaTeX file (does not include file name)
        pythontexcmd:  Command for running PythonTeX (does not include file name)
        randassigndir:  Root directory for saving created assignments and
                        solutions
        subdirs:  Whether to create subdirectories under ``randassigndir`` for
                  assignments and solutions
        assigndir:  Subdirectory for assignments
        solndir:  Subdirectory for solutions
        namefile:  LaTeX file containing the name of the current student
        attemptfile:  LaTeX file containing the number of the current attempt
        student:  An individual student for whome to generate assignments
        studentfile:  File containing the names of all students
        parsestudentfile:  Function for parsing the student file and returning
                           a list of student names in the form needed for
                           assignments
        parsestudentname:  Function for parsing individual lines of the student
                           file into student names in the desired format
        onlysolutions:  Only generate solutions; do not generate any assignments
        solnfile:  Solution file
        solnfmt:  Solution file format
        solncmd:  Command for post-processing solution file
        writesoln:  Function for writing the solutions, given the solution data,
                    templates, and other parameters
        msgfilepattern:  Pattern for identifying "message" files, files
                         containing solutions, that are saved from the .tex file
        onlylastsoln:  Whether to include only the solution for the last attempt
                       for each student, rather than complete solutions for all
                       attempts, in the solution file
        multipleattempts:  Whether multiple attempts will be given for an
                           assignment; this determines whether attempts are
                           listed/numbered in solutions
        randassigndatafile:  File for saving raw solution data and associated
                             metadata
        randassigndatafilefmt:  Format for data file
        solntemplatedoc:  Template for overall solution document
        solntemplatestudent:  Template for overall solutions for each student
        solntemplatesolnsattempt:  Template for attempt heading
        solntemplatesolnswrapper:  Template for wrapping a set of solutions,
                                   if the set of solutions needs to be preceded
                                   and followed by markup
        solntemplatesolnsingle:  Template for a one-part solution
        solntemplatesolnsingleinfo:  Template for a one-part solution that
                                     includes additional info from the problem
        solntemplatesolnmultiwrapper:  Template for wrapping a multi-part
                                       solution
        solntemplatesolnmultiwrapperinfo:  Template for wrapping a multi-part
                                           solution that includes additional
                                           info from the problem
        solntemplatesolnmulti:  Template for each piece of a multi-part solution
    '''

    # Default keyword args
    dkwargs = {'argv': True,
               'verbose': False,
               'silent': False,
               'texfile': None, 'texcmd': 'pdflatex -interaction=nonstopmode',
               'pythontexcmd': 'pythontex --rerun always',
               'randassigndir': 'randassign',
               'subdirs': True, 'assigndir': 'assignments', 'solndir': 'solutions',
               'namefile': 'name.tex', 'attemptfile': 'attempt.tex',
               'student': None, 'studentfile': 'students.txt',
               'parsestudentfile': _parsestudentfile, 'parsestudentname': _parsestudentname,
               'onlysolutions': False,
               'solnfile': None, 'solnfmt': 'tex', 'solncmd': 'pdflatex -interaction=nonstopmode',
               'writesoln': _writesoln,
               'msgfilepattern': '_randassign.*.json', 'onlylastsoln': False,
               'multipleattempts': True,
               'randassigndatafile': None, 'randassigndatafilefmt': 'json.zip',
               'solntemplatedoc': None,
               'solntemplatestudent': None,
               'solntemplatesolnsattempt': None,
               'solntemplatesolnswrapper': None,
               'solntemplatesolnsingle': None,
               'solntemplatesolnsingleinfo': None,
               'solntemplatesolnmultiwrapper': None,
               'solntemplatesolnmultiwrapperinfo': None,
               'solntemplatesolnmulti': None
              }

    # Create a copy of the default args that will be modified into the final args
    fkwargs = dkwargs.copy()

    # Update the final args with the kwargs from `make()`
    # Perform some basic type checking in processing kwargs
    bools = ('argv', 'subdirs', 'onlylastsoln', 'multipleattempts', 'verbose', 'silent', 'onlysolutions')
    funcs = ('parsestudentfile', 'parsestudentname', 'writesoln')
    for k in kwargs:
        if k in dkwargs:
            v = kwargs[k]
            if v is None:
                pass
            elif k in bools and v in (True, False):
                pass
            elif k in funcs and hasattr(v, '__call__'):
                pass
            elif k not in bools+funcs and isinstance(v, str):
                pass
            elif isinstance(v, bytes) and sys.version_info.major == 2:
                v = str(v)
            elif isinstance(v, list):
                if all(isinstance(x, str) for x in v):
                    pass
                elif all(isinstance(x, bytes) and sys.version_info.major == 2 for x in v):
                    v = [str(x) for x in v]
                else:
                    raise TypeError('Invalid type {0} for keyword argument "{0}" supplied to make()'.format(v.__type__, k))
            else:
                raise TypeError('Invalid type {0} for keyword argument "{0}" supplied to make()'.format(v.__type__, k))
            fkwargs[k] = v
        else:
            raise KeyError('Invalid keyword argument "{0}" supplied to make()'.format(k))

    # Update the final args with the args from `sys.argv`
    # The basic type checking used for kwargs isn't needed here because only a
    # subset of arguments is supported, and the values of these are handled by
    # the parser
    if fkwargs['argv'] is True:
        kwargv = {k:v for k, v in vars(argv_parser.parse_args()).items() if v is not None}
        for k in kwargv:
            if k in dkwargs:
                fkwargs[k] = kwargv[k]
            else:
                raise KeyError('Invalid keyword argument "{0}" supplied to make() via the command line'.format(k))


    # Check arg compatibility
    if fkwargs['verbose'] and fkwargs['silent']:
        raise RuntimeError('Cannot use options "verbose" and "silent" simultaneously')

    # Check texfile existence and extension after expanding
    # Then split off any path into texdir
    texfile = fkwargs['texfile']
    if texfile is None:
        raise RuntimeError('A tex file must be specified')
    texfile = os.path.expanduser(os.path.expandvars(texfile))
    if not os.path.isfile(texfile):
        raise RuntimeError('The tex file "{0}" does not exist'.format(fkwargs['texfile']))
    if not texfile.endswith('.tex'):
        raise RuntimeError('The format of the tex file "{0}" appears to be invalid; lacks the extension .tex'.format(fkwargs['texfile']))
    fkwargs['texdir'], fkwargs['texfile'] = os.path.split(texfile)

    # Format texcmd for subprocess
    if isinstance(fkwargs['texcmd'], str):
        fkwargs['texcmd'] = shlex.split(fkwargs['texcmd']) + [fkwargs['texfile']]
    elif isinstance(fkwargs['texcmd'], list):
        fkwargs['texcmd'] = fkwargs['texcmd'] + [fkwargs['texfile']]
    # Account for possible path to executable
    fkwargs['texcmd'][0] = os.path.expanduser(os.path.expandvars(fkwargs['texcmd'][0]))

    # Format pythontexcmd, accounting for possible path to pythontexcmd
    if isinstance(fkwargs['pythontexcmd'], str):
        fkwargs['pythontexcmd'] = shlex.split(fkwargs['pythontexcmd']) + [fkwargs['texfile']]
    elif isinstance(fkwargs['pythontexcmd'], list):
        fkwargs['pythontexcmd'] = fkwargs['pythontexcmd'] + [fkwargs['texfile']]
    fkwargs['pythontexcmd'][0] = os.path.expanduser(os.path.expandvars(fkwargs['pythontexcmd'][0]))

    # Set paths for randassign
    fkwargs['randassigndir'] = os.path.expanduser(os.path.expandvars(fkwargs['randassigndir']))
    # Set assigndir and solndir so that they are correct regardless of subdirs
    if fkwargs['subdirs']:
        fkwargs['assigndir'] = os.path.join(fkwargs['randassigndir'], os.path.expanduser(os.path.expandvars(fkwargs['assigndir'])))
        fkwargs['solndir'] = os.path.join(fkwargs['randassigndir'], os.path.expanduser(os.path.expandvars(fkwargs['solndir'])))
    else:
        fkwargs['assigndir'] = fkwargs['randassigndir']
        fkwargs['solndir'] = fkwargs['randassigndir']

    # Expand files used by tex file
    # Typically, these should be in the texdir, so this should be unnecessary
    for k in ('namefile', 'attemptfile'):
        fkwargs[k] = os.path.expanduser(os.path.expandvars(fkwargs[k]))

    # Set studentfile, assuming relative paths to workingdir
    fkwargs['studentfile'] = os.path.expanduser(os.path.expandvars(fkwargs['studentfile']))
    if not os.path.isfile(fkwargs['studentfile']):
        raise RuntimeError('Could not find student file "{0}"'.format(fkwargs['studentfile']))

    # Set solnfile and solnfmt, making sure solnfmt is valid if not using a
    # custom formatting function for solutions
    if fkwargs['solnfmt'] is None:
        fkwargs['solnfmt'] = fkwargs['solnfile'].rsplit('.', 1)[1].lower()
    else:
        fkwargs['solnfmt'] = fkwargs['solnfmt'].lstrip('.').lower()
    if fkwargs['solnfile'] is None:
        fkwargs['solnfile'] = os.path.join(fkwargs['solndir'], '{0}.{1}'.format('solutions', fkwargs['solnfmt']))
    else:
        fkwargs['solnfile'] = os.path.join(fkwargs['solndir'], os.path.expanduser(os.path.expandvars(fkwargs['solnfile'])))
    if fkwargs['writesoln'] is _writesoln:
        if fkwargs['solnfmt'] not in ('tex', 'md', 'markdown'):
            raise ValueError('Solution format "solnfmt" must be one of "tex", "md", or "markdown"; currently "{0}"'.format(fkwargs['solnfmt']))
        elif not fkwargs['solnfile'].endswith('.' + fkwargs['solnfmt']):
            raise ValueError('Solution file name "{0}" lacks appropriate extension ".{1}"'.format(fkwargs['solnfile'], fkwargs['solnfmt']))

    # Format solncmd
    if isinstance(fkwargs['solncmd'], str):
        fkwargs['solncmd'] = shlex.split(fkwargs['solncmd']) + [os.path.split(fkwargs['solnfile'])[1]]
    elif isinstance(fkwargs['solncmd'], list):
        fkwargs['solncmd'] = fkwargs['solncmd'] + [os.path.split(fkwargs['solnfile'])[1]]
    if fkwargs['solncmd'] is not None:  # Having solndcmd isn't required
        fkwargs['solncmd'][0] = os.path.expanduser(os.path.expandvars(fkwargs['solncmd'][0]))

    # Set data file name based on tex file name
    if fkwargs['randassigndatafilefmt'] is None:
        fkwargs['randassigndatafilefmt'] = fkwargs['randassigndatafile'].rsplit('.', 1)[1]
    else:
        fkwargs['randassigndatafilefmt'] = fkwargs['randassigndatafilefmt'].lstrip('.').lower()
    if fkwargs['randassigndatafilefmt'] not in ('json', 'json.zip', 'pkl', 'pickle'):
        raise ValueError('Data file format must be one of "json", "json.zip", or "pickle" (or equivalently "pkl"); currently "{0}"'.format(fkwargs['randassigndatafilefmt']))
    if fkwargs['randassigndatafile'] is None:
        fkwargs['randassigndatafile'] = os.path.join(fkwargs['solndir'], '{0}.{1}'.format(fkwargs['texfile'].rsplit('.', 1)[0], fkwargs['randassigndatafilefmt']))
    else:
        fkwargs['randassigndatafile'] = os.path.join(fkwargs['solndir'], os.path.expanduser(os.path.expandvars(fkwargs['randassigndatafile'])))
    if not fkwargs['randassigndatafile'].endswith('.' + fkwargs['randassigndatafilefmt']):
        raise ValueError('Data file name "{0}" lacks appropriate extension ".{1}"'.format(fkwargs['randassigndatafile'], fkwargs['randassigndatafilefmt']))

    # Now that arguments are finalized, provide convenient access via a
    # namedtuple
    Args = collections.namedtuple('Args', [k for k in fkwargs])
    a = Args(**fkwargs)
    return a




def _check_directory_structure(*args):
    '''
    Create any needed directories for randassign, solutions, or assignments.
    '''
    # Use `set()` to avoid duplicates in the event that everything is in a
    # single directory
    for x in set(args):
        if not os.path.isdir(x):
            os.makedirs(x)




def _load_data(datafile, datafilefmt):
    '''
    Load the data file from the last run, or if it does not exist, return an
    empty dictionary.  Backup any existing data in the process.
    '''
    if not os.path.isfile(datafile):
        data = {}
    else:
        if datafilefmt == 'json':
            with open(datafile, encoding='utf8') as f:
                data = json.load(f)
        elif datafilefmt == 'json.zip':
            with zipfile.ZipFile(datafile) as z:
                fname = os.path.split(datafile)[1].rsplit('.', 1)[0]
                with z.open(fname) as f:
                    data = json.loads(f.read().decode('utf8'))
        elif datafilefmt in ('pickle', 'pkl'):
            with open(datafile, 'rb') as f:
                data = pickle.load(f)
        else:
            raise ValueError('Invalid data file format {0}'.format(datafilefmt))
        # Create 2 levels of backups--maybe a little paranoid, but safer
        # The data file is only written after everything is complete and there
        # are no errors, so copying it in this manner doesn't risk overwriting
        # valid backups with bad data
        if os.path.isfile(datafile + '.backup'):
            shutil.copy(datafile + '.backup', datafile + '.backup2')
        shutil.copy(datafile, datafile + '.backup')

    return data




def _save_data(data, datafile, datafilefmt):
    '''
    Save the data file for future runs.
    '''
    if datafilefmt == 'json':
        with open(datafile, 'w', encoding='utf8') as f:
            # Need `ensure_ascii=False` to get Unicode
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
            f.write('\n')
    elif datafilefmt == 'json.zip':
        with zipfile.ZipFile(datafile, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            fname = os.path.split(datafile)[1].rsplit('.', 1)[0]
            t = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
            z.writestr(fname, t.encode('utf8'))
    elif datafilefmt in ('pickle', 'pkl'):
        with open(datafile, 'wb') as f:
            pickle.dump(data, f)
    else:
        raise ValueError('Invalid data file format {0}'.format(datafilefmt))




def _load_students(student, studentfile, parsestudentfile, parsestudentname):
    '''
    Load student data, returning a list of parsed student names and a list of
    raw student names.

    If the argument ``student`` is not None, then only return values for that
    student, so that only that student will be processed.  The list of students
    is parsed for an exact match for ``student``, and if this fails, then for
    a unique, full-word, partial match at the beginning or end.
    '''
    students, students_raw, student_raw_str = parsestudentfile(studentfile, parsestudentname)

    # Deal with case of generating for only a single student
    if student is not None:
        student = student.strip().lower()
        matches = []

        directmatch = [s for s in students if s.lower() == student]
        if directmatch:
            matches.extend(directmatch)
        elif ' ' not in student:
            for s in students:
                if student in s.lower().split(' '):
                    matches.append(s)
        else:
            for s in students:
                s_l = s.lower()
                if s_l.startswith(student) and s_l.replace(student, '').startswith(' '):
                    matches.append(s)
                elif s_l.endswith(student) and s_l.replace(student, '').endswith(' '):
                    matches.append(s)

        if not matches:
            raise RuntimeError('Could not find student "{0}"'.format(student))
        elif len(matches) == 1:
            n = students.index(matches[0])
            students = [students[n]]
            students_raw = [students_raw[n]]
        else:
            raise RuntimeError('Found multiple matches for student "{0}":  {1}'.format(student, matches))

    return students, students_raw, student_raw_str




def _parsestudentfile(studentfile, parsestudentname):
    '''
    Read the student file, and return a list of formatted student names.
    '''
    if studentfile.endswith('.txt'):
        with open(studentfile, encoding='utf8') as f:
            students_raw = [x.strip() for x in f.readlines() if x.strip()]
    elif studentfile.endswith('.csv'):
        import csv
        with open(studentfile, encoding='utf8', newline='') as f:
            students_raw = [x for x in csv.reader(f) if x and all(x)]
    else:
        raise ValueError('Student file "{0}" cannot be parsed because it is not .txt or .csv; supply a custom function parsestudentfile() for other formats'.format(studentfile))

    if not students_raw:
        raise RuntimeError('Parsing the student file gave no students')

    if not isinstance(students_raw[0], list):
        students_raw_str = [x.strip() for x in students_raw]
    else:
        if len(student_raw[0]) == 1:
            students_raw_str = [x[0].strip() for x in students_raw]
        elif len(student_raw) == 2:
            students_raw_str = [', '.join(x[0].strip(), x[1].strip()) for x in students_raw]
        else:
            raise RuntimeError('Cannot deal with raw names consisting of lists of length greater than 2')
    if len(students_raw_str) != len(set(students_raw_str)):
        if studentfile.endswith('.txt'):
            raise RuntimeError('The student file contains duplicate names')
        else:
            raise RuntimeError('The student file contains duplicate names, or the conversion of CSV cells into a string yielded duplicates')

    # Need to make sure that the parsed names are unique
    students = [parsestudentname(x) for x in students_raw]
    if len(students) != len(set(students)):
        students = [parsestudentname(x, initials=True) for x in students_raw]
    if len(students) != len(set(students)):
        raise RuntimeError('Student file yielded duplicate names after parsing')

    return students, students_raw, students_raw_str




def _parsestudentname(studentname, initials=False):
    '''
    Parse individual student names into the form that will actually appear on
    assignments.

    If ``studentname`` is a string, the parser assumes that commas will only be
    used in names in "Last, First" format.  Commas will not be used to separate
    "Jr," "Sr," "II," "III," etc. from the rest of the name.

    If ``studentname`` is a list containing two elements, the parser assumes
    that the last name is the first element in the list, and the first name is
    the last element.  If the list contains only a single element, it is parsed
    as a string.  If the list contains more than two elements, an error is
    raised since only simple cases are handled by the default name parser.

    If the first name contains an element wrapped in double quotes, that is
    extracted and used as the first name.  This is useful for dealing with
    nicknames.

    By default, initials are stripped, unless doing so would result in an empty
    first name.  Initials may be included via the optional keyword argument;
    this should allow the automatic resolution of most name collisions.
    '''

    def parsename(last, first):
        last = last.strip()
        first = first.strip()
        # If `first` contains a nickname, use that
        nickname_split = first.split('"')
        if len(nickname_split) == 1:
            if not initials:
                orig_first = first
                first = ' '.join(x for x in first.split(' ') if not (len(x) == 2 and x.endswith('.')))
                if not first:
                    first = orig_first
        elif len(nickname_split) == 3:
            first = nickname_split[1].strip()
        else:
            raise RuntimeError('First name {0} cannot be parsed due to unexpected quotations marks'.format(first))
        return '{0} {1}'.format(first, last)

    if isinstance(studentname, list) and len(studentname) == 1:
        studentname = studentname[0]

    if isinstance(studentname, str):
        names = studentname.split(',')
        if len(names) == 1:
            student = names[0].strip()
        elif len(names) == 2:
            student = parsename(names[0], names[1])
        else:
            raise ValueError('The default parsestudentname() cannot parse the name "{0}"'.format(studentname))
    elif isinstance(studentname, list) and len(studentname) == 2:
        student = parsename(studentname[0], studentname[1])
    else:
        raise TypeError('The default parsestudentname() is not equipped to parse names of the form "{0}"'.format(studentname))

    if not student or student.isspace():
        raise RuntimeError('Student name "{0}" parsed to an empty or whitespace value'.format(studentname))

    return student




def _run(data, createdfiles, students, students_raw, student_raw_str,
         verbose, silent, texcmd, texfile, namefile, attemptfile, pythontexcmd,
         msgfilepattern, assigndir, multipleattempts):
    '''
    Generate assignments for all specified students, move the assignments to
    the assigndir, and return a dictionary of solutions.
    '''
    pdffile = '{0}.{1}'.format(texfile.rsplit('.', 1)[0], 'pdf')


    # Clean up any existing message files
    # This ensures that any such files in the future constitute actual messages,
    # rather than leftovers from previous runs
    for f in fnmatch.filter(os.listdir('.'), msgfilepattern):
        os.remove(f)


    for n, (student, student_raw, student_raw_str) in enumerate(zip(students, students_raw, student_raw_str)):
        if student_raw_str not in data:
            data[student_raw_str] = {'name': student,
                                     'name_raw': student_raw,
                                     'solutions': []}

        if namefile is not None:
            with open(namefile, 'w', encoding='utf8') as f:
                f.write('{0}\\endinput\n'.format(student))

        if attemptfile is not None:
            if student_raw_str not in data:
                attempt = 1
            else:
                attempt = len(data[student_raw_str]['solutions']) + 1
            with open(attemptfile, 'w', encoding='utf8') as f:
                f.write('{0}\\endinput\n'.format(attempt))
        else:
            attempt = None

        # For the first student in the list, we need to run tex, then pythontex,
        # then tex again to produce the final pdf.  For subsequent students,
        # the first tex run may be omitted, since the temp files that pythontex
        # needs will already exist, and a following tex run will pick up the
        # modified namefile and attemptfile for the final pdf.
        if n == 0:
            if verbose:
                print('Running command {0}'.format(texcmd))
                subprocess.call(texcmd)
            else:
                if not silent:
                    print('Generating assignment {0}/{1}\r'.format(str(n+1).rjust(len(str(len(students)))), len(students)), end='')
                    sys.stdout.flush()
                try:
                    subprocess.check_output(texcmd)
                except subprocess.CalledProcessError as e:
                    # `output` is bytes; need a string to print nicely under Python 3
                    print(e.output.decode(sys.getdefaultencoding()), file=sys.stderr)
                    raise

        if verbose:
            print('Running command {0}'.format(pythontexcmd))
            subprocess.call(pythontexcmd)
            print('Running command {0}'.format(texcmd))
            subprocess.call(texcmd)
        else:
            if not silent:
                print('Generating assignment {0}/{1}\r'.format(str(n+1).rjust(len(str(len(students)))), len(students)), end='')
                sys.stdout.flush()
            try:
                subprocess.check_output(pythontexcmd)
            except subprocess.CalledProcessError as e:
                print(e.output.decode(sys.getdefaultencoding()), file=sys.stderr)
                raise
            try:
                subprocess.check_output(texcmd)
            except subprocess.CalledProcessError as e:
                print(e.output.decode(sys.getdefaultencoding()), file=sys.stderr)
                raise

        msgs = []
        for fname in fnmatch.filter(os.listdir('.'), msgfilepattern):
            try:
                with open(fname, encoding='utf8') as f:
                    m = json.load(f)
                msgs.append(m)
                assert m['type'] == 'randassign.solutions'
                assert 'id' in m
                assert m['format'] in ('soln', 'addsoln')
                if m['format'] == 'soln':
                    assert isinstance(m['solutions'], str)
                else:
                    assert isinstance(m['solutions'], list)
                    for s in m['solutions']:
                        assert isinstance(s['number'], int)
                        assert isinstance(s['info'], str)
                        assert isinstance(s['solution'], list)
                        assert all(isinstance(x, str) or isinstance(x, int) or isinstance(x, float) for x in s['solution'])
            except:
                print('Invalid message file "{0}"'.format(fname), file=sys.stderr)
                raise

        if all(m['format'] == 'soln' for m in msgs):
            newsoln = [m['solutions'] for m in msgs]
        elif all(m['format'] == 'addsoln' for m in msgs):
            newsoln = sorted((m_i for m_i in m['solutions'] for m in msgs), key=lambda m_i: m_i['number'])
        else:
            raise RuntimeError('Mixing messages in "soln" and "addsoln" format is not allowed')

        data[student_raw_str]['solutions'].append(newsoln)

        # Name files using a sanitized form of the raw student name
        if multipleattempts:
            newfile = os.path.join(assigndir, '{0}_{1}.pdf'.format(student_raw_str.replace('"', '').replace('.', ''), attempt))
        else:
            if len(data[student]['solutions']) > 1:
                raise RuntimeError('Although "multipleattempts" is False, there are multiple solutions for {0}'.format(student))
            newfile = os.path.join(assigndir, '{0}.pdf'.format(student_raw_str.replace('"', '').replace('.', '')))
        # Need `abspath()` to ensure functioning
        createdfiles.append(os.path.abspath(newfile))
        shutil.copy(pdffile, newfile)

    if not silent:
        print(' '*40 + '\r', end='')
        sys.stdout.flush()




def _writesoln(data, verbose=None, silent=None,
               solncmd=None, solnfile=None, solnfmt=None, onlylastsoln=None,
               multipleattempts=None,
               solntemplatedoc=None,
               solntemplatestudent=None,
               solntemplatesolnsattempt=None,
               solntemplatesolnswrapper=None,
               solntemplatesolnsingle=None,
               solntemplatesolnsingleinfo=None,
               solntemplatesolnmultiwrapper=None,
               solntemplatesolnmultiwrapperinfo=None,
               solntemplatesolnmulti=None,
               createdfiles=None):

    '''
    Write solutions in a specified format, using custom templates if supplied.

    The function is defined so that only the first argument, ``data``, is
    required.  The remaining arguments are keyword arguments.  For the default
    ``writesoln()``, all arguments may be needed and all are supplied.
    However, if a custom ``writesoln()`` is supplied by the user, it may not
    need all of these arguments, and may be defined as::

        def writesoln(data, **kwargs):
            ...

    Thus, ``writesoln()`` is always called in the same manner (that need
    not be customized), regardless of whether a custom function is in use and
    without making the creation of custom functions needlessly complex.
    '''

    if solnfmt not in ('tex', 'md', 'markdown'):
        raise RuntimeError('The default solution writer is not equipped to handle the format "{0}"'.format(solnfmt))

    if solnfmt == 'tex':
        solntemplatedoc = solntemplatedoc or _solntemplatedoc_tex
        solntemplatestudent = solntemplatestudent or _solntemplatestudent_tex
        solntemplatesolnsattempt = solntemplatesolnsattempt or _solntemplatesolnsattempt_tex
        solntemplatesolnswrapper = solntemplatesolnswrapper or _solntemplatesolnswrapper_tex
        solntemplatesolnsingle = solntemplatesolnsingle or _solntemplatesolnsingle_tex
        solntemplatesolnsingleinfo = solntemplatesolnsingleinfo or _solntemplatesolnsingleinfo_tex
        solntemplatesolnmultiwrapper = solntemplatesolnmultiwrapper or _solntemplatesolnmultiwrapper_tex
        solntemplatesolnmultiwrapperinfo = solntemplatesolnmultiwrapperinfo or _solntemplatesolnmultiwrapperinfo_tex
        solntemplatesolnmulti = solntemplatesolnmulti or _solntemplatesolnmulti_tex
    elif solnfmt in ('md', 'markdown'):
        solntemplatedoc = solntemplatedoc or _solntemplatedoc_md
        solntemplatestudent = solntemplatestudent or _solntemplatestudent_md
        solntemplatesolnsattempt = solntemplatesolnsattempt or _solntemplatesolnsattempt_md
        solntemplatesolnswrapper = solntemplatesolnswrapper or _solntemplatesolnswrapper_md
        solntemplatesolnsingle = solntemplatesolnsingle or _solntemplatesolnsingle_md
        solntemplatesolnsingleinfo = solntemplatesolnsingleinfo or _solntemplatesolnsingleinfo_md
        solntemplatesolnmultiwrapper = solntemplatesolnmultiwrapper or _solntemplatesolnmultiwrapper_md
        solntemplatesolnmultiwrapperinfo = solntemplatesolnmultiwrapperinfo or _solntemplatesolnmultiwrapperinfo_md
        solntemplatesolnmulti = solntemplatesolnmulti or _solntemplatesolnmulti_md

    allsolutions = []
    for student_raw_str in sorted((k for k in data), key=lambda x: x.split(',')[0]):
        if onlylastsoln:
            solns = [data[student_raw_str]['solutions'][-1]]
            attempts = [len(data[student_raw_str]['solutions'])]
        else:
            solns = data[student_raw_str]['solutions']
            attempts = [n for n in range(1, len(data[student_raw_str]['solutions'])+1)]
        if not multipleattempts:
            if len(data[student_raw_str]['solutions']) > 1:
                raise RuntimeError('Although "multipleattempts" is False, there are multiple solutions for {0}'.format(student))
            else:
                attempts = [None]

        studentsolutions = []
        for attempt, solnset in zip(attempts, solns):
            solution = []
            wrapper = True
            for n, s in enumerate(solnset):
                if isinstance(s, str):
                    solution.append(solntemplatesolnsingle.format(number=n, solution=s))
                    wrapper = False
                elif isinstance(s, dict):
                    if len(s['solution']) == 1:
                        if s['info']:
                            solution.append(solntemplatesolnsingleinfo.format(number=s['number'], info=s['info'], solution=s['solution'][0]))
                        else:
                            solution.append(solntemplatesolnsingle.format(number=s['number'], solution=s['solution'][0]))
                    else:
                        if s['info']:
                            solution.append(solntemplatesolnmultiwrapperinfo.format(number=s['number'], info=s['info'], solution=''.join(solntemplatesolnmulti.format(solution=x) for x in s['solution'])))
                        else:
                            solution.append(solntemplatesolnmultiwrapper.format(number=s['number'], solution=''.join(solntemplatesolnmulti.format(solution=x) for x in s['solution'])))
                else:
                    raise RuntimeError('Invalid solution format')

            if wrapper:
                solution = solntemplatesolnswrapper.format(solution=''.join(solution))
            else:
                solution = ''.join(solution)
            if attempt is not None:
                solution = solntemplatesolnsattempt.format(attempt=attempt) + solution

            studentsolutions.append(solution)

        allsolutions.append(solntemplatestudent.format(name=student_raw_str, solution=''.join(studentsolutions)))

    with open(solnfile, 'w', encoding='utf8') as f:
        f.write(solntemplatedoc.format(solution=''.join(allsolutions)))

    if solncmd:
        cwd = os.getcwd()
        solndir = os.path.split(solnfile)[0]
        if solndir:
            os.chdir(solndir)
        if verbose:
            print('Running command {0}'.format(solncmd))
            subprocess.call(solncmd)
        else:
            if not silent:
                # Final progress message needs to overwrite all previous
                print('Generating solutions\r', end='')
                sys.stdout.flush()
            try:
                subprocess.check_output(solncmd)
            except subprocess.CalledProcessError as e:
                print(e.output.decode(sys.getdefaultencoding()), file=sys.stderr)
                raise
            if not silent:
                print(' '*40 + '\r', end='')
                sys.stdout.flush()
        os.chdir(cwd)




_solntemplatedoc_tex = '''\
\\documentclass[11pt]{{article}}

% Engine-specific settings
% Detect pdftex/xetex/luatex, and load appropriate font packages.
% This is inspired by the approach in the iftex package.
% pdftex:
\\ifx\\pdfmatch\\undefined
\\else
    \\usepackage[T1]{{fontenc}}
    \\usepackage[utf8]{{inputenc}}
\\fi
% xetex:
\\ifx\\XeTeXinterchartoks\\undefined
\\else
    \\usepackage{{fontspec}}
    \\defaultfontfeatures{{Ligatures=TeX}}
\\fi
% luatex:
\\ifx\\directlua\\undefined
\\else
    \\usepackage{{fontspec}}
\\fi
% End engine-specific settings

\\usepackage[margin=1in]{{geometry}}
\\usepackage[shortlabels]{{enumitem}}
\\setlist[description]{{leftmargin=\\parindent, labelindent=\\parindent}}
\\usepackage{{amsmath, amssymb}}
\\usepackage{{siunitx}}


\\title{{Solutions}}
\\author{{}}

\\begin{{document}}
\\maketitle

{solution}

\\end{{document}}
'''


_solntemplatestudent_tex = '''\
\\subsection*{{{name}}}

{solution}

'''


_solntemplatesolnsattempt_tex = '''\

\\subsubsection*{{Attempt {attempt}}}
'''


_solntemplatesolnswrapper_tex = '''\
\\begin{{description}}
{solution}
\\end{{description}}
'''


_solntemplatesolnsingle_tex = '''\
\\item[{number}.] {solution}
'''


_solntemplatesolnsingleinfo_tex = '''\
\\item[{number}.] {info}
    \\begin{{itemize}}
    \\item {solution}
    \\end{{itemize}}
'''


_solntemplatesolnmultiwrapper_tex = '''\
\\item[{number}.] ~
    \\begin{{enumerate}}[(a)]
    {solution}
    \\end{{enumerate}}

'''


_solntemplatesolnmultiwrapperinfo_tex = '''\
\\item[{number}.] {info}

    \\begin{{enumerate}}[(a)]
    {solution}
    \\end{{enumerate}}

'''


_solntemplatesolnmulti_tex = '''\
    \\item {solution}
'''




_solntemplatedoc_md = '''\
# Solutions

{solution}
'''

_solntemplatestudent_md = '''\

## {name}

{solution}

'''

_solntemplatesolnsattempt_md = '''\
### Attempt {attempt}

'''

_solntemplatesolnswrapper_md = '''\
{solution}'''

_solntemplatesolnsingle_md = '''\

**{number}**.  {solution}

'''

_solntemplatesolnsingleinfo_md = '''\

**{number}**.  {info}

  * {solution}

'''

_solntemplatesolnmultiwrapper_md = '''\

**{number}**.

{solution}

'''

_solntemplatesolnmultiwrapperinfo_md = '''\

**{number}**.  {info}

{solution}

'''

_solntemplatesolnmulti_md = '''\
  * {solution}
'''
