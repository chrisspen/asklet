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
from asklet.utils import ShellUser, sterialize
from asklet import models

class Command(BaseCommand):
    help = ''
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--seed', default=None),
        make_option('--domain', default='test'),
#        make_option('--pause', action='store_true', default=False),
#        make_option('--verbose', action='store_true', default=False),
#        make_option('--max-sessions', default=1000),
        )
    
    
    def handle(self, *args, **options):
        if options['seed']:
            random.seed(int(options['seed']))
        
        domain = self.domain = models.Domain.objects.get(slug=options['domain'])
        
        user = self.user = ShellUser.load()
        print('User ID:',user.id)
        session = self.session = domain.get_session(user.id)
        print('Session:',session.id)
        while 1:
            print('-'*80)
            qi = session.answers.all().count() + 1
            if session.answers.all().count() >= domain.max_questions:
                if not session.target:
                    self.admit_defeat()
                    return
            else:
                if qi == 1:
                    raw_input('Thing of something and I will try to guess it. Press enter when ready.')
                q = session.get_next_question(verbose=1)
                if q is None:
                    self.admit_defeat()
                    return
                elif isinstance(q, models.Question):
                    print('Question %i:' % qi)
                    answer = user.ask(q.slug)
                    models.Answer.objects.create(
                        session=session,
                        question=q,
                        answer=answer)
                elif isinstance(q, models.Target):
                    print('Question %i:' % qi)
                    correct = user.is_it(target=q.slug)
                    if correct:
                        print('Horray!')
                        session.target = q
                        session.winner = True
                        session.save()
                        return
                    else:
                        models.Answer.objects.create(
                            session=session,
                            guess=q,
                            answer=c.YES if correct else c.NO)
                        print('Aw shucks!')

    def admit_defeat(self):
        while 1:
            target = sterialize(raw_input('I give up, what were you thinking? '))
            if target:
                target, _ = models.Target.objects.get_or_create(domain=self.domain, slug=target)
                self.session.target = target
                self.session.winner = False
                self.session.save()
                print("Ah, I see. I'll remember that next time.")
                things = self.user.describe(n=3)
                for question, weight in things:
                    question, _ = models.Question.objects.get_or_create(domain=self.domain, slug=sterialize(question))
                    weightObj, _ = models.TargetQuestionWeight.objects.get_or_create(target=target, question=question)
                    weightObj.weight += weight
                    weightObj.save()
                print("Thanks. Let's play again sometime.")
                return
            else:
                print('Sorry, but this is not a valid response.')
                continue
            