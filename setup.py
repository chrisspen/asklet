#!/usr/bin/env python
import os

from setuptools import setup, find_packages, Command

import asklet

def get_reqs():
    reqs = [
        'Django>=1.4.0',
        'six>=1.6.1',
        # Note, you may need to do:
        # sudo apt-get install python3-all-dev
        'PyYAML>=3.11',
        'psycopg2',
        
#        'numpy',
#        'scipy>=0.13.3',
#        'pandas',
#        'patsy',
#        'statsmodels'
#        'ggplot',
        #'pytables',
        #'h5py>=2.3.0',
    ]
    return reqs

class TestCommand(Command):
    description = "Runs unittests."
    
    user_options = [
        ('name=', None,
         'Name of the specific test to run.'),
        ('virtual-env-dir=', None,
         'The location of the virtual environment to use.'),
        ('pv=', None,
         'The version of Python to use. e.g. 2.7 or 3'),
    ]
    
    def initialize_options(self):
        self.name = None
        self.virtual_env_dir = './.env%s'
        self.pv = 2.7
        
    def finalize_options(self):
        pass
    
    def build_virtualenv(self, pv):
        #print('pv=',self.pv)
        virtual_env_dir = self.virtual_env_dir % self.pv
        kwargs = dict(virtual_env_dir=virtual_env_dir, pv=self.pv)
        if not os.path.isdir(virtual_env_dir):
            cmd = 'virtualenv -p /usr/bin/python{pv} {virtual_env_dir}'.format(**kwargs)
            #print(cmd)
            os.system(cmd)
            
            cmd = '. {virtual_env_dir}/bin/activate; easy_install -U distribute; deactivate'.format(**kwargs)
            os.system(cmd)
            
            for package in get_reqs():
                kwargs['package'] = package
                cmd = '. {virtual_env_dir}/bin/activate; pip install -U {package}; deactivate'.format(**kwargs)
                #print(cmd)
                os.system(cmd)
    
    def run(self):
        self.build_virtualenv(self.pv)
        kwargs = dict(pv=self.pv, name=self.name)
        if self.name:
            cmd = '. ./.env{pv}/bin/activate; django-admin.py test --pythonpath=. --settings=asklet.tests.settings asklet.tests.tests.Tests.{name}; deactivate'.format(**kwargs)
        else:
            cmd = '. ./.env{pv}/bin/activate; django-admin.py test --pythonpath=. --settings=asklet.tests.settings asklet.tests; deactivate'.format(**kwargs)
        #print(cmd)
        os.system(cmd)

setup(
    name = 'asklet',
    version = asklet.__version__,
    packages = find_packages(),
    author = 'Chris Spencer',
    author_email = 'chrisspen@gmail.com',
    description = 'A learning algorithm for the 20 questions game.',
    license = 'LGPL',
    url = 'https://github.com/chrisspen/asklet',
    #https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Framework :: Django',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
    zip_safe = False,
    install_requires = get_reqs(),
    cmdclass={
        'test': TestCommand,
    },
)
