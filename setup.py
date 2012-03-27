#!/usr/bin/env python

from distutils.core import setup

setup(name='imposter',
      version='0.1',
      description='Simple Python based UI for ConnMan',
      author='Daniel Wagner',
      author_email='daniel.wagner@bmw-carit.de',
      url='http://git.bmw-carit.de/?p=imposter.git;a=summary',
      packages=['imposter'],
      package_dir={'imposter': 'src'},
      package_data={'imposter': ['icons/*.png', 'ui/*.ui']},
      data_files=[('share/applications', ['imposter.desktop'])],
      license='GPLv2',
      options={'bdist_rpm': {'requires': 'PyQt4',
                             'group':    'User Interface/Desktops',
                             'vendor':   'The imposter'}},
      scripts=['imposter']
     )
