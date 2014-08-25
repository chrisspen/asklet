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

print 'Loading Wordnet...'
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

############################################################
# Lesk Algorithm
############################################################

def _compare_overlaps_greedy(context, synsets_signatures, pos=None):
    """
    Calculate overlaps between the context sentence and the synset_signature
    and returns the synset with the highest overlap.
    
    :param context: ``context_sentence`` The context sentence where the ambiguous word occurs.
    :param synsets_signatures: ``dictionary`` A list of words that 'signifies' the ambiguous word.
    :param pos: ``pos`` A specified Part-of-Speech (POS).
    :return: ``lesk_sense`` The Synset() object with the highest signature overlaps.
    """
    max_overlaps = 0
    lesk_sense = None
    for ss in synsets_signatures:
        if pos and str(ss.pos()) != pos: # Skips different POS.
            continue
        overlaps = set(synsets_signatures[ss]).intersection(context)
        if len(overlaps) > max_overlaps:
            lesk_sense = ss
            max_overlaps = len(overlaps)  
    return lesk_sense#, max_overlaps

def lesk2(context_sentence, ambiguous_word, pos=None, dictionary=None):
    """
    This function is the implementation of the original Lesk algorithm (1986).
    It requires a dictionary which contains the definition of the different
    sense of each word. See http://goo.gl/8TB15w

        >>> from nltk import word_tokenize
        >>> sent = word_tokenize("I went to the bank to deposit money.")
        >>> word = "bank"
        >>> pos = "n"
        >>> lesk(sent, word, pos)
        Synset('bank.n.07')
    
    :param context_sentence: The context sentence where the ambiguous word occurs.
    :param ambiguous_word: The ambiguous word that requires WSD.
    :param pos: A specified Part-of-Speech (POS).
    :param dictionary: A list of words that 'signifies' the ambiguous word.
    :return: ``lesk_sense`` The Synset() object with the highest signature overlaps.
    """
    ambiguous_word = lemmatize(ambiguous_word)
    
    if not dictionary:
        dictionary = {}
        for ss in wn.synsets(ambiguous_word):
            dictionary[ss] = ss.definition().split() + (' '.join(ss.examples())).split()
            for _ in ss.hyponyms():#e.g. house plant}, {fungus
                dictionary[ss] += _.definition().split() + (' '.join(_.examples())).split()
#            for _ in ss.hypernyms():#e.g. organism, being
#                dictionary[ss] += _.definition().split() + (' '.join(_.examples())).split()
                
            for _ in ss.member_meronyms():#e.g. plant tissue}, {plant part
                dictionary[ss] += _.definition().split() + (' '.join(_.examples())).split()
            for _ in ss.part_meronyms():#e.g. plant tissue}, {plant part
                dictionary[ss] += _.definition().split() + (' '.join(_.examples())).split()
            for _ in ss.substance_meronyms():#e.g. plant tissue}, {plant part
                dictionary[ss] += _.definition().split() + (' '.join(_.examples())).split()

#            for _ in ss.member_holonyms():#e.g. Plantae, kingdom Plantae, plant kingdom
#                dictionary[ss] += _.definition().split() + (' '.join(_.examples())).split()
#            for _ in ss.part_holonyms():#e.g. Plantae, kingdom Plantae, plant kingdom
#                dictionary[ss] += _.definition().split() + (' '.join(_.examples())).split()
#            for _ in ss.substance_holonyms():#e.g. Plantae, kingdom Plantae, plant kingdom
#                dictionary[ss] += _.definition().split() + (' '.join(_.examples())).split()
    best_sense = _compare_overlaps_greedy(context_sentence,
                                       dictionary, pos)
    return best_sense

#import pykov
import itertools
from functools import partial
from nltk.corpus import wordnet_ic
semcor_ic = wordnet_ic.ic('ic-semcor.dat')

def mihalcea(context_sentence, ambiguous_word, pos=None, dictionary=None, metric='path_similarity', ic=None):
    """
    https://github.com/opencog/opencog/blob/master/opencog/nlp/wsd/README
    http://riccardoscalco.github.io/Pykov/getting_started.html
    http://riccardoscalco.github.io/Pykov/getting_started.html#pykov.Chain.steady
    
    wn.synset('dog.n.01')
    
    sudo apt-get install python-sparse
    
    -path_similarity
    -lch_similarity
    -wup_similarity
    -res_similarity
    -jcn_similarity
    -lin_similarity
    """
    ambiguous_word = lemmatize(ambiguous_word)
    
    parts = nltk.pos_tag(context_sentence)
    print parts
    
    lemmatized_context_sentence = map(lemmatize, context_sentence)
    print lemmatized_context_sentence
#    context_sentence = [porter.stem(i) for i in context_sentence]
#    print context_sentence
    
    chainable = []
    chainable_words = []
    for (word, word_pos), lemma in zip(parts, lemmatized_context_sentence):
        if word_pos[:2] not in ('NN', 'VB'):
            continue
        #chainable.append(list(_.name() for _ in wn.synsets(lemma, pos=word_pos[0].lower())))
        chainable.append(list(wn.synsets(lemma, pos=word_pos[0].lower())))
        chainable_words.append(word)
    print chainable
    
    #chain = pykov.Chain()
    weights = {}
    paths = [] # [(total,path)]
    last_synsets = None
    for synsets in itertools.product(*chainable):
        total = 0
        for a, b in zip(synsets, synsets[1:]):
            if (a, b) not in weights:
                method = getattr(a, metric)
                if ic:
                    weights[(a, b)] = method(b, ic)
                else:
                    weights[(a, b)] = method(b)
            total += weights[(a, b)]
        paths.append((total, synsets))
    paths.sort()
    best_score, best_synset_chain = paths[-1]
    #print 'best:',best_score, best_synset_chain
    
    target_index = chainable_words.index(ambiguous_word)
    return best_synset_chain[target_index]

def mihalcea_lch(*args, **kwargs):
    kwargs['metric'] = 'lch_similarity'
    return mihalcea(*args, **kwargs)

def mihalcea_wup(*args, **kwargs):
    kwargs['metric'] = 'wup_similarity'
    return mihalcea(*args, **kwargs)

def mihalcea_res(*args, **kwargs):
    kwargs['metric'] = 'res_similarity'
    kwargs['ic'] = semcor_ic
    return mihalcea(*args, **kwargs)

def mihalcea_jcn(*args, **kwargs):
    kwargs['metric'] = 'jcn_similarity'
    kwargs['ic'] = semcor_ic
    return mihalcea(*args, **kwargs)

def mihalcea_lin(*args, **kwargs):
    kwargs['metric'] = 'lin_similarity'
    kwargs['ic'] = semcor_ic
    return mihalcea(*args, **kwargs)

from pywsd.lesk import simple_lesk, cosine_lesk, adapted_lesk, original_lesk

class Command(BaseCommand):
    help = ''
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--domain', default='test'),
        make_option('--verbose', action='store_true', default=False),
        )
    
    def handle(self, *args, **options):
        
#        synsets = wn.synsets('cat', pos=wn.NOUN)
#        for synset in synsets:
#            print synset.name()
#            print '\tdef:',synset.definition()
#            print '\texamples:',synset.examples()
#            print '\tlemma:',[str(lemma.name()) for lemma in synset.lemmas()]
#        return

        #s, word, pos = "I went to the bank to deposit money.", 'bank', 'n'
        samples = [
#            ("The cat has a fluffy tail.", 'cat', 'n', 'cat.n.01'),
            ("The cat ate the mouse.", 'cat', 'n', 'cat.n.01'),
#            ("My cat likes to eat mice.", 'cat', 'n', 'cat.n.01'),
#            ("The cat meows.", 'cat', 'n', 'cat.n.01'),
#            ("house cats are a type of feline.", 'cat', 'n', 'cat.n.01'),
#            ("the cat has been domesticated.", 'cat', 'n', 'cat.n.01'),
        ]
        
        methods = [
#            (lesk, word_tokenize, True),
#            (lesk2, word_tokenize, True),
#            (simple_lesk, str, True),
#            (cosine_lesk, str, False),
#            (adapted_lesk, str, True),
#            (original_lesk, str, False),
            (mihalcea, word_tokenize, True),
            (mihalcea_lch, word_tokenize, True),
            (mihalcea_wup, word_tokenize, True),
            (mihalcea_res, word_tokenize, True),
            (mihalcea_jcn, word_tokenize, True),
            (mihalcea_lin, word_tokenize, True),
        ]
        
        from collections import defaultdict
        scores = defaultdict(int)
        
        for s, word, pos, correct_answer in samples:
            print s
            for lesk_method, toker, takes_pos in methods:
                sent = toker(s)
                args = [sent, word]
                if takes_pos:
                    args += [pos]
                synset = lesk_method(*args)
                if synset:
                    print '\t',lesk_method.func_name,':', synset.name(), synset.definition()#, synset.examples()
                    scores[lesk_method.func_name] += synset.name() == correct_answer
                else:
                    print '\t',lesk_method.func_name,':', None
                    scores[lesk_method.func_name] += 0
        
        print '-'*80
        print 'scores:',scores
        