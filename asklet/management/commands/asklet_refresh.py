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
from django.db.models import Q
from django.db.transaction import commit_on_success, commit
from django.utils import timezone

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

from asklet import constants as c
from asklet.utils import MatrixUser
from asklet import models

class Command(BaseCommand):
    help = ''
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--domain', default=''),
        make_option('--dryrun', action='store_true', default=False),
        )
    
    @commit_on_success
    def handle(self, *args, **options):
        
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
            total = tqw_probs.count()
            i = 0
            for tqw in tqw_probs.iterator():
                i += 1
                if i == 1 or not i % 100 or i == total:
                    sys.stdout.write('\rProcessing weight %i of %i %.02f%%.' % (i, total, i/float(total)*100))
                    sys.stdout.flush()
                tqw.save()
            print('\nDone.')
            
            if not dryrun:
                commit()
        
        if dryrun:
            raise Exception
        