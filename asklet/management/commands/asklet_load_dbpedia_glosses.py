#!/usr/bin/python
from __future__ import print_function
import random
import re
import datetime
import os
import sys
import time
from optparse import make_option
import urllib2
import tarfile
import traceback
from multiprocessing import cpu_count

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries, OperationalError
from django.db.transaction import commit_on_success, commit
from django.utils import timezone

from joblib import Parallel, delayed

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

import sparql

from asklet import constants as c
from asklet import models

dbpedia_pred = '<http://dbpedia.org/ontology/abstract>'

@commit_on_success
def process(stripe_mod, stripe_num, domain_slug, target_slug=None, commit_freq=10):
    print('%i,%i: Processing...' % (stripe_mod, stripe_num))
    connection.close()
    domain = models.Domain.objects.get(slug=domain_slug)
    
    # Find all targets that haven't been checked for a DBpedia gloss.
    sql = """
select t.id
from asklet_target as t
where t.id not in 
(
    select tqw.target_id
    from asklet_question as q
    inner join asklet_targetquestionweight as tqw on tqw.question_id=q.id
    and q.conceptnet_predicate = %s
    and q.domain_id = %s
    and q.language = 'en'
)
and t.sense IS NULL
and t.domain_id = %s
and t.enabled = true
""" \
+ (" and ((t.id %%%% %s) = %s)" % (stripe_mod, stripe_num) if stripe_mod else '') \
+ (" and t.slug = '%s'" % target_slug if target_slug else '')
    
    #q = q.extra(where=['((id %%%% %i) = %i)' % (stripe_mod, stripe_num)])
    cursor = connection.cursor()
    cursor.execute(sql, [dbpedia_pred, domain.id, domain.id])
    
    s = sparql.Service('http://dbpedia.org/sparql')
    
    lang = 'en'
    print('%i,%i: Counting results...' % (stripe_mod, stripe_num))
    results = list(cursor)
    total = len(results)
    print('%i,%i: %i results found.' % (stripe_mod, stripe_num, total))
    i = 0
    for result in results:
        i += 1
        target_id = result[0]
        try:
            
            target = models.Target.objects.get(id=target_id)
            
            if i == 1 or not i % commit_freq or i == total:
                sys.stdout.write(
                    '%i,%i: %i of %i %.02f%%\n' % (
                        stripe_mod,
                        stripe_num,
                        i,
                        total,
                        i/float(total)*100))
                sys.stdout.flush()
                commit()
            
            # Query DBpedia.
            sparql_str = u"""select ?o where {{
  dbpedia:{slug} {predicate} ?o
  filter (isLiteral(?o))
  filter (lang(?o) = '{lang}')
}}""".format(
                slug=target.word.title(),
                predicate=dbpedia_pred,
                lang=lang)
            #print('sparql_str:',sparql_str)
            abstracts = list(s.query(sparql_str))

            abstract = None
            if abstracts:
                abstract = abstracts[0][0].value.strip().encode('utf-8')
            #print('abstract:',abstract)
                
            question, _ = models.Question.objects.get_or_create(
                slug=None,
                domain=domain,
                enabled=False,
                conceptnet_predicate=dbpedia_pred,
                conceptnet_object=target.slug,
                language=lang,
                defaults=dict(
                    text=abstract,
                )
            )
            models.TargetQuestionWeight.objects.get_or_create(
                target=target,
                question=question,
                defaults=dict(
                    weight=domain.default_inference_count*c.YES,
                    count=domain.default_inference_count,
                ),
            )
            
        except Exception, e:
            traceback.print_exc(file=sys.stderr)
    
class Command(BaseCommand):
    help = 'Downloads gloss text for subjects in DBpedia.'
    args = ''
    option_list = BaseCommand.option_list + (
        #make_option('--seed', default=None),
        make_option('--domain', default=''),
        make_option('--target', default=''),
#        make_option('--fn', default=''),
        make_option('--parts', default=0),
        make_option('--commit-freq', default=10),
#        make_option('--part-name-template',
#            default='assertions/part_%02i.csv'),
    )
    
    def handle(self, *args, **options):
        tmp_settings = settings.DEBUG
        settings.DEBUG = False
        try:
            
            models.SET_QUESTION_INDEX = False
            
            parts = int(options['parts']) or cpu_count()
            commit_freq = int(options['commit_freq'])
            
            target_slug = options['target']
            domain_slug = options['domain']
            domain = models.Domain.objects.get(slug=domain_slug)
            
            print('Launching processes...')
            if parts > 1:
                connection.close()
                Parallel(n_jobs=parts)(
                    delayed(process)(
                        stripe_mod=parts,
                        stripe_num=i,
                        domain_slug=domain_slug,
                        target_slug=target_slug,
                        commit_freq=commit_freq,
                    )
                    for i in range(parts))
            else:
                process(
                    stripe_mod=parts,
                    stripe_num=0,
                    domain_slug=domain_slug,
                    target_slug=target_slug,
                    commit_freq=commit_freq,
                )
            
        finally:
            models.SET_QUESTION_INDEX = True
            settings.DEBUG = tmp_settings
            