#!/usr/bin/python
import random
import datetime
import os
import sys
import time
from optparse import make_option
from multiprocessing import cpu_count

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.db.models import Q
from django.db.transaction import commit_on_success, commit
from django.utils import timezone

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

from joblib import Parallel, delayed

from asklet import constants as c
from asklet import models

def refresh(stripe_num=0, stripe_mod=0, options={}):
    connection.close()
    dryrun = options['dryrun']
    q = models.Domain.objects.all()
    domain_id = options['domain']
    if domain_id:
        if domain_id.isdigit():
            q = q.filter(id=int(domain_id))
        else:
            q = q.filter(slug=domain_id)
    
    for domain in q.iterator():
        print('Processing domain %s.' % domain)
        
        tqw_probs = models.TargetQuestionWeight.objects\
            .filter(Q(target__domain=domain)&Q(Q(prob__isnull=True)|Q(nweight__isnull=True)))\
            .exclude(count=0)
        if stripe_mod:
            tqw_probs = tqw_probs.extra(where=['((asklet_targetquestionweight.id %%%% %i) = %i)' % (stripe_mod, stripe_num)])
        total = tqw_probs.count()
        i = 0
        for tqw in tqw_probs.iterator():
            i += 1
            if i == 1 or not i % 100 or i == total:
                sys.stdout.write('Processing weight %i of %i %.02f%%.\n' \
                    % (i, total, i/float(total)*100))
                sys.stdout.flush()
                if not dryrun:
                    commit()
            tqw.save()
        print
    
        targets = domain.targets.filter(
            Q(slug_parts__isnull=True)|\
            Q(language__isnull=True)|\
            Q(word__isnull=True)|\
            Q(sense__isnull=True, total_senses__isnull=True)|\
            Q(total_weights__isnull=True)|\
            Q(pos__isnull=True, slug_parts__gt=3)|\
            Q(sense__isnull=True, slug_parts__gt=4))
        if stripe_mod:
            targets = targets.extra(where=['((asklet_target.id %%%% %i) = %i)' % (stripe_mod, stripe_num)])
        total = targets.count()
        print '%i stale targets.' % total
        i = 0
        for r in targets.iterator():
            i += 1
            if i == 1 or not i % 100 or i == total:
                sys.stdout.write('Processing target %i of %i %.02f%%.\n' \
                    % (i, total, i/float(total)*100))
                sys.stdout.flush()
                if not dryrun:
                    commit()
            r.save()
        print
            
        questions = domain.questions.filter(
            Q(conceptnet_object__isnull=False, slug_parts__isnull=True)|\
            Q(conceptnet_object__isnull=False, language__isnull=True)|\
            Q(conceptnet_object__isnull=False, word__isnull=True)|\
            Q(conceptnet_object__isnull=False, object__isnull=True)|\
            Q(total_weights__isnull=True)|\
            Q(conceptnet_object__isnull=False, pos__isnull=True, slug_parts__gt=5)|\
            Q(conceptnet_object__isnull=False, sense__isnull=True, slug_parts__gt=6))
        if stripe_mod:
            questions = questions.extra(where=['((asklet_question.id %%%% %i) = %i)' % (stripe_mod, stripe_num)])
        total = questions.count()
        print '%i stale questions.' % total
        i = 0
        for r in questions.iterator():
            i += 1
            if i == 1 or not i % 100 or i == total:
                sys.stdout.write('Processing question %i of %i %.02f%%.\n' \
                    % (i, total, i/float(total)*100))
                sys.stdout.flush()
                if not dryrun:
                    commit()
            r.save()
        print
    
        if stripe_num == 0:
            missing_targets = domain.missing_targets.all()
            total = missing_targets.count()
            i = 0
            for mt in missing_targets.iterator():
                i += 1
                if i == 1 or not i % 100 or i == total:
                    sys.stdout.write('Processing missing target %i of %i %.02f%%.\n' \
                        % (i, total, i/float(total)*100))
                    sys.stdout.flush()
                    if not dryrun:
                        commit()
                mt.materialize()
            print
    
    if dryrun:
        raise Exception


class Command(BaseCommand):
    help = ''
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--domain', default=''),
        make_option('--dryrun', action='store_true', default=False),
    )
    
    @commit_on_success
    def handle(self, *args, **options):
        
        tmp_settings = settings.DEBUG
        settings.DEBUG = False
        try:
            
            print('Launching processes...')
            stripe_mod = cpu_count()
            connection.close()
            Parallel(n_jobs=stripe_mod)(
                delayed(refresh)(
                    stripe_mod=stripe_mod,
                    stripe_num=i,
                    options=options,
                )
                for i in range(stripe_mod))
                
            print('\nDone.')
        
        finally:
            settings.DEBUG = tmp_settings
            