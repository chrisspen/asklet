import os
import random
import re
import uuid
import yaml

from six.moves import input as raw_input

from . import constants as c

def sterialize(s):
    s = re.sub('[^a-z0-9_]+', ' ', s.lower())
    s = s.strip().replace(' ', '_')
    return s

def is_int(s):
    try:
        int(s)
        return True
    except TypeError:
        return False

class BaseUser(object):
    """
    The interface the system expects when communicating with a user.
    """
    
    def __init__(self):
        self.target = None
        
    def think_of_something(self):
        """
        Randomly choices a target for the system to guess.
        """
        raise NotImplementedError
        
    def ask(self, question_slug):
        """
        Returns the user's belief in the question's relation
        to our secret target.
        """
        raise NotImplementedError
    
    def is_it(self, target):
        """
        Confirms or denies whether or not the given target is the one we chose.
        """
        raise NotImplementedError
    
    def describe(self, n, exclude=set()):
        """
        Returns 3 random attributes of our target.
        """
        raise NotImplementedError

class MatrixUser(BaseUser):
    """
    An automated user whose knowledge is contained in a matrix.
    """
    
    def __init__(self, fn):
        super(BaseUser, self).__init__()
        self.data = yaml.load(open(fn))
        
    def think_of_something(self):
        """
        Randomly choices a target for the system to guess.
        """
        self.target = random.choice(list(self.data.keys()))
        
    def ask(self, question_slug):
        """
        Returns the user's belief in the question's relation
        to our secret target.
        """
        return self.data[self.target][question_slug]
    
    def is_it(self, target):
        """
        Confirms or denies whether or not the given target is the one we chose.
        """
        return self.target == target
    
    def describe(self, n, exclude=set()):
        """
        Returns 3 random attributes of our target.
        """
        attrs = set(self.data[self.target].keys())
        attrs = list(attrs.difference(exclude))
        random.shuffle(attrs)
        #Don't do this. Otherwise, we'll get the same hints over and over.
        #attrs = sorted(attrs, key=lambda k: self.data[self.target][k], reverse=True)
        attrs = attrs[:n]
        return [(_, self.data[self.target][_]) for _ in attrs]

class ShellUser(BaseUser):
    """
    A user interacting through a shell.
    """
    
    id_filename = '/tmp/asklet_user'
    
    def __init__(self, id=None):
        super(BaseUser, self).__init__()
        self.target = None
        self.id = id or str(uuid.uuid4()).replace('-', '')
        self.save()
    
    @classmethod
    def load(cls):
        """
        Loads the locally saved user id.
        """
        id = None
        fn = cls.id_filename
        if os.path.isfile(fn):
            id = open(fn, 'r').read().strip()
        return cls(id=id)
    
    def clear(self):
        fn = self.id_filename
        if os.path.isfile(fn):
            os.remove(fn)
            
    def save(self):
        fn = self.id_filename
        open(fn, 'w').write(self.id)
    
    def think_of_something(self):
        """
        Randomly choices a target for the system to guess.
        """
        print('Think of something.')
        while 1:
            target = raw_input('Enter it here: ')
            target = sterialize(target)
            if target:
                break
            print('Sorry, but that string is invalid.')
            print('Please enter a simple non-empty string with no punctuation.')
        print('You are thinking of %s.' % target)
        self.target = target
        
    def ask(self, question_slug):
        """
        Returns the user's belief in the question's relation
        to our secret target.
        """
        while 1:
            print('%s? ' % question_slug)
            weight = raw_input('Enter integer weight between %s and %s: ' % (c.YES, c.NO))
            if is_int(weight):
                weight = int(weight)
                if c.YES >= weight >= c.NO:
                    return weight
            print('Sorry, but that weight is invalid.')
    
    def is_it(self, target):
        """
        Confirms or denies whether or not the given target is the one we chose.
        """
        while 1:
            print('%s?' % target)
            yn = raw_input('y/n: ').strip().lower()
            if yn.startswith('y'):
                return True
            elif yn.startswith('n'):
                return False
            print('Sorry, but that response is invalid.')
    
    def describe(self, n=3, exclude=set()):
        """
        Returns 3 random attributes of our target.
        """
        things = []
        assert n > 0
        print('Please describe %i things about this.' % n)
        while len(things) < n:
            response = raw_input('<thing> <weight>')
            response = sterialize(response)
            parts = response.split('_')
            if parts:
                weight = parts[-1]
                if is_int(weight):
                    weight = int(weight)
                    slug = '_'.join(parts[:-1])
                    things.append((slug, weight))
            print('Sorry, but that is an invalid input.')
        return things
    