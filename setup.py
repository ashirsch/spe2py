from setuptools import setup


def readme():
	with open('README.md') as f:
		return f.read()


setup(
    name='spe2py',
    version='2.0.0',
    description='This module imports a Princeton Instruments LightField (SPE 3.0) file into a python environment.',
    long_description=readme(),
    long_description_content_type='text/markdown',
    author='Alex Hirsch (Zia Lab)',
    author_email='alexander_hirsch@brown.edu',
    url='https://github.com/ashirsch/spe2py',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only'
    ],
    keywords='spectroscopy optics imaging data analysis',
    py_modules=['spe2py', 'spe_loader'],
    install_requires=[
        'numpy',
        'matplotlib',
        'untangle'
    ]
)
