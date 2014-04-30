#!/usr/bin/python
import random
import re
import datetime
import os
import sys
import time
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.db.transaction import commit_on_success, commit
from django.utils import timezone

from six.moves import cPickle as pickle
from six.moves import range as xrange
from six.moves import input as raw_input
from six import u

from asklet import constants as c
from asklet.utils import MatrixUser
from asklet import models

class ConceptNetEdge(object):
    
    def __init__(self, *args):
        fields = 'uri,rel,start,end,context,weight,sources,id,dataset,surfaceText'.strip().split(',')
#        print('fields:',fields)
#        print('args:',args)
        assert len(args) == len(fields), '%i != %i' % (len(args), len(fields))
        self.__dict__.update(zip(fields, args))
        self.surfaceText = self.surfaceText.strip()
    
    @classmethod
    def from_string(cls, s):
        return cls(*s.split('\t'))
    
    @property
    def surface_parts(self):
        text = self.surfaceText
        parts = [_ for _ in re.split('\[\[|\]\]', text) if _.strip()]
        if len(parts) == 3:
            return parts
    
    @property
    def target_text(self):
        parts = self.surface_parts
        if parts:
            return parts[0].strip()
        text = re.sub('[^a-zA-Z0-9]+', ' ', self.start.split('/')[-1])
        text = re.sub('[ ]+', ' ', text)
        return text
    
    @property
    def target_slug(self):
        return self.start
    
    @property
    def question_text(self):
        parts = self.surface_parts
        if parts:
            return parts[1].strip() + ' ' + parts[2].strip()
        #Not reliable. Makes broken segments.
#        text = re.sub('[^a-zA-Z0-9]+', ' ', self.rel.split('/')[-1].lower() + ' ' + self.end.split('/')[-1])
#        text = re.sub('[ ]+', ' ', text)
#        return text
    
    @property
    def question_slug(self):
        return '%s,%s' % (self.rel, self.end)
    
    @property
    def weight_int(self):
        #typical=1, our typical is 2
        weight = float(self.weight)*2
        weight = min(max(weight, c.NO), c.YES)
        return int(round(weight*1000))
    
    def __str__(self):
        return '%s->%s->%s' % (self.start, self.rel, self.end)

class Command(BaseCommand):
    help = 'Loads targets, questions and weights from a ConceptNet5 CSV dump file.'
    args = ''
    option_list = BaseCommand.option_list + (
        #make_option('--seed', default=None),
        make_option('--domain', default=''),
        make_option('--fn', default=''),
        )
    
    @commit_on_success
    def handle(self, *args, **options):
        tmp_settings = settings.DEBUG
        #TODO:auto-download ConceptNet csv file?
        try:
            domain = models.Domain.objects.get(slug=options['domain'])
            fn = options['fn'].strip()
            assert os.path.isfile(fn)
            commit_freq = 100
    #        import bz2
    #        fin = bz2.BZ2File(fn, 'r')
            import tarfile
            tar = tarfile.open(fn, 'r')
            
            print('Counting total lines...')
            total = 0
#            total = 9855250
            for member in tar:
                print(member)
                fin = tar.extractfile(member)
                total += fin.read().decode('utf8').count('\n')
            #TODO:record line on domain so we can skip if interrupted
            print('%i total lines found.' % total)
    #        return
            
            i = 0
            for member in tar:
                print(member)
                fin = tar.extractfile(member)
                for line in fin:
                    i += 1
                    if i == 1 or not i % commit_freq or i == total:
                        sys.stdout.write('\rProcessing line %i of %i %.02f%%.' % (i, total, i/float(total or i)*100))
                        sys.stdout.flush()
                        commit()
                        reset_queries()
                    line = line.decode('utf8')
    #                print('raw:',line)
                    edge = ConceptNetEdge.from_string(line)
    #                print(edge)
    #                print('fields:',edge.__dict__)
    #                print('target:',edge.target_text)
    #                print('question:',edge.question_text)
    #                print('target slug:',edge.target_slug)
    #                print('question slug:',edge.question_slug)
    #                print('weight:',edge.weight_int)
                    
                    target, _ = models.Target.objects.get_or_create(
                        domain=domain,
                        slug=edge.target_slug,
                        )
                    target.conceptnet_subject = edge.start
                    if edge.target_text:
                        target.text = edge.target_text
                    target.enabled = True
                    target.save()
                    
                    question, _ = models.Question.objects.get_or_create(
                        domain=domain,
                        slug=edge.question_slug,
                        )
                    question.conceptnet_predicate = edge.rel
                    question.conceptnet_object = edge.end
                    if edge.question_text:
                        question.text = edge.question_text
                    question.enabled = True
                    question.save()
                    
                    weight, _ = models.TargetQuestionWeight.objects.get_or_create(
                        target=target,
                        question=question,
                        defaults=dict(
                            weight=edge.weight_int,
                            count=1000,
                        ))
    #                print('normalized weight:',weight.normalized_weight)
    #                
    #                raw_input('enter')
                    #break
        finally:
            settings.DEBUG = tmp_settings
            