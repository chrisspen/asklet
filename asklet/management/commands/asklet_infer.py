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
    help = 'Generates weights using user-defined inference rules.'
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--domain', default=''),
        make_option('--dryrun', action='store_true', default=False),
        make_option('--continuous', action='store_true', default=False),
        make_option('--verbose', action='store_true', default=False),
        make_option('--limit', default=1000),
        make_option('--target', default=''),
    )
    
    @commit_on_success
    def handle(self, *args, **options):
        
        dryrun = options['dryrun']
        limit = int(options['limit'])
        domain_id = options['domain']
        verbose = options['verbose']
        
        q = models.Domain.objects.all()
        if domain_id:
            if domain_id.isdigit():
                q = q.filter(id=int(domain_id))
            else:
                q = q.filter(slug=domain_id)
        
        for domain in q.iterator():
            print('Processing domain %s.' % domain)
            domain.infer(
                continuous=options['continuous'],
                limit=limit,
                target=options['target'],
                verbose=verbose)
            