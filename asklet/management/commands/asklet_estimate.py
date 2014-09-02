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

def get_weight(subject, predicate, object):
    
    # Check for an explicit weight.
    try:
        return models.TargetQuestionWeight.objects.get(
            target__slug=subject,
            question__conceptnet_predicate=predicate,
            question__conceptnet_object=object
        )
    except models.TargetQuestionWeight.DoesNotExist:
        pass
        
    # Otherwise, attempt inference.

class Command(BaseCommand):
    help = ''
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--domain', default=''),
        make_option('--verbose', action='store_true', default=False),
        )
    
    def handle(self, *edges, **options):
        
        domains = models.Domain.objects.all()
        if options['domain']:
            domains = domains.filter(name=options['domain'])
        
        for domain in domains.iterator():
            for edge in edges:
                a,b,c = edge.split(':')
                print a,b,c
                weight = get_weight(a, b, c)
                print 'weight:',weight