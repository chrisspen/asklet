#!/usr/bin/python
from __future__ import print_function
import random
import datetime
import os
import sys
import time
from optparse import make_option
import codecs

out = codecs.getwriter('utf-8')(sys.stdout)

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.db.models import Q, Avg
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

def lesk2(domain, ambiguous_word, context_word, ambiguous_pos=None, predicate=None):
    
    best = (0, None, None)
    print('ambiguous_word:',ambiguous_word)
    print('context_word:',context_word)
    print('ambiguous_pos:',ambiguous_pos)
    context_targets = domain.targets.filter(sense__isnull=False)
    if '/' in context_word:
        context_targets = context_targets.filter(slug=context_word)
    else:
        context_targets = context_targets.filter(word=context_word)
    for context_target in context_targets.iterator():
        context_gloss = context_target.get_all_extended_glosses().split()
        context_gloss_pos = nltk.pos_tag(context_gloss)
        context_gloss = [lemmatize(_) for _, _pos in context_gloss_pos if _pos[:2] in ('NN', 'VB', 'JJ')]
        context_prob = context_target.total_prob
        if context_prob is None:
            context_prob = 1.0
        
        targets = domain.targets.filter(sense__isnull=False, word=ambiguous_word)
        if ambiguous_pos:
            targets = targets.filter(pos=ambiguous_pos)
        #targets = targets.filter(slug__icontains='extension')
        for target in targets.iterator():
            print('-'*80)
            print(u'context sense:',unicode(context_target))
            print('context gloss:',context_gloss)
            
            # Use an explicit weight if one exists.
            bump_prob = None
            if predicate:
                tqw = models.TargetQuestionWeight.objects.filter(
                    question__conceptnet_predicate=predicate
                ).filter(
                    Q(target=target, question__conceptnet_object=context_target.conceptnet_subject)|\
                    Q(target=context_target, question__conceptnet_object=target.conceptnet_subject)
                )
                if tqw.exists():
                    bump_prob = tqw.aggregate(Avg('prob'))['prob__avg']
            
            target_gloss = target.get_all_extended_glosses().split()
            target_gloss_pos = nltk.pos_tag(target_gloss)
            target_gloss = [lemmatize(_) for _, _pos in target_gloss_pos if _pos[:2] in ('NN', 'VB')]
            target_prob = target.total_prob
            if target_prob is None:
                target_prob = 1.0
            print(u'possible sense:',unicode(target))
            print('possible gloss:',target_gloss)
            overlaps = set(target_gloss).intersection(context_gloss)
            print('%i overlaps:' % len(overlaps), overlaps)
            if bump_prob is not None:
                final_prob = bump_prob
            else:
                final_prob = context_prob*target_prob
            best = max(best, (len(overlaps)*final_prob, target, context_target))
            print('best:',best)
            #raw_input('<enter>')
        
    best_count, best_target, best_context = best
    if not best_count:
        return None, None
    return best_target, best_context

def get_pos_polarity(domain_id, predicate):
    sql = "select same_ratio from asklet_pospolarity where domain_id=%s and predicate=%s"
    cursor = connection.cursor()
    cursor.execute(sql, [domain_id, predicate])
    results = list(cursor)
    if results:
        return results[0][0]

class Command(BaseCommand):
    help = 'Infer using semantic-Lesk.'
    args = '<weight_ids>'
    option_list = BaseCommand.option_list + (
        make_option('--domain', default=''),
        make_option('--dryrun', action='store_true', default=False),
        make_option('--continuous', action='store_true', default=False),
        make_option('--verbose', action='store_true', default=False),
        make_option('--force', action='store_true', default=False),
        make_option('--literal', default=''),
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
        literal = options['literal']
        
        try:
            
            q = models.Domain.objects.all()
            if domain_id:
                if domain_id.isdigit():
                    q = q.filter(id=int(domain_id))
                else:
                    q = q.filter(slug=domain_id)
            
            for domain in q.iterator():
                print('Processing domain %s.' % domain)
                
                if literal:
                    subject, predicate, object = literal.split(':')
                    subject_sense = models.extract_sense(subject)
                    object_sense = models.extract_sense(object)
                    if subject_sense:
                        assert not object_sense
                        ambiguous_word=models.extract_word(object)
                        ambiguous_pos=models.extract_pos(subject)
                        context_word=subject
                    else:
                        assert object_sense
                        ambiguous_word=models.extract_word(subject)
                        ambiguous_pos=models.extract_pos(object)
                        context_word=object
                        
                    pos_polarity = get_pos_polarity(domain.id, predicate)
                    print('predicate:',predicate)
                    print('pos_polarity:',pos_polarity)
                    
                    best_target = lesk2(
                        domain,
                        ambiguous_word=ambiguous_word,
                        context_word=context_word,
                        ambiguous_pos=(pos_polarity > 0.5) and ambiguous_pos,
                        predicate=predicate,
                    )
                    print('best_target:',best_target)
                    continue
                
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
                