#!/usr/bin/python3

from distutils.core import setup

setup(name='imposter',
      version='0.2',
      description='Simple Python based UI for ConnMan',
      author='Daniel Wagner',
      author_email='wagi@monom.org',
      url='https://github.com/igaw/imposter',
      packages=['imposter'],
      package_dir={'imposter': 'src'},
      package_data={'imposter': ['icons/*.png', 'ui/*.ui']},
      data_files=[('share/applications', ['imposter.desktop'])],
      license='GPLv2',
      options={'bdist_rpm': {'requires': 'python3-PyQt4',
                             'group':    'User Interface/Desktops',
                             'vendor':   'The imposter'}},
      scripts=['imposter']
     )
