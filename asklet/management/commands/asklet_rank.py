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
from django.db.transaction import commit_on_success, rollback
from django.utils import timezone

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

from asklet import constants as c
from asklet.utils import MatrixUser
from asklet import models

class Command(BaseCommand):
    help = 'Given a list of answers, generates a list of ranked targets.'
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--seed', default=None),
        make_option('--domain', default='test'),
        make_option('--question', default=''),
        make_option(
            '--answers',
            default='',
            help='A semi-colon-delimited list of answers formatted as "answer_id:answer_weight".'),
        make_option('--rank-targets', action='store_true', default=False),
        make_option('--rank-questions', action='store_true', default=False),
#        make_option('--pause', action='store_true', default=False),
        make_option('--verbose', action='store_true', default=False),
#        make_option('--max-sessions', default=1000),
        )
    
    @commit_on_success
    def handle(self, *args, **options):
        try:
            if options['seed']:
                random.seed(int(options['seed']))
            
            verbose = options['verbose']
            
            domain = models.Domain.objects.get(slug=options['domain'])
            print(domain)
            
            answers = dict((_.split(':')[0], int(_.split(':')[1])) for _ in options['answers'].split(';') if _.strip())
            print('answers:',answers)
            session = models.Session.objects.create(
                domain=domain,
                user_uuid=models.uuid.uuid4(),
            )
            for question_slug, answer_value in answers.iteritems():
                question = models.Question.objects.get(slug=question_slug, domain=domain)
                session.add_answer(question=question, answer=answer_value)
            
            if options['rank_targets'] or options['rank_questions']:
                target_rankings = domain.rank_targets(
                    session=session,
                    answers=answers,
                    verbose=verbose,
                )
                if target_rankings:
                    print('Targets (most likely to least likely):')
                    for i, (target, rank) in enumerate(target_rankings):
                        print(i, rank, target)
                else:
                    print('No target rankings!')
            
            if options['rank_questions']:
                previous_question_ids = models.Question.objects.filter(slug__in=answers).values_list('id', flat=True)
                question_rankings = domain.rank_questions(
                    targets=[_1 for _1,_2 in target_rankings],
                    previous_question_ids=previous_question_ids)
                if question_rankings:
                    print('Questions (most helpful to least helpful):')
                    for i, (question, rank) in enumerate(question_rankings):
                        print(i, rank, question)
                else:
                    print('No question rankings!')
        finally:
            rollback()
            