#!/usr/bin/env python

from os.path import abspath, dirname, join
from setuptools import setup


def read(name):
    here = abspath(dirname(__file__))
    return open(join(here, f"{name}.md")).read()


setup(
    name="appendlayer",
    version="2.2",
    description="Append a tarball to an image in a container registry",
    long_description="\n\n".join((read("README"), read("CHANGES"))),
    long_description_content_type="text/markdown",
    author="Malthe Borch",
    author_email="mborch@gmail.com",
    url="https://github.com/malthe/appendlayer",
    py_modules=["appendlayer"],
    entry_points={
        "console_scripts": [
            "appendlayer=appendlayer:main",
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    license="MIT",
)
