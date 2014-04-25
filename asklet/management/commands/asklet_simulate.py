#!/usr/bin/python
import random
import datetime
import os
import sys
import time
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.db.transaction import commit_on_success
from django.utils import timezone

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

from asklet import constants as c
from asklet.utils import MatrixUser
from asklet import models

class Command(BaseCommand):
    help = 'Plays an arbitrary number of games against an automated user.'
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--seed', default=None),
        make_option('--pause', action='store_true', default=False),
        make_option('--verbose', action='store_true', default=False),
        make_option('--max-sessions', default=1000),
        make_option('--domain', default='test'),
        make_option('--matrix', default='asklet/tests/fixtures/matrix.yaml'),
        )
    
    def print_(self, *args):
        if self.verbose:
            sys.stdout.write(' '.join(map(str, args)))
            sys.stdout.write('\n')
    
    def handle(self, *args, **options):
        if options['seed']:
            random.seed(int(options['seed']))
        
        domains = models.Domain.objects.all()
        self.domain = models.Domain.objects.get(slug=options['domain'])
        
        self.verbose = options['verbose']
        self.pause = options['pause']
        self.max_sessions = int(options['max_sessions'])
        
        print_ = self.print_
        
        self.user = MatrixUser(options['matrix'])
        
        self.progress = [] # [(winner, steps, datetime)]
        self.total_count = 0
        self.correct_count = 0
        self.t0 = time.clock()
        self.record_freq = 10
        tmp_debug = settings.DEBUG
        settings.DEBUG = False
        try:
            for i in xrange(self.max_sessions):
                #self.pause = self.verbose = i+1 >= 500
                if not self.pause:
                    td = time.clock() - self.t0
                    sessions_per_sec = self.total_count/float(td) if td else 0
                    sys.stdout.write('\rProcessing %i of %i. %i correct out of %i. %.02f sessions/sec' \
                        % (i+1, self.max_sessions, self.correct_count, self.total_count, sessions_per_sec))
                    sys.stdout.flush()
                self.run_session(i)
                reset_queries()
        finally:
            settings.DEBUG = tmp_debug
        print('')
        print('Done!')
    
    @commit_on_success
    def run_session(self, i):
        print_ = self.print_
        domain = self.domain
        user = self.user
        
        print_('='*80)
        session = domain.get_session(user)
        print_('System: Welcome to session %i (%i of %i)!' % (session.id, i+1, self.max_sessions))
        print_('System: I know %i questions and %i targets and %i associations.' % (
            domain.questions.all().count(),
            domain.targets.all().count(),
            domain.weights.count(),
        ))
        
        self.total_count += 1
        
        user.think_of_something()
        print_('User thinks of %s.' % user.target)
        
        prior_question_slugs = set()
        for j in xrange(domain.max_questions):
            guess = None
            things = []
            print_('-'*80)
            print_('Question %i' % (j+1,))
            q = session.get_next_question(verbose=self.verbose)
            if q is None:
                print_('System: I give up. What was it?')
                print_('User: %s' % user.target)
                print_('System: Please describe three things about it.')
                domain_question_count = session.domain.questions.all().count()
                session_question_count = session.questions_count()
#                print('')
#                print('domain_question_count:',domain_question_count)
#                print('session_question_count:',session_question_count)
                assert session_question_count >= domain_question_count-2, 'Stopped before max_questions reached: %s' % (session_question_count,)
                things = user.describe(3, exclude=prior_question_slugs)
                self.progress.append((False, j, timezone.now()))
                if self.pause: raw_input('enter')
                break
            elif isinstance(q, models.Question):
                print_('System: %s?' % q.slug)
                answer = user.ask(q.slug)
                print_('User: %s' % answer)
                print_('User is thinking %s.' % user.target)
                models.Answer.objects.create(session=session, question=q, answer=answer)
                if self.pause: raw_input('enter')
            elif isinstance(q, models.Target):
                guess = q
                print_('System: Are you thinking %s?' % q.slug)
                correct = user.is_it(target=q.slug)
                self.correct_count += correct
                print_('User: %s' % correct)
                models.Answer.objects.get_or_create(
                    session=session,
                    guess=q,
                    defaults=dict(answer=c.YES if correct else c.NO))
                if correct:
                    print_('System: Horray!')
                    self.progress.append((True, j, timezone.now()))
                    if self.pause: raw_input('enter')
                    break
                else:
                    print_('System: Aw shucks!')
                    if self.pause: raw_input('enter')
            else:
                raise Exception('Unknown type: %s' % (q,))
            
        session.record_result(guess=guess, actual=user.target, merge=True, attrs=things)
        