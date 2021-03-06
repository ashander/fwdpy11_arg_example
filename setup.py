# This is a copy/paste/hack of the fwdpy11 setup.py

from setuptools import setup
from setuptools import Extension
from setuptools.command.build_ext import build_ext
import sys
import pybind11
import fwdpy11
import setuptools
import os

if sys.version_info[0] < 3:
    raise ValueError("Python 3 is required!")

__version__ = '0.0.1'

if sys.version_info < (3, 3):
    raise RuntimeError("Python >= 3.3 required")

if pybind11.__version__ < '2.1.0':
    raise RuntimeError("fwdpy11 >= " + '2.1.0' + " required")


# clang/llvm is default for OS X builds.
# can over-ride darwin-specific options
# with setup.py --gcc install
if '--gcc' in sys.argv:
    USE_GCC = True
    sys.argv.remove('--gcc')
else:
    USE_GCC = False

if '--debug' in sys.argv:
    DEBUG_MODE = True
else:
    DEBUG_MODE = False


class get_pybind_include(object):
    """Helper class to determine the pybind11 include path

    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked. """

    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)


PKGS = ['fwdpy11_arg_example']

INCLUDES = [
    # Path to fwdpy11 headers
    fwdpy11.get_includes(),
    # Path to the fwdpp headers included
    # with fwdpy11
    fwdpy11.get_fwdpp_includes(),
    # Path to pybind11 headers
    get_pybind_include(),
    get_pybind_include(user=True),
    os.path.join(sys.prefix, 'include')
]

LIBRARY_DIRS = [
    os.path.join(sys.prefix, 'lib')
    ]

ext_modules = [
        Extension(
            'fwdpy11_arg_example.wfarg',
            ['fwdpy11_arg_example/wfarg.cc','fwdpy11_arg_example/evolve_generation.cc'],
            library_dirs=LIBRARY_DIRS,
            include_dirs=INCLUDES,
            libraries=['gsl', 'gslcblas'],
            language='c++'
            ),
        ]


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
        f.write('int main (int argc, char **argv) { return 0; }')
        try:
            compiler.compile([f.name], extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14] compiler flag.

    The c++14 is prefered over c++11 (when it is available).
    """
    if has_flag(compiler, '-std=c++14'):
        return '-std=c++14'
    elif has_flag(compiler, '-std=c++11'):
        return '-std=c++11'
    else:
        raise RuntimeError('Unsupported compiler -- at least C++11 support '
                           'is needed!')


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""
    c_opts = {
        'msvc': ['/EHsc'],
        'unix': [],
    }

    if sys.platform == 'darwin' and USE_GCC is False:
        c_opts['unix'] += ['-stdlib=libc++', '-mmacosx-version-min=10.7']

    def build_extensions(self):
        ct = self.compiler.compiler_type
        opts = self.c_opts.get(ct, [])
        if ct == 'unix':
            opts.append('-DVERSION_INFO="%s"' %
                        self.distribution.get_version())
            opts.append(cpp_flag(self.compiler))
            if has_flag(self.compiler, '-fvisibility=hidden') and \
                       (sys.platform != 'darwin' or USE_GCC is True):
                opts.append('-fvisibility=hidden')
            if has_flag(self.compiler, '-g0') and DEBUG_MODE is False:
                opts.append('-g0')
            if DEBUG_MODE is True:
                opts.append('-UNDEBUG')
        elif ct == 'msvc':
            opts.append('/DVERSION_INFO=\\"%s\\"' %
                        self.distribution.get_version())
        for ext in self.extensions:
            ext.extra_compile_args = opts
            if sys.platform == 'darwin' and USE_GCC is False:
                ext.extra_link_args = ['-stdlib=libc++',
                                       '-mmacosx-version-min=10.7']
        build_ext.build_extensions(self)


# Figure out the headers we need to install:
generated_package_data = {}
# for root, dirnames, filenames in os.walk('fwdpy11/headers'):
#     if 'testsuite' not in root and 'examples' not in root and \
#        'python_examples' not in root:
#         g = glob.glob(root+'/*.hh')
#         if len(g) > 0:
#             replace = root.replace('/', '.')
#             # If there's a header file, we add the directory as a package
#             if replace not in PKGS:
#                 PKGS.append(replace)
#             generated_package_data[replace] = ['*.hh']
#         g = glob.glob(root + '/*.hpp')
#         if len(g) > 0:
#             replace = root.replace('/',  '.')
#             # If there's a header file, we add the directory as a package
#             if replace not in PKGS:
#                 PKGS.append(replace)
#             try:
#                 if '*.hpp' not in generated_package_data[replace]:
#                     generated_package_data[replace].append('*.hpp')
#             except:
#                 generated_package_data[replace] = ['*.hpp']
#         g = glob.glob(root+'/*.tcc')
#         if len(g) > 0:
#             replace = root.replace('/', '.')
#             # If there's a template implementation file,
#             # we add the directory as a package
#             if replace not in PKGS:
#                 PKGS.append(replace)
#             try:
#                 if '*.tcc' not in generated_package_data[replace]:
#                     generated_package_data[replace].append('*.tcc')
#             except:
#                 generated_package_data[replace] = ['*.tcc']

long_desc = open("README.rst").read()

setup(
    name='fwdpy11_arg_example',
    version=__version__,
    author='Kevin Thornton',
    author_email='krthornt@uci.edu',
    url='http://molpopgen.github.io/fwdpy11_arg_example',
    classifiers=['Intended Audience :: Science/Research',
                 'Topic :: Scientific/Engineering :: Bio-Informatics',
                 'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)'],
    description='Example of ARG tracking using fwdpp.  Interface provided as fwdpy11 extension.',
    license='GPL >= 3',
    requires=['pybind11', 'numpy', 'fwdpy11', 'msprime'],
    provides=['fwdpy11_arg_example'],
    obsoletes=['none'],
    data_files=[('fwdpy11', ['COPYING', 'README.rst'])],
    long_description=long_desc,
    ext_modules=ext_modules,
    install_requires=['pybind11>=2.1.0', 'fwdpy11>=0.1.2', 'msprime'],
    cmdclass={'build_ext': BuildExt},
    packages=PKGS,
    package_data=generated_package_data,
    zip_safe=False,
)
