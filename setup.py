#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# black --line-length 100
#
# TODO: it is possible to override distutils.dist.Distribution and pass within
#       setup `distclass=MyDistribution`.  However, it's not clear how to
#       remove unsupported commands from possible commands, e.g. `upload_docs`
#       and other unused commands.  They clutter the `--help`.

"""
Python setup_tools setup.py for goto_http_redirect_server.

Based on sample https://github.com/pypa/sampleproject/blob/master/setup.py
and instructions at
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://setuptools.readthedocs.io/en/latest/setuptools.html#automatic-script-creation
"""

import abc
from distutils.cmd import Command
import platform
import os
import sys
import subprocess

from setuptools import setup

from goto_http_redirect_server.goto_http_redirect_server import (
    __version__,
    __author__,
    __url_github__,
    __url_azure__,
    __url_circleci__,
    __url_pypi__,
    __url_issues__,
    __doc__,
)

# XXX: these defaults should match those in tools/ci/service-*.sh files
GOTO_FILE_REDIRECTS = "/usr/local/share/goto_http_redirect_server.csv"
GOTO_CONFIG = "/etc/goto_http_redirect_server.conf"
_HERED = os.path.abspath(os.path.dirname(__file__))
GOTO_SERVICE_FILES = [
    os.path.join(_HERED, "service", file_)
    for file_ in (
        "goto_http_redirect_server.conf",
        "goto_http_redirect_server.service",
        "goto_http_redirect_server.sh",
        "service-install.sh",
        "service-uninstall.sh",
    )
]
PACKAGE_DATA = GOTO_SERVICE_FILES + [
    os.path.join(_HERED, "setup.py"),
    os.path.join(_HERED, "README.md"),
]


# Python version >3.5 ?
PYVER_GT35 = sys.version_info.major >= 3 and sys.version_info.minor > 5


class GotoSetupCommand(Command, abc.ABC):
    """
    Base class for goto_http_redirect_server extra commands.
    Child classes should define attribute string `description` to overwrite
    the setuptools default.
    """

    # override user_options for `--help` output and command-line parsing
    user_options = ()

    def finalize_options(self):
        pass

    def run_print(self, cmd):
        """
        wrap subprocess call with helpful printing
        :param cmd: sequence of strings that is an OS command
        """

        # XXX: self.verbose default is 1, increments to max 2 if `--verbose`
        #      is passed. See
        #      https://github.com/python/cpython/blob/8837dd092fe5ad5184889104e8036811ed839f98/Lib/distutils/dist.py#L148
        #      https://github.com/python/cpython/blob/8837dd092fe5ad5184889104e8036811ed839f98/Lib/distutils/dist.py#L477
        #      https://github.com/python/cpython/blob/8837dd092fe5ad5184889104e8036811ed839f98/Lib/distutils/log.py#L69
        verbose = self.verbose >= 2
        output = None
        try:
            if verbose:
                print(" ".join(cmd), file=sys.stderr)
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as cpe:
            print(str(cpe.output, errors="backslashreplace"), file=sys.stderr)
            print("Command (%s) returned %s" % (" ".join(cmd), cpe.returncode), file=sys.stderr)
        finally:
            if output and verbose:
                print(str(output, errors="backslashreplace"), file=sys.stderr)

    @abc.abstractmethod
    def run(self):
        if "linux" not in platform.system().lower():
            raise NotImplementedError(
                "systemd services are for a Linux system,"
                " this is a %s system." % platform.system()
            )


class systemd_install(GotoSetupCommand):
    """
    install the systemd service

    XXX: uses non-PEP8 class name to avoid different naming in
             python setup.py --help-commands
         and
             python setup.py systemd_install --help
         The first refers to key in setup.cmdclass.
         The second refers to class.__name__.
         Force these to match.
    """

    script = os.path.join(_HERED, "service", "service-install.sh")

    description = (
        "install systemd service files for"
        + " goto_http_redirect_server.service (Linux only) - calls %s" % script
    )

    # these should match service-install.sh
    user_options = [
        ("enable", "e", "enable the systemd service"),
        ("start", "s", "start the systemd service (requires --enable)"),
    ]
    enable = None
    start = None

    def initialize_options(self):
        self.enable = None
        self.start = None

    def run(self):
        super().run()
        # passed to service-install.sh
        opts = []
        opts += ["--enable"] if self.enable else []
        opts += ["--start"] if self.start else []
        self.run_print([self.script] + opts)


class systemd_uninstall(GotoSetupCommand):
    """
    uninstall the systemd service

    XXX: see message about class name in systemd_install
    """

    script = os.path.join(_HERED, "service", "service-uninstall.sh")

    description = (
        "uninstall systemd service files for"
        + " goto_http_redirect_server.service (Linux only) - calls %s" % script
    )

    # these should match service-uninstall.sh
    user_options = [
        ("reload", "r", "reload the systemd service after service removal"),
        ("wipe", "w", "remove configuration and csv files"),
    ]
    reload = None
    wipe = None

    def initialize_options(self):
        self.reload = None
        self.wipe = None

    def run(self):
        super().run()
        # passed to service-uninstall.sh
        opts = []
        opts += ["--reload"] if self.reload else []
        opts += ["--wipe"] if self.wipe else []
        self.run_print([self.script] + opts)


# Get the long description from the README.md file
with open(os.path.join(_HERED, "README.md"), encoding="utf-8") as f_:
    long_description = f_.read()

setup(
    # `setup` arguments are listed at
    # https://github.com/python/cpython/blob/8837dd092fe5ad5184889104e8036811ed839f98/Lib/distutils/dist.py#L1023
    name="goto_http_redirect_server",
    version=__version__,
    author=__author__,
    url=__url_pypi__,
    project_urls={
        "Source": __url_github__,
        "Bug Reports": __url_issues__,
        "CI (Azure)": __url_azure__,
        "CI (CircleCI)": __url_circleci__,
    },
    description=__doc__.splitlines()[0],
    long_description_content_type="text/markdown",
    long_description=long_description,
    license="MIT License",
    install_requires=[],
    setup_requires=["wheel"],
    extras_require={
        # install these locally with command:
        #     python -m pip install --user -e '.[development]'
        "development": [
            "flake8==3.8",
            "mypy==0.812",
            "pytest==6.2" if PYVER_GT35 else "pytest==6.1",
            "pytest-cov==2.11",
            "pytest-timeout==1.4",
            "yamllint==1.26",
        ],
        # subsets of 'development' for faster `pip install` in CI stages
        "development-flake8": [
            "flake8==3.8",
        ],
        "development-mypy": [
            "mypy==0.812",
        ],
        "development-pytest": [
            "pytest==6.2" if PYVER_GT35 else "pytest==6.1",
            "pytest-cov==2.11",
            "pytest-timeout==1.4",
        ],
        "development-yamllint": [
            "yamllint==1.26",
        ],
        "build": [
            "pip",
            "setuptools>=44",
            "twine>=3.3",
            "wheel",
        ],
        "readme": [
            "md_toc",
        ],
    },
    # see https://pypi.org/classifiers/
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    ],
    # keywords should match "topics" listed at github project
    keywords="http-server redirect-urls shortcuts shorturl shorturl-services"
    "shorturls url-shortener",
    python_requires=">=3.5.2",
    packages=["goto_http_redirect_server"],
    # enables `python -m goto-http-redirect-server`
    py_modules=["goto-http-redirect-server"],
    entry_points={
        "console_scripts": [
            "goto_http_redirect_server=goto_http_redirect_server.goto_http_redirect_server:main",
        ],
    },
    # viewable from `python setup.py --help-commands`
    cmdclass={
        "systemd_install": systemd_install,
        "systemd_uninstall": systemd_uninstall,
    },
    package_data={
        "goto_http_redirect_server": PACKAGE_DATA,
    },
    include_package_data=True,
)
