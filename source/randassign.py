# coding: UTF-8
#
# randassign.py
#
# Copyright (c) 2013, Geoffrey M. Poore
# Licensed under the BSD 3-Clause License
# http://opensource.org/licenses/BSD-3-Clause
#

import sys
import os
import shutil
import argparse
try:
    import cpickle as pickle
except:
    import pickle
import subprocess
import textwrap




class RandAssign(object):
    '''
    Class for creating randomized assignments.  Primarily manages the 
    accumulation and creation of per-assignment solutions.
    '''
    def __init__(self, texdir=None, solnfmt='.txt'):
        if texdir is None:
            if os.path.isfile('name.tex'):
                self.texdir = '.'
            elif os.path.isfile(os.path.join('..', 'name.tex')):
                self.texdir = '..'
            else:
                raise RuntimeError('Cannot find helper file "name.tex"; specify the path')
        else:
            if os.path.isfile(os.path.join(texdir, 'name.tex')):
                self.texdir = texdir
            else:
                raise RuntimeError('Cannot find helper file "name.tex"; specify the path')
        
        self.solnfmt = solnfmt
    
        self.soln = []
    
    @property
    def solnfmt(self):
        """Format for solutions.  Accepts `.txt`, `.csv`, and `.tex`."""
        return self._solnfmt
    
    @solnfmt.setter
    def solnfmt(self, value):
        if sys.version_info.major == 2:
            if not isinstance(value, basestring):
                raise TypeError('Solution format must be a string')
        else:
            if not isinstance(value, str):
                raise TypeError('Solution format must be a string')
        if not value.startswith('.'):
            value = '.' + value
        if value not in ('.txt', '.csv', '.tex'):
            raise ValueError('Solution format must be .txt, .csv, or .tex')
        else:
            self._solnfmt = value
    
    @solnfmt.getter
    def solnfmt(self):
        return self._solnfmt
        
    @solnfmt.deleter
    def solnfmt(self):
        del self._solnfmt
    
    def cleanup(self):
        outfile = os.path.join(self.texdir, 'solution' + self.solnfmt)
        f = open(outfile, 'w')
        f.write(''.join(self.soln))
        f.close()




def make(outdir=None, student=None, students=None, texfile=None, texcmd=None, writesoln=None):
    '''
    Make randomized assignments, using default values or options passed
    via the command line.
    
    Standard usage:
    
        from randassign import make
        make()
        
    Default configuration should be sufficient for typical cases.  All 
    typical customization should be able to be accomplished by passing 
    arguments to `make()`.
    '''
    # Process function args
    if texcmd is None:
        texcmd = ['pdflatex', '-interaction=nonstopmode']
    if writesoln is not None:
        if not hasattr(writesoln, '__call__'):
            sys.exit('Argument "writesoln" must be a function')
    else:
        def writesoln(data, outdir, fmt):
            '''
            Write format-dependent solutions
            '''
            if fmt == '.txt':
                f = open(os.path.join(outdir, 'solutions.txt'), 'w')
                for student in data:
                    f.write(student + '\n')
                    f.write('='*len(student) + '\n\n')
                    for attempt, soln in enumerate(data[student]):
                        label = 'Attempt #{0}'.format(str(attempt + 1))
                        f.write(label + '\n')
                        f.write('-'*len(label) + '\n\n')
                        f.write(soln)
                        if not soln.endswith('\n'):
                            f.write('\n\n\n')
                        else:
                            f.write('\n\n')
                    f.write('\n')
                f.close()
            elif fmt == '.csv':    
                f = open(os.path.join(outdir, 'solutions.csv'), 'w')
                f.write('STUDENT, ATTEMPT, SOLUTION\n')
                for student in data:
                    for attempt, soln in enumerate(data[student]):
                        f.write('{0}, {1}, {2}\n'.format(student, str(attempt+1), soln))
                f.close()
            elif fmt == '.tex':
                soln_template = '''
                        \\documentclass[11pt]{{article}}
                        \\usepackage{{amsmath, amssymb}}
                        \\usepackage[margin=1in]{{geometry}}
                        \\usepackage{{siunitx}}
                        \\title{{Solutions for ``{tex_name}''}}
                        \\author{{}}
                        
                        \\begin{{document}}
                        
                        \\maketitle
                        
                        
                        {content}
                        
                        
                        \\end{{document}}
                        '''
                soln_template = textwrap.dedent(soln_template)[1:]
                
                content = []
                for student in data:
                    content.append('\\section*{{{0}}}'.format(student))
                    for attempt, soln in enumerate(data[student]):
                        content.append('\\subsection*{{Attempt {0}}}'.format(str(attempt + 1)))
                        content.append(soln)
                
                f = open(os.path.join(outdir, 'solutions.tex'), 'w')
                f.write(soln_template.format(tex_name=basename.replace('_', '\\_'), content='\n'.join(content)))
                f.close()
                cwd = os.getcwd()
                os.chdir(outdir)
                subprocess.call(texcmd + ['solutions.tex'])
                subprocess.call(texcmd + ['solutions.tex'])
                os.chdir(cwd)
    
    
    
    # Process command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--outdir', default=None,
                        help='directory for created assignments and records')
    parser.add_argument('--student', default=None,
                        help='individual student for whom to create assignment')
    parser.add_argument('--students', default=None, 
                        help='plain text file listing students (one per line)')
    parser.add_argument('TEXFILE', nargs='?', default=None,
                        help='exam file, with or without .tex extension')
    args = parser.parse_args()
    
    # Make sure all paths are OS-appropriate and expanded
    if args.TEXFILE:
        tex_file = os.path.expanduser(os.path.normcase(args.TEXFILE))
        if not tex_file.endswith('.tex'):
            tex_file += '.tex'
        if not os.path.isfile(tex_file):
            sys.exit('Invalid .tex file; does not exist')
    elif texfile:
        tex_file = os.path.expanduser(os.path.normcase(texfile))
        if not tex_file.endswith('.tex'):
            tex_file += '.tex'
        if not os.path.isfile(tex_file):
            sys.exit('Invalid .tex file; does not exist')
    else:
        texfiles = [f for f in os.listdir('.') if f.endswith('.tex') and f not in ('name.tex', 'attempt.tex')]
        if not texfiles:
            sys.exit('No .tex files were found in the current directory')
        elif len(texfiles) > 1:
            sys.exit('Multiple .tex files were found; please specify one')
        else:
            tex_file = texfiles[0]
    pdf_file = tex_file[:-4] + '.pdf'
    doc_dir, basename = os.path.split(tex_file)
    basename = basename[:-4]
    name_file = os.path.join(doc_dir, 'name.tex')
    attempt_file = os.path.join(doc_dir, 'attempt.tex')
    if args.student:
        indiv_student = args.student
    elif student:
        indiv_student = student
    else:
        indiv_student = None
    if args.students:
        student_file = os.path.expanduser(os.path.normcase(args.students))
    elif students:
        student_file = os.path.expanduser(os.path.normcase(students))
    else:
        student_file = 'students.txt'
    if args.outdir:
        outdir = os.path.expanduser(os.path.normcase(args.outdir))
    elif outdir:
        pass
    else:
        outdir = 'randassign_' + basename
    if not os.path.isdir(outdir):
        os.mkdir(outdir)
    
    
    
    # Prepare for run
    # Read in list of students (plain text file, one student per line)
    if os.path.isfile(student_file):
        f = open(student_file, 'r')
        students = [s.rstrip(' \n').replace('  ', ' ').replace('  ', ' ') for s in f.readlines()]
        f.close()
    else:
        sys.exit('Cannot find file "{0}"'.format(student_file))
    # Make dict of student names and lastnames, so can do `--student <lastname>`
    # Store a value of None for duplicate lastnames, so they can be detected
    name_dict = {}
    lastname_dict = {}
    for student in students:
        if ',' in student:
            lastname, firstname = student.split(',')
        else:
            firstname, lastname = student.rsplit(' ', 1)
        if '"' in firstname:
            firstname = firstname.split('"')[1]
        else:
            names = [n for n in firstname.split(' ') if not n.endswith('.')]
            firstname = ' '.join(names)
        name = firstname.strip(' ') + ' ' + lastname.strip(' ')
        name_dict[student] = name
        if lastname not in lastname_dict:
            lastname_dict[lastname.lower()] = student
        else:
            lastname_dict[lastname] = None
    # If a single student has been specified, modify the student list
    # Also make sure the student is valid
    if indiv_student is not None:
        student = indiv_student
        if student not in name_dict:
            if student in lastname_dict:
                student = lastname_dict[student.lower()]
            else:
                sys.exit('Unknown student "{0}"'.format(student))
        students = [student]
    # Load data from the last run, if it exists
    data_file = os.path.join(outdir, 'randassign_' + basename + '.pkl')
    if os.path.isfile(data_file):
        # Backup old data, in case of corruption
        shutil.copy(data_file, data_file + '.bak')
        f = open(data_file, 'rb')
        old_data = pickle.load(f)
        f.close()
    else:
        old_data = None
    # Create a dictionary for storing new data
    data = {}
    # Copy over any old data
    # Use `name_dict` because it contains all names
    for student in name_dict:
        if old_data and student in old_data:
            data[student] = old_data[student]
        else:
            data[student] = []
    
    
    
    # Create assignments
    # Run pdflatex for the first time
    # Make sure there are name and attempt files, to avoid TeX errors
    if not os.path.isfile(name_file):
        f = open(name_file, 'w')
        f.write('Michael Faraday\\endinput\n')
        f.close()
    if not os.path.isfile(attempt_file):
        f = open(attempt_file, 'w')
        f.write('1\\endinput\n')
        f.close()
    subprocess.call(texcmd + [tex_file])
    
    # Loop through all students, creating an assignment for each
    # Make sure there aren't any old solutions hanging around
    soln_file = os.path.join(doc_dir, 'solution')
    for extension in ('.txt', '.csv', '.tex'):
        if os.path.isfile(soln_file + extension):
            os.remove(soln_file + extension)
    for student in students:
        # Save the current name in the file `name.tex`
        name = name_dict[student]
        f = open('name.tex', 'w')
        f.write(name + '\\endinput\n')
        f.close()
        
        # Save the current attempt in the file `attempt.tex`
        attempt = len(data[student]) + 1
        f = open('attempt.tex', 'w')
        f.write(str(attempt) + '\\endinput\n')
        f.close()
        
        # Run PythonTeX
        subprocess.call(['pythontex', '--runall', 'true', tex_file])
        
        # Run pdflatex
        subprocess.call(texcmd + [tex_file])
        
        # Read in and store solutions
        soln_file = os.path.join(doc_dir, 'solution')
        soln_extension = None
        for extension in ('.txt', '.csv', '.tex'):
            if os.path.isfile(soln_file + extension):
                soln_file += extension
                soln_extension = extension
                f = open(soln_file)
                soln = f.read()
                f.close()
                data[student].append(soln)
                break
        if soln_extension is None:
            sys.exit('Missing solutions')
        
        # Move the PDF output to the solutions directory
        pdf_file_named = os.path.join(outdir, '{0}_{1}.pdf'.format(name.replace(' ', '_'), str(attempt)))
        os.rename(pdf_file, pdf_file_named)
    
    # Clean up
    # Need to delete old solutions, so no conflict if format changes in the future
    if os.path.isfile(soln_file):
        os.remove(soln_file)
    
    # Write solutions
    writesoln(data, outdir, soln_extension)
    
    # Save data
    f = open(data_file, 'wb')
    pickle.dump(data, f, -1)
    f.close()




