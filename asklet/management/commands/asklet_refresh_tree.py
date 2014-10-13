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
from asklet import models

class Command(BaseCommand):
    help = 'Refreshes the index tree of a domain.'
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--domains', default=''),
        make_option('--verbose', action='store_true', default=False),
        )
    
    def handle(self, **options):
        
        domains = models.Domain.objects.filter(use_tree_indexing=True)
        
        _domains = options['domains'].split(',')
        domain_ids = [_ for _ in _domains if _.strip() and _.isdigit()]
        domain_names = [_ for _ in _domains if _.strip() and not _.isdigit()]
        if domain_ids:
            domains = domains.filter(id__in=domain_names)
        if domain_names:
            domains = domains.filter(name__in=domain_names)
        
        for domain in domains.iterator():
            print('Refreshing tree for domain %s...' % domain)
            domain.refresh_tree(**options)
            