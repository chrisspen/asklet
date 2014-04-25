
class BaseBackend(object):
    
    def __init__(self, domain):
        self.domain = domain
    
    def add_question(self, q):
        raise NotImplementedError
    
    def add_target(self, t):
        raise NotImplementedError
    
    def remove_question(self, q):
        raise NotImplementedError
    
    def remove_target(self, t):
        raise NotImplementedError