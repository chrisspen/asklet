import sys
import random
import time
from collections import defaultdict

from django.test import TestCase
from django.db.utils import IntegrityError
from django.db import transaction
from django.utils import timezone
from django.core.management import call_command

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

import yaml

from asklet import models
from asklet import constants as c
from asklet import utils

# Ensure our random selections are deterministic for easier testing.
random.seed(0)

class Tests(TestCase):
    
    fixtures = ['test_data.yaml']
    
    def setUp(self):
        pass
    
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
        
        try:
            # Duplicates should be prevented.
            q4 = models.Question.objects.create(domain=domain, slug='barks')
            #print(q4.index)
            self.assert_(0)
        except IntegrityError:
            pass
    
    def test_learn_manual(self):
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        domain = models.Domain.objects.get(slug='test')
        
        mu = utils.MatrixUser('asklet/tests/fixtures/matrix.yaml')
        mu.target = 'bird'
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
        
        q1 = models.Question.objects.create(domain=domain, slug='has_fur')
        #q2 = models.Question.objects.create(domain=domain, slug='has_wings')
        #q3 = models.Question.objects.create(domain=domain, slug='barks')
        bat = models.Target.objects.create(domain=domain, slug='bat')
        rat = models.Target.objects.create(domain=domain, slug='rat')
        
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
        
    def test_learn_auto(self):
        """
        Confirms the system can learn a toy knowledgebase from scratch.
        Should obtain 100% accuracy within the first 100 sessions.
        """
        domains = models.Domain.objects.all()
        self.assertEqual(domains.count(), 1)
        domain_name = 'test'
        
        call_command('asklet_simulate', max_sessions=100, domain=domain_name)
        
        domain = models.Domain.objects.get(slug=domain_name)
        history = domain.accuracy_history()
        #print('history:',history)
        self.assertEqual(history[-1], 1.0)
        