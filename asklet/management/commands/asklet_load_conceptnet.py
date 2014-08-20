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

from asklet import constants as c
from asklet.utils import MatrixUser
from asklet import models

class ConceptNetEdge(object):
    
    def __init__(self, *args):
        fields = [
            'uri', 'rel', 'start', 'end', 'context',
            'weight', 'sources', 'id', 'dataset', 'surfaceText']
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
            return '[%s] [%s]' % (parts[1].strip(), parts[2].strip())
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

def download_concept():
    base = 'http://conceptnet5.media.mit.edu/downloads/current/'
    html = urllib2.urlopen(base).read()
    local_dir = '/tmp'
    matches = re.findall('"(conceptnet5_csv_[^"]+)"', html)
    if matches:
        fn = matches[-1]
        local_fqfn = os.path.join(local_dir, fn)
        if os.path.isfile(local_fqfn):
            print('File %s already downloaded' % local_fqfn)
            return local_fqfn
        url = base + fn
        print('Downloading %s...' % url)
        os.system('wget --directory-prefix=/tmp %s' % url)
        return local_fqfn
    else:
        print(('No Conceptnet URL found! Perhaps the '
            'page %s has changed?') % base, file=sys.stderr)

@commit_on_success
def process(fn, part_name, domain_slug, commit_freq=10):
    print('%s: Processing...' % part_name)
    connection.close()
    domain = models.Domain.objects.get(slug=domain_slug)
    
    models.SET_QUESTION_INDEX = False
    models.SET_TARGET_INDEX = False
    
    fi, _ = models.FileImport.objects.get_or_create(
        domain=domain,
        filename=fn.split('/')[-1],
        part=part_name)
    
    if fi.total_lines is None:
        tar = tarfile.open(fn, 'r')
        fin = tar.extractfile(part_name)
        print('%s: Counting lines...' % part_name)
        total = fin.read().decode('utf8').count('\n')
        fi.current_line = 0
        fi.total_lines = total
        fi.save()
    elif fi.done:
        print('%s: Already complete.' % part_name)
        return
    else:
        total = fi.total_lines
    
    print('%s: %i lines found.' % (part_name, total))
    tar = tarfile.open(fn, 'r')
    fin = tar.extractfile(part_name)
    skip_to_line = fi.current_line or 0
    i = 0
    for line in fin:
        i += 1
        
        if skip_to_line and i < skip_to_line:
            continue
        
        if i == 1 or not i % commit_freq or i == total:
            print(
                '%s: Processing line %i of %i %.02f%%.' \
                    % (part_name, i, total, i/float(total or i)*100))
            sys.stdout.flush()
            fi.current_line = i
            fi.save()
            commit()
            reset_queries()
        
        line = line.decode('utf8')
        edge = ConceptNetEdge.from_string(line)
        
        # Ignore languages we don't care about.
        if domain.language:
            subject_lang = models.extract_language_code(edge.start)
            if subject_lang != domain.language:
                continue
            object_lang = models.extract_language_code(edge.end)
            if object_lang != domain.language:
                continue
        
        # Ignore edges without sense.
        # Note, this skips an estimated 85% of edges.
        start_sense = models.extract_sense(edge.start)
        if not start_sense:
            continue
        end_sense = models.extract_sense(edge.end)
        if not end_sense:
            continue
        
        retry = 0
        while 1:
            try:
                retry += 1
                
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
                    
                break
                
            except OperationalError as e:
                if 'deadlock' in str(e):
                    print('%s: Retry %i after deadlock.' % (part_name, retry))
                else:
                    raise
                    
    print('%s: Complete.' % part_name)

class Command(BaseCommand):
    help = 'Loads targets, questions and weights from a ConceptNet5 CSV dump file.'
    args = ''
    option_list = BaseCommand.option_list + (
        #make_option('--seed', default=None),
        make_option('--domain', default=''),
        make_option('--fn', default=''),
        make_option('--parts', default=20),
        make_option('--commit-freq', default=10),
        make_option('--part-name-template',
            default='assertions/part_%02i.csv'),
        )
    
    def handle(self, *args, **options):
        tmp_settings = settings.DEBUG
        settings.DEBUG = False
        try:
            
            commit_freq = int(options['commit_freq'])
            
            parts = int(options['parts'])
            
            part_name_template = options['part_name_template']
        
            fn = options['fn'].strip()
            if not fn or not os.path.isfile(fn):
                fn = download_concept()
            
            domain_slug = options['domain']
            domain = models.Domain.objects.get(slug=domain_slug)
            
            print('Launching processes...')
            connection.close()
            Parallel(n_jobs=cpu_count())(
                delayed(process)(
                    fn=fn,
                    part_name=part_name_template % i,
                    domain_slug=domain_slug,
                    commit_freq=commit_freq,
                )
                for i in range(parts))
            
#            models.SET_TARGET_INDEX = True
#            q = domain.targets.filter(index__isnull=True).order_by('id')
#            total = q.count()
#            i = 0
#            for r in q.iterator():
#                i += 1
#                if i == 1 or not i % 10 or i == total:
#                    print('Updating target index %i of %i.' % (i, total))
#                r.save()
#            
#            models.SET_QUESTION_INDEX = True
#            q = domain.questions.filter(index__isnull=True).order_by('id')
#            total = q.count()
#            i = 0
#            for r in q.iterator():
#                i += 1
#                if i == 1 or not i % 10 or i == total:
#                    print('Updating question index %i of %i.' % (i, total))
#                r.save()
            
        finally:
            settings.DEBUG = tmp_settings
            