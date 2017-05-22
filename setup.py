import os
from setuptools import setup, find_packages

root_dir = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(root_dir, "VERSION"), 'r') as version_file:
    version = version_file.read().strip()

setup(
    name="matrix-leaf",
    version=version,
    description="A Matrix (matrix.org) client",
    author="SimonKLB",
    author_email="simonkollberg@gmail.com",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
    ],
    packages=find_packages(exclude=[]),
    install_requires=[
        "matrix-client",
        "urwid"
    ],
    entry_points={
        "console_scripts": [
            "matrix-leaf = leaf.__main__:main"
        ],
    },
)
