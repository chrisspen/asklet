from __future__ import print_function
import sys
import random
import time
from collections import defaultdict

from django.test import TestCase, TransactionTestCase
from django.db.utils import IntegrityError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.conf import settings
from django.core.management import call_command

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

import yaml

from asklet import models
from asklet import constants as c
from asklet import utils

#Throws: TransactionManagementError: Your database backend doesn't behave properly when autocommit is off. Turn it on before using 'atomic'.
#class Tests(TransactionTestCase):
class Tests(TestCase):
    
    fixtures = ['test_data.yaml']
    
    def setUp(self):

        # Ensure our random selections are deterministic for easier testing.
        random.seed(0)
        
        # Ensure backends are reset to defaults.
        settings.ASKLET_BACKEND = c.SQL
        settings.ASKLET_RANKER = c.SQL
    
    def test_models(self):
        domain = models.Domain.objects.create(slug='_test')
        
        # Question index should be automatically incremented per domain.
        q1 = models.Question.objects.create(domain=domain, slug='has_fur')
        #print(q1.index)
        q2 = models.Question.objects.create(domain=domain, slug='has_wings')
        #print(q2.index)
        q3 = models.Question.objects.create(domain=domain, slug='barks')
        #print(q3.index)
        self.assertEqual(q3.index, 2)
        
        unicode(q3)
        
        try:
            # Duplicates should be prevented.
            with transaction.atomic():
                q4 = models.Question.objects.create(domain=domain, slug='barks')
            #print(q4.index)
            self.assertTrue(0, 'Duplicate question allowed.')
        except IntegrityError:
            pass
        
        bat = models.Target.objects.create(domain=domain, slug='bat')
        
        session = domain.get_session('test-user')
        
        unicode(session)
        
        models.Answer.objects.create(session=session, guess=bat, answer=c.YES)
        try:
            with transaction.atomic():
                models.Answer.objects.create(session=session, guess=bat, answer=c.YES)
            self.assertTrue(0, 'Duplicate answers were given.')
        except IntegrityError:
            pass
    
    def test_learn_manual(self):
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        domain = models.Domain.objects.get(slug='test')
        
        mu = utils.MatrixUser('asklet/tests/fixtures/matrix.yaml')
        mu.target = '/c/en/bird/n/bird'
        #print(mu.target)
        
        session = domain.get_session(mu)
        q = session.get_next_question()
        self.assertEqual(q, None)
        things = mu.describe(3)
        session.record_result(guess=None, actual=mu.target, merge=True, attrs=things)
        self.assertEqual(session.merged, True)
        
        weights = list(domain.weights)
        #print(weights)
        self.assertEqual(len(weights), 3)
        self.assertTrue(weights[0].weight)
        
        q1 = models.Question.objects.create(domain=domain, slug='/r/IsA/,/c/en/has_fur/n/has_fur', enabled=True)
        #q2 = models.Question.objects.create(domain=domain, slug='has_wings', enabled=True)
        #q3 = models.Question.objects.create(domain=domain, slug='barks', enabled=True)
        bat = models.Target.objects.create(domain=domain, slug='/c/en/bat/n/bat', enabled=True)
        rat = models.Target.objects.create(domain=domain, slug='/c/en/rat/n/rat', enabled=True)
        
        session = domain.get_session(user='123')
        
        models.Answer.objects.create(session=session, question=q1, answer=c.YES)
        try:
            with transaction.atomic():
                models.Answer.objects.create(session=session, question=q1, answer=c.YES)
            self.assertTrue(0, 'Duplicate answers were given.')
        except IntegrityError:
            pass
        answers = session.answers.all()
        self.assertEqual(answers.count(), 1)
        
        models.Answer.objects.create(session=session, guess=rat, answer=c.YES)
        try:
            with transaction.atomic():
                models.Answer.objects.create(session=session, guess=rat, answer=c.YES)
            self.assertTrue(0, 'Duplicate guesses were given.')
        except IntegrityError:
            pass
        answers = session.answers.all()
        self.assertEqual(answers.count(), 2)
        
        q = session.get_next_question(
            #verbose=1,#uncomment to debug
        )
        
        q = domain.targets.all()
        for target in q.iterator():
            self.assertTrue(target.sense)
            self.assertTrue(target.enabled)
        
        q = domain.questions.all()
        for question in q.iterator():
            self.assertTrue(question.sense)
            self.assertTrue(question.enabled)
        
    def test_learn_manual_sql(self):
        settings.ASKLET_RANKER = c.SQL
        
        domain = models.Domain.objects.get(slug='test')
        
        q1 = models.Question.objects.create(domain=domain, slug='has_fur', enabled=1)
        q2 = models.Question.objects.create(domain=domain, slug='has_wings', enabled=1)
        q3 = models.Question.objects.create(domain=domain, slug='barks', enabled=1)
        models.Question.objects.all().update(sense=F('slug'))
        
        bat = models.Target.objects.create(domain=domain, slug='bat', enabled=1)
        rat = models.Target.objects.create(domain=domain, slug='rat', enabled=1)
        bird = models.Target.objects.create(domain=domain, slug='bird', enabled=1)
        models.Target.objects.all().update(sense=F('slug'))
        
        mu = utils.MatrixUser('asklet/tests/fixtures/matrix.yaml')
        mu.target = 'bird'
        #print(mu.target)
        
        session = domain.get_session(mu)
        q = session.get_next_question(verbose=0)
        self.assertTrue(q)
#        print(q)
        
    def test_learn_auto(self):
        """
        Confirms the system can learn a toy knowledgebase from scratch.
        Should obtain 100% accuracy within the first 100 sessions.
        """
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        domain_name = 'test'
        
        call_command(
            'asklet_simulate',
            max_sessions=150,
            domain=domain_name,
            matrix='asklet/tests/fixtures/matrix.yaml',
            verbose=0,
            seed=0)
        
        domain = models.Domain.objects.get(slug=domain_name)
        history = domain.accuracy_history()
        #print('history:',history)
        self.assertEqual(history[-1], 1.0)
    
    def test_learn_auto_sql(self):
        """
        Confirms the system can learn a toy knowledgebase from scratch.
        Should obtain 100% accuracy within the first 100 sessions.
        """
        settings.ASKLET_RANKER = c.SQL
        
        matrix_fn = 'asklet/tests/fixtures/matrix.yaml'
        max_sessions = 150
        
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        
        # Set domain to use CWA.
        domain_name = 'test'
        domain = models.Domain.objects.get(slug=domain_name)
        domain.assumption = c.CLOSED
        domain.save()
        
        # Simulate domain using the CWA.
        random.seed(0)
        call_command(
            'asklet_simulate',
            max_sessions=max_sessions,
            domain=domain_name,
            matrix=matrix_fn,
            verbose=0,#enable for debugging messages
            seed=0)
        domain = models.Domain.objects.get(slug=domain_name)
        history = domain.accuracy_history()
        print('closed-world-assumption history:',history)
        self.assertEqual(history[-1], 1.0)
        
        # Reset domain.
        domain.purge(verbose=1)
        self.assertEqual(domain.sessions.all().count(), 0)
        self.assertEqual(domain.targets.all().count(), 0)
        self.assertEqual(domain.questions.all().count(), 0)
        self.assertEqual(domain.weights.count(), 0)
        
        # Change domain to use OWA.
        models.Domain.objects.update()
        domain = models.Domain.objects.get(slug=domain_name)
        domain.assumption = c.OPEN
        domain.save()
        
        # Simulate domain using the OWA.
        random.seed(0)
        call_command(
            'asklet_simulate',
            max_sessions=max_sessions,
            domain=domain_name,
            matrix=matrix_fn,
            verbose=0,#enable for debugging messages
            seed=0)
        domain = models.Domain.objects.get(slug=domain_name)
        history = domain.accuracy_history()
        print('open-world-assumption history:',history)
        self.assertEqual(history[-1], 1.0)
    
    def test_numpy(self):
        import pickle
        import numpy as np
        from scipy.sparse import coo_matrix
        nrow = 10000000
        ncol = 10000000
        m_coo = coo_matrix((nrow, ncol), np.int32)
        #m = m.to_csr()[rows_to_keep, :]
        #m = m.to_csc()[:, cols_to_keep]
        
        #TODO:takes forever?
        #print('To lil...')
        #m_lil = m_coo.tolil()
        
        #print('To dok...')
        m_dok = m_coo.todok()
        ret = m_dok[103, 43534]
        #print(ret)
        
#        print('Saving...')
        pickle.dump(m_coo, open('/tmp/asklet-matrix-coo.pkl','wb'))
        #pickle.dump(m_lil, open('/tmp/asklet-matrix-lil.pkl','wb'))#massive?
        pickle.dump(m_dok, open('/tmp/asklet-matrix-dok.pkl','wb'))
    
    def test_ranking(self):
        
        weights = [
            #(them,us)
            (1,1),
            (4,4),
            (4,3),
            (4,2),
            (4,1),
            (4,0),
            (4,-1),
            (4,-2),
            (4,-3),
            (4,-4),
            (3,-4),
            (2,-4),
            (1,-4),
            (0,-4),
            (-1,-4),
            (-2,-4),
            (-3,-4),
            (-4,-4),
        ]
        for them, us in weights:
            agg1 = models.calculate_target_rank_item1(local_weight=them, answer_weight=us)
            agg2 = models.calculate_target_rank_item2(local_weight=them, answer_weight=us)
            agg3 = models.calculate_target_rank_item3(them, us)
            print(them, us, agg1, agg2, agg3)
            self.assertEqual(agg1, agg2)
            
    def test_domainuser(self):
        """
        Confirms the system can learn a toy knowledgebase from scratch.
        Should obtain 100% accuracy within the first 100 sessions.
        """
        settings.ASKLET_RANKER = c.SQL
        matrix_fn = 'asklet/tests/fixtures/matrix.yaml'
        max_sessions = 150
        domain_name = 'test'
        
        # Train the domain on a matrix.
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        domain = models.Domain.objects.get(slug=domain_name)
        domain.assumption = c.OPEN
        domain.save()
        random.seed(0)
        call_command(
            'asklet_simulate',
            max_sessions=max_sessions,
            domain=domain_name,
            matrix=matrix_fn,
            verbose=0,#enable for debugging messages
            seed=0)
        
        # Test the domain against itself.
        domain.sessions.all().delete()
        random.seed(0)
        call_command(
            'asklet_simulate',
            max_sessions=50,
            domain=domain_name,
            verbose=0,#enable for debugging messages
            seed=0)
        
        domain = models.Domain.objects.get(slug=domain_name)
        history = domain.accuracy_history()
        #print('history:',history)
        self.assertEqual(history[-1], 1.0)
    
    def test_extract_uri(self):
        
        uri = '/c/en/cat'
        self.assertEqual(models.extract_language_code(uri), 'en')
        
        uri = '/c/en/cat/n'
        self.assertEqual(models.extract_pos(uri), 'n')
        
        uri = '/c/en/cat/n/domestic_pet'
        self.assertEqual(models.extract_sense(uri), 'domestic_pet')
        
    def test_rules(self):
        
        domain = models.Domain.objects.get(slug='test')
        domain.allow_inference = True
        domain.save()
        
        r = models.InferenceRule(
            domain=domain,
            name='IsA',
            lhs='?a /r/IsA ?b\n?b /r/IsA ?c',
            rhs='?a /r/IsA ?c')
        r.save()
        
        self.assertEqual(domain.rules.all().count(), 1)
        
        t = domain.create_target('/c/en/cat/n/feline_animal')
        self.assertEqual(t.conceptnet_subject, '/c/en/cat/n/feline_animal')
        self.assertEqual(t.language, 'en')
        self.assertEqual(t.pos, 'n')
        self.assertEqual(t.sense, 'feline_animal')
        
        q = domain.create_question('/r/IsA', '/c/en/feline/n/cat_family')
        self.assertEqual(q.conceptnet_predicate, '/r/IsA')
        self.assertEqual(q.conceptnet_object, '/c/en/feline/n/cat_family')
        self.assertEqual(q.language, 'en')
        self.assertEqual(q.pos, 'n')
        self.assertEqual(q.sense, 'cat_family')
        
        tq1 = models.TargetQuestionWeight.objects.create(target=t, question=q)
        tq1.vote(c.YES)
        self.assertEqual(tq1.nweight, 4.0)
        self.assertEqual(tq1.prob, 1.0)
        
        tq2 = domain.create_weight(
            '/c/en/feline/n/cat_family',
            '/r/IsA',
            '/c/en/mammal/n/warm_blooded_animal')
        tq2.vote(c.YES)
        self.assertEqual(tq2.nweight, 4.0)
        self.assertEqual(tq2.prob, 1.0)
        
        domain.infer(continuous=False, iter_commit=False)
        
        # Confirm "cat IsA mammal" was inferred.
        q = models.TargetQuestionWeight.objects.filter(target__domain=domain)
        self.assertEqual(q.count(), 3)
        tqw = models.TargetQuestionWeight.objects.get(id=3)
        self.assertEqual(tqw.count, 1)
        self.assertEqual(tqw.weight, 4)
        self.assertEqual(tqw.prob, 1.0)
        self.assertEqual(tqw.target.slug, '/c/en/cat/n/feline_animal')
        self.assertEqual(tqw.question.slug, '/r/IsA,/c/en/mammal/n/warm_blooded_animal')
        self.assertEqual(tqw.inferences.all().count(), 1)
        
        domain.infer(continuous=False, iter_commit=False)
        q = models.TargetQuestionWeight.objects.filter(target__domain=domain)
        self.assertEqual(q.count(), 3)
    
    def _test_learn_animals(self):
        """
        Confirms the system can learn a toy knowledgebase from scratch.
        Should obtain 100% accuracy within the first 100 sessions.
        """
        settings.ASKLET_RANKER = c.SQL
        
        matrix_fn = 'asklet/tests/fixtures/animals.yaml'
        max_sessions = 150
        
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        
        # Set domain to use CWA.
        domain_name = 'test'
        domain = models.Domain.objects.get(slug=domain_name)
        domain.assumption = c.CLOSED
        domain.save()
        
        # Simulate domain using the CWA.
        random.seed(0)
        call_command(
            'asklet_simulate',
            max_sessions=max_sessions,
            domain=domain_name,
            matrix=matrix_fn,
            verbose=0,#enable for debugging messages
            seed=0)
        domain = models.Domain.objects.get(slug=domain_name)
        history = domain.accuracy_history()
        print('closed-world-assumption history:',history)
        self.assertEqual(history[-1], 1.0)
        
        # Reset domain.
#        domain.purge(verbose=1)
#        self.assertEqual(domain.sessions.all().count(), 0)
#        self.assertEqual(domain.targets.all().count(), 0)
#        self.assertEqual(domain.questions.all().count(), 0)
#        self.assertEqual(domain.weights.count(), 0)
#        
#        # Change domain to use OWA.
#        models.Domain.objects.update()
#        domain = models.Domain.objects.get(slug=domain_name)
#        domain.assumption = c.OPEN
#        domain.save()
#        
#        # Simulate domain using the OWA.
#        random.seed(0)
#        call_command(
#            'asklet_simulate',
#            max_sessions=max_sessions,
#            domain=domain_name,
#            matrix=matrix_fn,
#            verbose=0,#enable for debugging messages
#            seed=0)
#        domain = models.Domain.objects.get(slug=domain_name)
#        history = domain.accuracy_history()
#        print('open-world-assumption history:',history)
#        self.assertEqual(history[-1], 1.0)

    def test_tree_indexing(self):
        
        settings.ASKLET_RANKER = c.SQL
        matrix_fn = 'asklet/tests/fixtures/matrix.yaml'
        max_sessions = 150
        domain_name = 'test'
        
        # Train the domain on a matrix.
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        domain = models.Domain.objects.get(slug=domain_name)
        domain.use_tree_indexing = True
        domain.assumption = c.OPEN
        domain.save()
        random.seed(0)
        
        # Skip learning and load test data directly into the domain.
        domain.load_yaml_matrix(fn=matrix_fn, verbose=True)
        weights = domain.weights.all()
        self.assertEqual(weights.count(), 432)
        # All questions should have senses.
        weights = domain.weights.filter(question__sense__isnull=True)
        self.assertEqual(weights.count(), 0)
        # All questions should be enabled.
        weights = domain.weights.filter(question__enabled=False)
        self.assertEqual(weights.count(), 0)
        
        call_command(
            'asklet_refresh',
            domain=domain.id,
            jobs=1,
        )
        
        domain.refresh_tree(verbose=1)
        
#        call_command(
#            'asklet_simulate',
#            max_sessions=max_sessions,
#            domain=domain_name,
#            matrix=matrix_fn,
#            verbose=0,#enable for debugging messages
#            seed=0)
        
        # Test the domain against itself. It should have 100% accuracy.
#        domain.sessions.all().delete()
#        random.seed(0)
#        call_command(
#            'asklet_simulate',
#            max_sessions=50,
#            domain=domain_name,
#            verbose=0,#enable for debugging messages
#            seed=0)
#        
#        domain = models.Domain.objects.get(slug=domain_name)
#        history = domain.accuracy_history()
#        #print('history:',history)
#        self.assertEqual(history[-1], 1.0)
