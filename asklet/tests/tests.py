import sys
import random
import time
from collections import defaultdict

from django.test import TestCase
from django.db.utils import IntegrityError
from django.utils import timezone

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

import yaml

from asklet import models
from asklet import constants as c

#cat,dog,pig,rat,bat,bird,human
#plane,car,truck,train,motorcycle
#tree,shrub,flower,moss,carrot,lettuce

# Ensure our random selections are deterministic for easier testing.
random.seed(0)

def plot(seq, fn, title, xname, yname):
    
    from ggplot import ggplot, aes, geom_point, xlab, ylab, ggsave
    from pandas import DataFrame
    
    data = DataFrame([dict(x=x, y=y) for x,y in enumerate(data)])
    
    plot = ggplot(
        aes(x='x', y='y'), data=data) + \
        geom_point(color='blue') + \
        ggtitle(title) + \
        xlab(xname) + \
        ylab(yname) #+ \
        #xlim(0, max(data['x'])) + \
        #ylim(0, max(data['y']))
    ggsave(plot, fn)

class Tests(TestCase):
    
    fixtures = ['test_data.yaml']
    
    def setUp(self):
        pass
    
    def test_models(self):
        domain = models.Domain.objects.create(slug='_test')
        
        # Question index should be automatically incremented per domain.
        q1 = models.Question.objects.create(domain=domain, slug='has_fur')
        print(q1.index)
        q2 = models.Question.objects.create(domain=domain, slug='has_wings')
        print(q2.index)
        q3 = models.Question.objects.create(domain=domain, slug='barks')
        print(q3.index)
        self.assertEqual(q3.index, 2)
        
        try:
            # Duplicates should be prevented.
            q4 = models.Question.objects.create(domain=domain, slug='barks')
            print(q4.index)
            self.assert_(0)
        except IntegrityError:
            pass
    
    def test_learn_manual(self):
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        domain = models.Domain.objects.get(slug='test')
        
        mu = MatrixUser('asklet/tests/fixtures/matrix.yaml')
        mu.target = 'bird'
        print(mu.target)
        
        session = domain.get_session(mu)
        q = session.get_next_question()
        self.assertEqual(q, None)
        things = mu.describe(3)
        session.record_result(guess=None, actual=mu.target, merge=True, attrs=things)
        self.assertEqual(session.merged, True)
        
        weights = list(domain.weights)
        print(weights)
        self.assertEqual(len(weights), 3)
        self.assertTrue(weights[0].weight)
        
    def test_learn_auto(self):
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        domain = models.Domain.objects.get(slug='test')
        
        verbose = True
        
        def print_(*args):
            if verbose:
                sys.stdout.write(' '.join(map(str, args)))
                sys.stdout.write('\n')
        
        mu = MatrixUser('asklet/tests/fixtures/matrix.yaml')
        
        max_sessions = 10000
        progress = [] # [(winner, steps, datetime)]
        total_count = 0
        correct_count = 0
        t0 = time.clock()
        record_freq = 10
        for i in xrange(max_sessions):
            pause = verbose = i+1 >= 500
            if not pause:
                td = time.clock() - t0
                sessions_per_sec = total_count/float(td) if td else 0
                sys.stdout.write('\rProcessing %i of %i. %i correct out of %i. %.02f sessions/sec' \
                    % (i, max_sessions, correct_count, total_count, sessions_per_sec))
                sys.stdout.flush()
            print_('='*80)
            session = domain.get_session(mu)
            print_('System: Welcome to session %i (%i of %i)!' % (session.id, i+1, max_sessions))
            print_('System: I know %i questions and %i targets and %i associations.' % (
                domain.questions.all().count(),
                domain.targets.all().count(),
                domain.weights.count(),
            ))
            
            total_count += 1
            
            mu.think_of_something()
            print_('User thinks of %s.' % mu.target)
            self.assertTrue(mu.target)
            
            prior_question_slugs = set()
            for j in xrange(domain.max_questions):
                print_('-'*80)
                print_('Question %i' % (j+1,))
                q = session.get_next_question()
                if q is None:
                    print_('System: I give up. What was it?')
                    print_('User: %s' % mu.target)
                    print_('System: Please describe three things about it.')
                    things = mu.describe(3, exclude=prior_question_slugs)
                    session.record_result(guess=None, actual=mu.target, merge=True, attrs=things)
                    progress.append((False, j, timezone.now()))
                    if pause: raw_input('enter')
                    break
                elif isinstance(q, models.Question):
                    print_('System: %s?' % u(q))
                    answer = mu.ask(q.slug)
                    print_('User: %s' % answer)
                    print_('User is thinking %s.' % mu.target)
                    models.Answer.objects.create(session=session, question=q, answer=answer)
                    if pause: raw_input('enter')
                elif isinstance(q, models.Target):
                    print_('System: Are you thinking %s?' % u(q))
                    correct = mu.is_it(target=q.slug)
                    correct_count += correct
                    print_('User: %s' % correct)
                    if correct:
                        print_('System: Horray!')
                        session.record_result(guess=q, actual=mu.target, merge=True)
                        progress.append((True, j, timezone.now()))
                        if pause: raw_input('enter')
                        break
                    else:
                        models.Answer.objects.create(session=session, guess=q, answer=c.YES if correct else c.NO)
                        print_('System: Aw shucks!')
                        if pause: raw_input('enter')
                else:
                    raise Exception('Unknown type: %s' % (q,))
    
    def _test_h5py(self):
        import h5py
        f = h5py.File("/tmp/asklet-test.hdf5", "w")
        dset = f.create_dataset("mydataset", shape=(1000000, 1000000), dtype='int8', maxshape=(None, None), compression='gzip')
        print(dset.shape)
        print(dset.dtype)
        print(dset[0:10])
        print(dir(dset))
        
        #MemoryError
        #dset = dset[:10] + dset[11:]
        
        #MemoryError
#        dset[10:-1] = dset[11:]
#        dset.resize((1000000-1, 1000000))
        
        print(dset.shape)
        
    def _test_numpy(self):
        #http://docs.scipy.org/doc/scipy-0.13.0/reference/generated/scipy.sparse.csc_matrix.html
        #http://docs.scipy.org/doc/scipy-0.13.0/reference/generated/scipy.sparse.lil_matrix.html
        from scipy.sparse import csc_matrix
        from scipy import int8
        
        m = csc_matrix((1000, 1000), dtype=int8)
        print(m)
        pickle.dump(m, open('/tmp/asklet-test.scipy.csc', 'wb'))
        