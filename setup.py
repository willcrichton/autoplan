from setuptools import setup
import os

if __name__ == "__main__":
    setup(name='autoplan',
          version='0.1.0',
          description='A system for program analysis',
          url='http://github.com/willcrichton/autoplan',
          author='Will Crichton and Georgia Sampaio',
          author_email='wcrichto@cs.stanford.edu',
          license='Apache 2.0',
          install_requires=['torch >= 1.0.0', 'scikit-learn >= 0.21.2'],
          packages=['autoplan'],
          zip_safe=False)
