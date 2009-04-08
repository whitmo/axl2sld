from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='axl2sld',
      version=version,
      description="converter script for turning arc .axl files into sdl files",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='whit',
      author_email='whit@opengeo.org',
      url='',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
       'lxml',
       'decorator'
      ],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      axl2sld=axl2sld:main
      sld_explore=axl2sld:explorer
      """,
      )
