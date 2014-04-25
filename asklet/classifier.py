
#http://stackoverflow.com/questions/2368544/how-can-i-remove-a-column-from-a-sparse-matrix-efficiently
#http://stackoverflow.com/questions/4695337/expanding-adding-a-row-or-column-a-scipy-sparse-matrix
# We need a way to efficiently add/remove specific rows and columns.

class BurgenerClassifier(object):
    """
    A neural network based classification algorithm inspired
    by the 20q program invented by Robin Burgener.
    
    http://www.google.com/patents/US20060230008?dq=Artificial+neural+network+guessing+method+and+game
    """
    
    def __init__(self, features=[], labels=[]):
        # Map feature/label names to indexes
        self._features = list(features) # the "questions"
        self._labels = list(labels) # the "targets"
    
    def fit(self, X, y):
        """
        Will overwrite the matrix weights with the new weights
        in the given training samples.
        """
        todo
        
    def partial_fit(self, X, y):
        """
        Will update the matrix weights with the new weights in the given training samples.
        """
        #todo:handle resizing matrix when new features and/or targets are found
        todo
        
    def score(self, X, y):
        """
        Calculates the model's accuracy predicting the given data set.
        """
        todo
        
    def predict(self, X):
        """
        Returns the most likely class label for the given data.
        """
        todo
        