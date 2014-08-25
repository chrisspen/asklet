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
from django.db.transaction import commit_on_success, commit, rollback
from django.utils import timezone

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

from asklet import constants as c
from asklet.utils import MatrixUser
from asklet import models

class Command(BaseCommand):
    help = 'Bulk deletes all inferred weights.'
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--domain', default=''),
        make_option('--dryrun', action='store_true', default=False),
        make_option('--target', default=''),
    )
    
    @commit_on_success
    def handle(self, *args, **options):
        
        dryrun = options['dryrun']
        target = options['target'].strip()
        freq = 1000
        
        try:
            q = models.Domain.objects.all()
            domain_id = options['domain']
            if domain_id:
                if domain_id.isdigit():
                    q = q.filter(id=int(domain_id))
                else:
                    q = q.filter(slug=domain_id)
            
            for domain in q.iterator():
                print('Processing domain %s.' % domain)
                
                weights = models.TargetQuestionWeight.objects.filter(
                    target__domain=domain,
                    inference_depth__isnull=False,
                )
                if target:
                    weights = weights.filter(target__slug=target)
                total = weights.count()
                i = 0
                for weight in weights.iterator():
                    i += 1
                    if i == 1 or not i % freq or i == total:
                        sys.stdout.write('\rDeleting weight %i of %i %.02f%%.' \
                            % (i, total, i/float(total)*100))
                        sys.stdout.flush()
                        if not dryrun:
                            commit()
                    weight.delete()
                print
                
        finally:
            if dryrun:
                rollback()
                