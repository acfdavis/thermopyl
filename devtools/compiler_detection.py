import os
import sys
import json
import shutil
import subprocess
import tempfile

class CompilerDetection:
    def __init__(self, disable_openmp):
        from distutils.ccompiler import new_compiler
        from distutils.sysconfig import customize_compiler, get_config_vars
        from distutils.errors import DistutilsExecError
        self._DONT_REMOVE_ME = get_config_vars()
        cc = new_compiler()
        customize_compiler(cc)
        self.msvc = cc.compiler_type == 'msvc'
        self._print_compiler_version(cc)
        if disable_openmp:
            self.openmp_enabled = False
        else:
            self.openmp_enabled, openmp_needs_gomp = self._detect_openmp()
        self.sse3_enabled = self._detect_sse3() if not self.msvc else True
        self.sse41_enabled = self._detect_sse41() if not self.msvc else True
        self.compiler_args_sse2  = ['-msse2'] if not self.msvc else ['/arch:SSE2']
        self.compiler_args_sse3  = ['-mssse3'] if (self.sse3_enabled and not self.msvc) else []
        self.compiler_args_sse41, self.define_macros_sse41 = [], []
        if self.sse41_enabled:
            self.define_macros_sse41 = [('__SSE4__', 1), ('__SSE4_1__', 1)]
            if not self.msvc:
                self.compiler_args_sse41 = ['-msse4']
        if self.openmp_enabled:
            self.compiler_libraries_openmp = []
            if self.msvc:
                self.compiler_args_openmp = ['/openmp']
            else:
                self.compiler_args_openmp = ['-fopenmp']
                if openmp_needs_gomp:
                    self.compiler_libraries_openmp = ['gomp']
        else:
            self.compiler_libraries_openmp = []
            self.compiler_args_openmp = []
        if self.msvc:
            self.compiler_args_opt = ['/O2']
        else:
            self.compiler_args_opt = ['-O3', '-funroll-loops']
        print()

    def _print_compiler_version(self, cc):
        from distutils.errors import DistutilsExecError
        print("C compiler:")
        try:
            if self.msvc:
                if not cc.initialized:
                    cc.initialize()
                cc.spawn([cc.cc])
            else:
                cc.spawn([cc.compiler[0]] + ['-v'])
        except DistutilsExecError:
            pass

    def hasfunction(self, funcname, include=None, libraries=None, extra_postargs=None):
        part1 = '''
import os
import json
from distutils.ccompiler import new_compiler
from distutils.sysconfig import customize_compiler, get_config_vars
FUNCNAME = json.loads('%(funcname)s')
INCLUDE = json.loads('%(include)s')
LIBRARIES = json.loads('%(libraries)s')
EXTRA_POSTARGS = json.loads('%(extra_postargs)s')
        ''' % {
            'funcname': json.dumps(funcname),
            'include': json.dumps(include),
            'libraries': json.dumps(libraries or []),
            'extra_postargs': json.dumps(extra_postargs)}
        part2 = '''
get_config_vars()  # DON'T REMOVE ME
cc = new_compiler()
customize_compiler(cc)
for library in LIBRARIES:
    cc.add_library(library)
status = 0
try:
    with open('func.c', 'w') as f:
        if INCLUDE is not None:
            f.write('#include %s\n' % INCLUDE)
        f.write('int main(void) {\n')
        f.write('    %s;\n' % FUNCNAME)
        f.write('}\n')
    objects = cc.compile(['func.c'], output_dir='.',
                         extra_postargs=EXTRA_POSTARGS)
    cc.link_executable(objects, 'a.out')
except Exception as e:
    status = 1
exit(status)
        '''
        tmpdir = tempfile.mkdtemp(prefix='hasfunction-')
        try:
            curdir = os.path.abspath(os.curdir)
            os.chdir(tmpdir)
            with open('script.py', 'w') as f:
                f.write(part1 + part2)
            proc = subprocess.Popen(
                [sys.executable, 'script.py'],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.communicate()
            status = proc.wait()
        finally:
            os.chdir(curdir)
            shutil.rmtree(tmpdir)
        return status == 0

    def _print_support_start(self, feature):
        print(f'Attempting to autodetect {feature:6} support...', end=' ')

    def _print_support_end(self, feature, status):
        if status is True:
            print(f'Compiler supports {feature}')
        else:
            print(f'Did not detect {feature} support')

    def _detect_openmp(self):
        self._print_support_start('OpenMP')
        hasopenmp = self.hasfunction('omp_get_num_threads()', extra_postargs=['-fopenmp', '/openmp'])
        needs_gomp = hasopenmp
        if not hasopenmp:
            hasopenmp = self.hasfunction('omp_get_num_threads()', libraries=['gomp'])
            needs_gomp = hasopenmp
        self._print_support_end('OpenMP', hasopenmp)
        return hasopenmp, needs_gomp

    def _detect_sse3(self):
        self._print_support_start('SSE3')
        result = self.hasfunction('__m128 v; _mm_hadd_ps(v,v)',
                           include='<pmmintrin.h>',
                           extra_postargs=['-msse3'])
        self._print_support_end('SSE3', result)
        return result

    def _detect_sse41(self):
        self._print_support_start('SSE4.1')
        result = self.hasfunction( '__m128 v; _mm_round_ps(v,0x00)',
                           include='<smmintrin.h>',
                           extra_postargs=['-msse4'])
        self._print_support_end('SSE4.1', result)
        return result
