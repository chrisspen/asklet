#!/usr/bin/python
from __future__ import print_function
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

print('Loading Wordnet...')
from nltk.corpus import wordnet as wn

#import inspect
from nltk.wsd import lesk
from nltk import word_tokenize
import nltk
from nltk.corpus import wordnet as wn
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.corpus import stopwords

porter = PorterStemmer()
wnl = WordNetLemmatizer()

from asklet import constants as c
from asklet.utils import MatrixUser
from asklet import models

def lemmatize(ambiguous_word):
    """
    Tries to convert a surface word into lemma, and if lemmatize word is not in
    wordnet then try and convert surface word into its stem.
    
    This is to handle the case where users input a surface word as an ambiguous 
    word and the surface word is a not a lemma.
    """
    lemma = wnl.lemmatize(ambiguous_word)
    stem = porter.stem(ambiguous_word)
    # Ensure that ambiguous word is a lemma.
    if not wn.synsets(lemma):
        if not wn.synsets(stem):
            return ambiguous_word
        else:
            return stem
    else:
        return lemma

def lesk(domain, ambiguous_word, context_word):
    
    print('ambiguous_word:',ambiguous_word)
    context_glosses = []
    context_targets = domain.targets.filter(sense__isnull=False, word=context_word)
    for context_target in context_targets.iterator():
        context_glosses.append(context_target.get_all_extended_glosses())
    context_glosses = set((' '.join(context_glosses)).split())
    print('context_word:',context_word)
    print('context_glosses:',context_glosses)
    
    best = (0, None)
    targets = domain.targets.filter(sense__isnull=False, word=ambiguous_word)
    for target in targets.iterator():
        target_glosses = set(target.get_all_extended_glosses().split())
        print('possible sense:',target)
        print('\tpossible glosses:',target_glosses)
        overlaps = target_glosses.intersection(context_glosses)
        print('\t%i overlaps:' % len(overlaps), overlaps)
        best = max(best, (len(overlaps), target))
        print('best:',best)
    
    best_count, best_target = best
    return best_target

def lesk2(domain, ambiguous_word, context_word):
    
    best = (0, None, None)
    print('ambiguous_word:',ambiguous_word)
    print('context_word:',context_word)
    context_targets = domain.targets.filter(sense__isnull=False, word=context_word)
    for context_target in context_targets.iterator():
        context_gloss = context_target.get_all_extended_glosses().split()
        context_gloss_pos = nltk.pos_tag(context_gloss)
        context_gloss = [lemmatize(_) for _, _pos in context_gloss_pos if _pos[:2] in ('NN', 'VB')]
        context_prob = context_target.total_prob
        if context_prob is None:
            context_prob = 1.0
        
        targets = domain.targets.filter(sense__isnull=False, word=ambiguous_word)
        #targets = targets.filter(slug__icontains='extension')
        for target in targets.iterator():
            print('-'*80)
            print('context sense:',context_target)
            print('context gloss:',context_gloss)
            target_gloss = target.get_all_extended_glosses().split()
            target_gloss_pos = nltk.pos_tag(target_gloss)
            target_gloss = [lemmatize(_) for _, _pos in target_gloss_pos if _pos[:2] in ('NN', 'VB')]
            target_prob = target.total_prob
            if target_prob is None:
                target_prob = 1.0
            print('possible sense:',target)
            print('possible gloss:',target_gloss)
            overlaps = set(target_gloss).intersection(context_gloss)
            print('%i overlaps:' % len(overlaps), overlaps)
            best = max(best, (len(overlaps)*context_prob*target_prob, target, context_target))
            print('best:',best)
            #raw_input('<enter>')
        
    best_count, best_target, best_context = best
    return best_target, best_context

class Command(BaseCommand):
    help = 'Infer using semantic-Lesk.'
    args = '<weight_ids>'
    option_list = BaseCommand.option_list + (
        make_option('--domain', default=''),
        make_option('--dryrun', action='store_true', default=False),
        make_option('--continuous', action='store_true', default=False),
        make_option('--verbose', action='store_true', default=False),
        make_option('--force', action='store_true', default=False),
        make_option('--limit', default=100),
        make_option('--target', default=''),
        #make_option('--rules', default=''),
    )
    
    @commit_on_success
    def handle(self, *weight_ids, **options):
        
        dryrun = options['dryrun']
        limit = int(options['limit'])
        domain_id = options['domain']
        verbose = options['verbose']
        target = options['target']
        force = options['force']
        
        try:
            
            q = models.Domain.objects.all()
            if domain_id:
                if domain_id.isdigit():
                    q = q.filter(id=int(domain_id))
                else:
                    q = q.filter(slug=domain_id)
            
            for domain in q.iterator():
                print('Processing domain %s.' % domain)
                weights = models.TargetQuestionWeight.objects.pending_ambiguous(force=force)
                weights = weights.filter(target__domain=domain)
                if target:
                    weights = weights.filter(target__slug=target)
                if weight_ids:
                    weights = weights.filter(id__in=[int(_) for _ in weight_ids])
                print(weights.count())
                for weight in weights.iterator():
                    print(weight)
                    best_target = lesk2(domain, weight.target.word, weight.question.word)
                    print('best_target:',best_target)
#                domain.infer_sl(
#                    continuous=options['continuous'],
#                    limit=limit,
#                    target=options['target'],
#                    #rules=options['rules'],
#                    verbose=verbose)
        finally:
            #if dryrun:
            rollback()
                