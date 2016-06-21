from setuptools import setup
from codecs import open
from os import path

setup(
    name='spe2py',
    version='1.0.0a',
    description='This module imports a Princeton Instruments LightField (SPE 3.0) file into a python environment.',
    author='Alex Hirsch (Zia Lab)',
    author_email='alexander_hirsch@brown.edu',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python 3'
    ],
    keywords='spectroscopy optics imaging data analysis',
    py_modules=['spe2py'],
    install_requires=[
        'numpy',
        'matplotlib',
        'untangle'
    ]
)
