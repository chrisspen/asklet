Asklet - A learning algorithm for the 20 questions game
======

An algorithm for playing the
[20 questions](http://en.wikipedia.org/wiki/Twenty_Questions) game,
inspired by [Robin Burgener's implementation](http://www.google.com/patents/US20060230008?dq=Artificial+neural+network+guessing+method+and+game),
which is used to power [20q.net](http://www.20q.net/).

Overview
--------

The project uses [Django](https://www.djangoproject.com/) as a framework
for organizing and managing a game domain, as well as recording games.

Installation
------------

Usage
-----

To run unittests, execute:

    python setup.py test
    
To run unittests for a specific Python version (e.g. 3), execute:

    python setup.py test --pv=3