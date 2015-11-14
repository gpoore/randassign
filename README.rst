======================================================
``RandAssign``:  Randomized assignments with PythonTeX
======================================================

:Author: Geoffrey M. Poore
:License: `BSD 3-Clause <http://opensource.org/licenses/BSD-3-Clause>`_

Create randomized assignments with solutions/keys using Python and LaTeX.



Installation
------------

Python 2.7 and 3.2+ are officially supported.

For the latest version, download the source from GitHub_, then run::

    python setup.py install

The package will also be available on PyPI_ (the Python Package Index) soon.
Then it may be installed via::

   pip install randassign

Requires the PythonTeX_ package for LaTeX.  PythonTeX is part of the full
TeX Live installation; it may also be installed via the TeX Live package
manager, or using the Python installation script that is bundled with PythonTeX
(this supports MiKTeX).

 .. _PythonTeX:  https://github.com/gpoore/pythontex

.. _GitHub:  https://github.com/gpoore/randassign

.. _PyPI:  https://pypi.python.org/pypi



Standard usage
--------------

The steps to create a typical randomized assignment are listed below.  Complete
examples are included in the documentation.

* Create a LaTeX document, with ``\usepackage{pythontex}``.  Have this file
  ``\input`` a file ``name.tex`` that contains a placeholder name for the
  person who will take the assignment.  Also ``\input`` a file ``attempt.tex``
  that contains a placeholder integer for the number of attempts the person
  taking the assignment has made (optional).

* Write the assignment within the LaTeX document, using PythonTeX as desired
  to generate random values for parameters.

* At the beginning of each PythonTeX session::

      from randassign import RandAssign
      ra = RandAssign()

  Within the session, add solutions via ``ra.addsoln()``.  This takes
  an arbitrary number of arguments, corresponding to the solutions for a
  single problem; if multiple arguments are received, they are treated as
  the solutions to a multi-part problem.  The optional, keyword argument
  ``info`` is used to pass information about the problem into the
  solutions.  The keyword argument ``number`` may be used to set the
  problem number manually when the problems created in a session are not
  directly sequential.  When solutions are created with ``addsoln()``,
  solutions are formatted automatically; only the actual answers and any
  accompanying info need be provided.

* Alternately, solutions may be created by appending text to the list
  ``ra.soln``.  Solutions created in this way will not be automatically
  numbered and formatted; the user has complete, direct control over the form
  of the solution text.  Any desired linebreaks must be included explicitly as
  ``\n`` in the text that is appended to ``ra.soln``.  This method of creating
  solutions may not be mixed with ``ra.addsoln()``.

* Create a text file ``students.txt`` that contains the names of all
  individuals for whom assignments are to be generated, with one name per line.
  Commas should only appear in names in "Last, First" format.  Put this file
  in the same directory as the LaTeX file.

* Run the command-line utility ``randassign``::

      randassign <tex_file>

  By default, this will create a directory ``randassign`` in the LaTeX file's
  directory.  Within this will be an ``assignments`` directory that contains
  an assignment for each student, and a ``solutions`` directory that contains
  complete solutions for all students within a single PDF document, as well
  as a data file in JSON format.

  Run the ``randassign`` utility again as desired to create additional
  assignments to allow for additional attempts.  Solutions will be updated
  automatically.  Use the ``--student <student>`` command-line flag to
  generate an additional assignment for only a single student.



Error handling
--------------

The ``randassign`` utility (and ``make()`` function) is carefully designed so
that if an error occurs during a run, all assignments generated during that run
will automatically be discarded.  If an error occurs, it should typically be
adequate to resolve the error and then run ``randassign`` again, without
performing any manual cleanup from the failed run.

In the event that automatic cleanup somehow fails, ``randassign`` also creates
backups of the data file in which raw assignment data and metadata are stored.
These are saved in the same directory as the data file, which is by default
in the directory with the solutions.



Customization
-------------

The ``randassign`` utility accepts a limited number of command-line arguments
to customize settings.  Run ``randassign --help`` for a list of available
options.

Further customization is available by creating a Python script and passing
arguments to ``randassign``'s ``make()`` function::

    from randassign import make
    make(texfile='<tex_file>', <kwargs>)

The ``make()`` function accepts the following keyword arguments.  Note that
all paths (all ``*dir`` keywords) are interpreted relative to the LaTeX file's
directory, rather than relative to the current working directory.  This ensures
that LaTeX functions smoothly and does not attempt to write to directories
outside the document directory and its subdirectories.  Absolute paths may be
used when this behavior is not desired.

Unix-style paths with forward slashes, and with leading ``~`` expanding to the
user's home directory, will work under all systems, including Windows.

``argv`` (*bool*) default: ``True``
  Whether to supplement supplied arguments from ``sys.argv``, using the parser
  from the ``randassign`` command-line utility.

``verbose`` (*bool*) default: ``False``
  Verbose output.

``silent`` (*bool*) default: ``False``
  Suppress all output.

``texfile`` (*str*)
  LaTeX file from which to generate assignments.

``texcmd`` (*str* or *list* of *str*) default: ``pdflatex -interaction=nonstopmode``
  Command for compiling LaTeX file (does not include file name).

``pythontexcmd`` (*str* or *list* of *str*) default: ``pythontex --rerun always``
  Command for running PythonTeX (does not include file name).

``randassigndir`` (*str*) default: ``randassign``
  Root directory for saving created assignments and solutions.

``subdirs`` (*bool*) default: ``True``
  Whether to create subdirectories under ``randassigndir`` for assignments and
  solutions.

``assigndir`` (*str*) default: ``assignments``
  Subdirectory for assignments.

``solndir`` (*str*) default: ``solutions``
  Subdirectory for solutions.

``namefile`` (*str*) default: ``name.tex``
  LaTeX file containing the name of the current student.

``attemptfile`` (*str*) default: ``attempt.tex``
  LaTeX file containing the number of the current attempt.

``student`` (*str*) default: ``None``
  An individual student for whome to generate assignments.

``studentfile`` (*str*) default:  ``students.txt``
  File containing the names of all students.  ``txt`` files with names in
  "Last, First" or "First Last" form are accepted, as well as CSV files with
  the first column containing last names and the second column containing first
  names (with no header row).

``parsestudentfile`` (*function*)
  Function for parsing the student file and returning a list of student names
  in the form needed for assignments.  See ``_parsestudentfile`` in ``make.py``
  for an example.

``parsestudentname`` (*function*)
  Function for parsing individual lines/rows of the student file into student
  names in the desired format.

``onlysolutions`` (*bool*) default: ``False``
  Only generate solutions; do not generate any assignments.  Useful for
  regenerating solutions in a different format or with a different template.

``solnfile`` (*str*)  default:  ``solutions.tex``
  Solution file.

``solnfmt`` (*str*)  default:  ``tex``
  Solution file format.  ``tex`` and ``md``/``markdown`` are accepted.

``solncmd`` (*str* or *list* of *str*, or ``None``)  default:  ``pdflatex -interaction=nonstopmode``
  Command for post-processing solution file (does not include file name).
  Should be ``None``/evaluate to ``False`` if no post-processing is desired.

``writesoln`` (*function*)
  Function for writing the solutions, given the solution data, templates, and
  other parameters.  See ``_writesoln()`` in ``make.py`` for an example.

``msgfilepattern`` (*str*) default: ``_randassign.*.json``
  Pattern for identifying "message" files, files containing solutions, that are
  saved by PythonTeX and used to pass data to RandAssign.

``onlylastsoln`` (*bool*) default:  ``False``
  Solutions include all solutions for all attempts for each students, or only
  the solutions from the most recent attempt (all solutions are still saved in
  the data file).

``multipleattempts`` (*bool*) default: ``True``
  Whether multiple attempts will be given for an assignment; this determines
  whether attempts are listed/numbered in solutions.

``randassigndatafile`` (*str*)  default: ``<solndir>/<tex_filename>.<randassigndatafilefmt>``
  File for saving raw solution data and associated metadata.

``randassigndatafilefmt`` (*str*) default: ``json.zip``
  Format for data file.  Accepted options are ``json``, ``json.zip``, and
  ``pickle``/``pkl``.

``solntemplatedoc`` (*str*)
  Template for overall solution document; see examples in ``make.py``.

``solntemplatestudent`` (*str*)
  Template for overall solutions for each student.

``solntemplatesolnsattempt`` (*str*)
  Template for attempt heading.

``solntemplatesolnswrapper`` (*str*)
  Template for wrapping a set of solutions, if the set of solutions needs to be
  preceded and followed by markup.

``solntemplatesolnsingle`` (*str*)
  Template for a one-part solution.

``solntemplatesolnsingleinfo`` (*str*)
  Template for a one-part solution that includes additional info from the
  problem.

``solntemplatesolnmultiwrapper`` (*str*)
  Template for wrapping a multi-part solution.

``solntemplatesolnmultiwrapperinfo`` (*str*)
  Template for wrapping a multi-part solution that includes additional info
  from the problem.

``solntemplatesolnmulti`` (*str*)
  Template for each piece of a multi-part solution.
