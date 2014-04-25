Asklet - A learning algorithm for playing 20 questions
======

Overview
--------

An algorithm for playing [20 questions](http://en.wikipedia.org/wiki/Twenty_Questions),
inspired by [Robin Burgener's implementation](http://www.google.com/patents/US20060230008?dq=Artificial+neural+network+guessing+method+and+game),
which is used to power website [20q.net](http://www.20q.net/).

Note, Burgener's patent filing doesn't completely describe how the target rank
is calculated, so I had to improvise my own method, but otherwise this should
be a faithful implementation of his algorithm.

The project uses [Django](https://www.djangoproject.com/) as a framework
for organizing and managing a game domain, as well as recording games.

Installation
------------

Some dependencies build Python extensions, so make sure you have
the appropriate Python dev package installed for your platform.

e.g. On Ubuntu this would be something like:

    sudo apt-get install python2.7-dev
    
or:

    sudo apt-get install python3-dev

Then install the package via pip:

    pip install asklet
    
If you're installing into the global Python install, as opposed
to a virtualenv, you'll likely need to prefix that with `sudo`.

Testing
-------

For development work, checkout the project using `git` or download and
extract a release tarball.

Then, to run unittests, in the top-level project directory, execute:

    python setup.py test
    
To run unittests for a specific Python version (e.g. 3), execute:

    python setup.py test --pv=3

These commands will automatically create a local virtualenv and install
all required dependencies.

Usage
-----

For using the library as a Django app, start by creating basic Django project.
For reference, see the `asklet/tests` directory, which represents a minimal
Django project.

Then add `asklet` to your `INSTALLED_APPS` and run
`manage.py syncdb; manage.py migrate asket;` to install the models.

For using the library as a stand-alone classifier, TODO.
