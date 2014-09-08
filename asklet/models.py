from __future__ import print_function
import random
import re
import sys
import uuid
from collections import defaultdict

from django.db import models, connection
from django.db.transaction import commit, rollback, atomic
from django.db.models import Min, Max, Count, Sum, F, Q, Avg
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

#from picklefield.fields import PickledObjectField

import six
u = six.u
unicode = six.text_type
basestring = six.string_types

from conceptnet5.util.language_codes import CODE_TO_ENGLISH_NAME, SUPPORTED_LANGUAGE_CODES
LANGUAGE_CHOICES = sorted([
    (code, CODE_TO_ENGLISH_NAME[code])
    for code in SUPPORTED_LANGUAGE_CODES
], key=lambda o: o[1])

from admin_steroids.utils import DictCursor

from . import constants as c
from . import settings as _settings
from .backends.sql import SQLBackend

def get_backend_cls():
    name = settings.ASKLET_BACKEND
    if name == c.SQL:
        return SQLBackend
    else:
        raise NotImplementedError('Unknown backend: %s' % (name,))

def calculate_target_rank_item1(local_weight, answer_weight):
    #TODO:is this correct? section 0048 is ambiguous
    agreement = (local_weight < 0 and answer_weight < 0) or (local_weight > 0 and answer_weight > 0)
    diff = abs((answer_weight + local_weight)/2.)
    if agreement:
        return +diff
    else:
        return -diff

def calculate_target_rank_item2(local_weight, answer_weight):
    #TODO:is this correct? section 0048 is ambiguous
    them = local_weight
    us = answer_weight
    
    # Bias toward agreement on zero.
    #sign = (them*us+1)/abs(them*us+1)
    
    # Bias towards disagreement on zero.
    #sign = (them*us-1)/abs(them*us-1)
    #sign = (them*us-1+abs(them*us))/abs(them*us-1+abs(them*us))
    #sign = +1 if ((them < 0 and us < 0) or (them > 0 and us > 0)) else -1
    #sign = +1 if (them * us) > 0 else -1
    sign = ((them * us) > 0) * 2 - 1
    
    return sign*abs(them+us)/2.

def calculate_target_rank_item3(local_weight, answer_weight):
    return c.YES - abs(local_weight - answer_weight)

class Domain(models.Model):
    """
    A specific context used to organize separate groups
    of questions and targets.
    
    Also manages the learned model.
    """
    
    slug = models.SlugField(
        max_length=500,
        unique=True,
        blank=False,
        null=False)
    
    max_questions = models.PositiveIntegerField(
        default=20,
        help_text=_('''The maximum number of questions the system will
            be allowed to ask in a session.'''))
    
    top_n_guess = models.PositiveIntegerField(
        default=3,
        help_text=_('''If a target is the top-ranked choice for this many
            iterations, it will be used as a guess.'''))
    
    assumption = models.CharField(
        max_length=25,
        blank=False,
        null=False,
        db_index=True,
        choices=c.ASSUMPTION_CHOICES,
        default=c.CLOSED,
        #default=c.OPEN,
        help_text=_('''Defines what weight is used for missing
            target/question associations.
            If "open", the weight is assumed to be {open}.
            If "closed", the weight is assumed to be {closed}.'''\
            .format(open=c.OWA_WEIGHT, closed=c.CWA_WEIGHT)))
    
    language = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        choices=LANGUAGE_CHOICES,
        help_text=_('If specified, only edges in this language will be used.'))
    
    allow_inference = models.BooleanField(
        default=False,
        help_text=_('''If checked, and inference rule are specified,
            additional edges may be generated according to those rules.'''))
    
    max_inference_depth = models.PositiveIntegerField(
        default=5,
        help_text=_('''The maximum number of recursive inferences to make.'''))
    
    min_inference_probability = models.FloatField(
        default=0.5,
        help_text=_('''The minimum probability necessary to trigger
        an inference.'''))
        
    default_inference_count = models.IntegerField(
        default=1,
        help_text=_('''The default count used when creating an inferred weight.
            A low value allows the inference to be quickly overriden by user input.
            A high value makes the inference longer lived.'''))
    
    created = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        editable=False)
        
    def __unicode__(self):
        return self.slug
    
    def __str__(self):
        return '<Domain: %s>' % (self.slug,)
    
    @property
    def usable_targets(self):
        return self.targets.filter(enabled=True, sense__isnull=False)
    
    @property
    def usable_questions(self):
        return self.questions.filter(enabled=True, sense__isnull=False)
        
    def create_target(self, slug):
        t, _ = Target.objects.get_or_create(
            domain=self,
            slug=slug,
            conceptnet_subject=slug)
        return t
    
    def create_question(self, predicate, object):
        slug = predicate + ',' + object
        q, _ = Question.objects.get_or_create(
            domain=self,
            slug=slug,
            conceptnet_predicate=predicate,
            conceptnet_object=object)
        return q
    
    def create_weight(self, subject, predicate, object):
        t = self.create_target(subject)
        q = self.create_question(predicate, object)
        tq, _ = TargetQuestionWeight.objects.get_or_create(
            target=t, question=q)
        return tq
    
    @atomic
    def infer(self, limit=1000, continuous=True, target=None, verbose=False, iter_commit=True, rules=None):
        """
        Creates new weights based on all enabled inference rules.
        
        limit := The maximum number of weights to infer per batch.
        """
        if not self.allow_inference:
            return
        
        rule_ids = []
        rule_slugs = []
        if rules:
            if isinstance(rules, basestring):
                rules = [
                    int(_.strip()) if _.isdigit() else _.strip()
                    for _ in rules.split(',')
                    if _.strip()
                ]
                
            rule_ids = [_ for _ in rules if isinstance(_, int)]
                
            rule_slugs = [_ for _ in rules if isinstance(_, basestring)]
        
        rules = self.rules.filter(enabled=True)
        if rule_ids:
            rules = rules.filter(id__in=rule_ids)
        if rule_slugs:
            rules = rules.filter(name__in=rule_slugs)
        
        #print('rules:',rules)
        while 1:
            created = False
            for rule in rules.iterator():
                matches = rule.get_matches(limit=limit, target=target, verbose=verbose)
                for triple, parent_ids in matches:
                    assert len(triple), \
                        'Invalid triple, length %i.' % len(triple)
                    print('Infering:', triple)
                    weights = TargetQuestionWeight.objects\
                        .filter(id__in=parent_ids)
                    #weight,count,prob,inference_depth
                    aggs = weights.aggregate(
                        Max('inference_depth'),
                        Min('weight'),
                        #Min('prob'),
                        Min('count'))
                    probs = weights.values_list('prob', flat=True)
                    #print triple, parent_ids, weights
                    #print 'aggs:',aggs
                    target_slug = triple[0]
                    #question_slug = '%s,%s' % tuple(triple[1:])
                    w = self.create_weight(target_slug, triple[1], triple[2])
                    w.inference_depth = (aggs['inference_depth__max'] or 0) + 1
                    weight = max(aggs['weight__min'], 0)
                    count = max(aggs['count__min'], 1)
                    #prob = aggs['prob__min']
                    #print('probs:',probs)
                    
                    probs = [((_ - 0) / float(1 - 0))*(1.0 - -1.0) + -1.0 for _ in probs]
                    prob = reduce(lambda a,b:a*b, probs, 1.0)
                    prob = ((prob - -1.0) / float(+1.0 - -1.0))*(1.0 - 0.0) + 0
                    count = self.default_inference_count
                    weight = (prob*(c.YES - c.NO) - c.YES)*float(count)
                    
                    w.weight = weight
                    w.count = count
                    w.save()
                    
                    TargetQuestionWeightInference.objects.get_or_create(
                        rule=rule,
                        weight=w,
                        arguments=','.join(map(str, parent_ids)))
                    
                    created = True
            
            if iter_commit:
                commit()
            
            # Only stop inferring when we run out of matches.
            if not continuous or not created:
                break
    
    def infer_sl(self, continuous=False, limit=100, target=None, verbose=False, dryrun=False):
        """
        Infers using semantic-Lesk.
        """
        
        def guess_sense(ambiguous_subject, pos=None):
            try:
                if pos:
                    sql = """
    select unambiguous_subject, avg_prob
    from asklet_targetguess
    where ambiguous_subject = %s and pos = %s
    limit 1"""
                    cursor = connection.cursor()
                    cursor.execute(sql, [ambiguous_subject, pos])
                else:
                    sql = """
    select unambiguous_subject, avg_prob
    from asklet_targetguess
    where ambiguous_subject = %s
    limit 1"""
                    cursor = connection.cursor()
                    cursor.execute(sql, [ambiguous_subject])
                results = list(cursor)
                if results:
                    return results[0]
            except Exception as e:
                print(e)
                rollback()
        
        rule, _ = InferenceRule.objects.get_or_create(
            domain=self, name='SemanticLesk')
        rule.enabled = False
        rule.save()
        
        weights = TargetQuestionWeight.objects.pending_ambiguous()
        weights = weights.filter(target__domain=self)
        if target:
            weights = weights.filter(target__slug=target)
        
        agg = set(weights.values_list('target__slug', flat=True).distinct())
        total = len(agg)
        i = 0
        for target_slug in agg:
            
            target = None
            target_sense = guess_sense(target_slug)
            print('target:',target_slug, target_sense)
            if target_sense:
                target_sense, target_sense_prob = target_sense
                print('target prob:',target_sense_prob)
                target = Target.objects.get(domain=self, slug=target_sense)
                
            local_weights = weights.filter(target__slug=target_slug)
            for local_weight in local_weights.iterator():
                probs = [target_sense_prob]
                
                if not target:
                    local_weight.disambiguation_success = False
                    local_weight.save()
                    continue
                
                # Lookup unambiguous question.
                question = None
                if local_weight.question.sense:
                    question = local_weight.question
                else:
                    question_sense = guess_sense(
                        local_weight.question.conceptnet_object,
                        pos=target.pos)
                    if question_sense:
                        question_sense, question_sense_prob = question_sense
                        print('question prob:',question_sense_prob)
                        probs.append(question_sense_prob)
                        question, _ = Question.objects.get_or_create(
                            domain=self,
                            slug=local_weight.question.conceptnet_predicate+','+question_sense,
                            conceptnet_predicate=local_weight.question.conceptnet_predicate,
                            conceptnet_object=question_sense,
                        )
                        
                if question:
                    
                    probs = [((_ - 0) / float(1 - 0))*(1.0 - -1.0) + -1.0 for _ in probs]
                    prob = reduce(lambda a,b:a*b, probs, 1.0)
                    prob = ((prob - -1.0) / float(+1.0 - -1.0))*(1.0 - 0.0) + 0
                    count = self.default_inference_count
                    weight = (prob*(c.YES - c.NO) - c.YES)*float(count)
                    
                    print('Inferring:', target.slug, question.slug, prob)
                    weight, _ = TargetQuestionWeight.objects.get_or_create(
                        target=target,
                        question=question,
                        defaults=dict(
                            #weight=int(round(local_weight.weight*(weight_prob*2-1))),
                            #count=local_weight.count,
                            weight=weight,
                            count=count,
                            inference_depth=(local_weight.inference_depth or 0) + 1,
                        ),
                    )
                    TargetQuestionWeightInference.objects.get_or_create(
                        rule=rule,
                        weight=weight,
                        arguments=str(local_weight.id),
                    )
                    local_weight.disambiguated = timezone.now()
                    local_weight.disambiguation_success = True
                    local_weight.save()
                else:
                    #TODO:mark local_weight as inference attempted and failed
                    #so we won't retry?
                    local_weight.disambiguation_success = False
                    local_weight.save()
                    
            if not dryrun:
                commit()
    
    def purge(self, verbose=0):
        """
        Deletes all targets, questions and weights linked to the domain.
        """
        # Note, there may be millions of records, so if we tried to wrap this
        # in one single transaction, we might run out of memory and never
        # complete.
        commit_freq = 100
        queries = [
            self.sessions.all(),
            self.weights,
            self.targets.all(),
            self.questions.all(),
        ]
        i = total = 0
        for q in queries:
            total += q.count()
        for q in queries:
            for r in q.iterator():
                i += 1
                if i == 1 or not i % commit_freq or i == total:
                    if verbose:
                        sys.stdout.write('\rDeleting %i of %i %.02f%%.' \
                            % (i, total, i/float(total)*100))
                        sys.stdout.flush()
                    #commit()#TODO:enable once atomic bug fixed
                r.delete()
        if verbose:
            print('\nDone!')
    
    def accuracy_history(self, chunk=10):
        try:
            sessions = self.sessions.filter(winner__isnull=False)
            sessions = sessions.order_by('id')
            history = []
            correct = total = i = 0
            for session in sessions.iterator():
                i += 1
                correct += session.winner
                total += 1
                if (i % chunk)+1 == chunk:
                    history.append(correct/float(total))
                    correct = total = 0
            return history
        except Exception as e:
            return str(e)
    
    def get_session(self, user):
        try:
            return Session.objects.get(
                domain=self,
                user=user if isinstance(user, User) else None,
                user_uuid=str(user) if not isinstance(user, User) else None,
                winner=None,
            )
        except Session.DoesNotExist:
            return Session.objects.create(
                domain=self,
                user=user if isinstance(user, User) else None,
                user_uuid=str(user) if not isinstance(user, User) else None,
            )
    
    @property
    def connectivity(self):
        target_count = self.targets.all().count()
        question_count = self.questions.all().count()
        max_weight_count = target_count * question_count
        actual_weight_count = self.weights.all().count()
        if not max_weight_count:
            return
        ratio = actual_weight_count/float(max_weight_count)
        return ratio
    
    @property
    def weights(self):
        return TargetQuestionWeight.objects.filter(target__domain=self)
    
    @property
    def assumption_weight(self):
        """
        The value of missing weights according to the world-assumption.
        """
        if self.assumption == c.CLOSED:
            return c.CWA_WEIGHT
        elif self.assumption == c.OPEN:
            return c.OWA_WEIGHT
        else:
            raise Exception('Unknown world assumption: %s' % self.assumption)
    
    def get_weight(self, target, question, normalized=False):
        if isinstance(question, Question):
            weights = TargetQuestionWeight.objects.filter(
                target=target, question=question)
        elif isinstance(question, basestring):
            weights = TargetQuestionWeight.objects.filter(
                target=target, question__slug=question)
        if weights.exists():
            if normalized:
                return weights[0].normalized_weight
            else:
                return weights[0].weight
        return self.assumption_weight
    
class Session(models.Model):
    """
    Represents a single game of question and answering
    in which the system attempts to guess what the user is thinking.
    
    Also manages the temporary modifications of the domain model.
    """
    
    domain = models.ForeignKey(Domain, related_name='sessions')
    
    user = models.ForeignKey(
        User,
        related_name='sessions',
        on_delete=models.SET_NULL,
        blank=True,
        null=True)
    
    user_uuid = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text=_('''A universally unique ID assigned to the user incase they
            are anonymous and have not registered a user account.'''))
    
    winner = models.NullBooleanField(
        default=None,
        blank=True,
        null=True,
        db_index=True,
        help_text=_('''If true, indicates the system won.
            If false, indicates the user won.
            If none, indicates the session is ongoing or incomplete.'''))
    
    target = models.ForeignKey(
        'Target',
        related_name='sessions',
        blank=True,
        null=True,
        help_text=_('The user-confirmed target.'))
    
    merged = models.BooleanField(
        default=False,
        help_text=_('''If true, indicates this answer has been used as
            a training sample to alter the model.'''))
    
    created = models.DateTimeField(auto_now_add=True)
    
    def question_count(self):
        return self.answers.all().count()
    question_count.short_description = 'questions'
    
    @property
    def incorrect_targets(self):
        """
        Returns a queryset of targets that were guessed but were incorrect.
        """
        return Target.objects.filter(
            id__in=self.answers.filter(
                guess__isnull=False
            ).values_list('guess_id', flat=True))
    
    @property
    def previously_asked_questions(self):
        return self.answers.filter(question__isnull=False)
        
    @property
    def previously_asked_question_ids(self):
        return self.previously_asked_questions\
            .values_list('question_id', flat=True)
        
    @property
    def unguessed_targets(self):
        guessed_targets = self.answers\
            .filter(guess__isnull=False)\
            .values_list('guess_id', flat=True)
        return self.domain.usable_targets.exclude(id__in=guessed_targets)
    
    @property
    def minimum_question_count(self):
        """
        The minimum number of questions the system is allowed to ask.
        """
        unguessed_target_count = self.unguessed_targets.count()
        domain_question_count = self.domain.usable_questions.count()
        return min(unguessed_target_count, domain_question_count-2)
    
    def __unicode__(self):
        return u'user %s in domain %s' % (self.user or self.user_uuid, self.domain)
    
    def add_answer(self, question, answer):
        Answer.objects.create(
            session=self,
            question=question,
            answer=answer)
    
    @atomic
    def update_target_rankings(self, verbose=0):
        """
        Recalculates the target ranking records given the currently
        answered questions.
        """
        
        drop_threshold = -4#works!
        #drop_threshold = 0
        
        #=>1.0 old rank fixed
        #=>0.0 new rank overrides everything
        #=>0.5 old rank cut in half
        ranking_weight = 0.1
        ranking_weight_inv = 1-ranking_weight
        
        # Delete rankings of failed target guesses?
        incorrect_targets = self.incorrect_targets
        if incorrect_targets:
            expired_rankings = self.rankings.filter(target__in=incorrect_targets)
            if verbose:
                print('%i expired_rankings' % expired_rankings.count())
            expired_rankings.delete()
        exclude_target_ids = [0] + list(incorrect_targets.values_list('id', flat=True))
        exclude_target_id_str = ','.join(map(str, exclude_target_ids))
        
        # Incrementally update ranking one question at a time.
        unranked_answers = self.answers.filter(ranked=False, question__isnull=False)
        for unranked_answer in unranked_answers.iterator():
            manually_update = False
            first = self.answers.count() == 1
            if first:
                # Ensure all prior rankings for this session are deleted.
                self.rankings.all().delete()
                # For the first interation, insert the initial ranking records.
                sql = """
INSERT INTO asklet_ranking (session_id, target_id, ranking)
SELECT  a.session_id,
        t.id,
        SUM(4 - ABS(a.answer - COALESCE(tqw.nweight, {assumption_weight}))) AS ranking
FROM    asklet_target AS t
INNER JOIN asklet_answer AS a on
        a.session_id = {session_id}
    AND a.guess_id IS NULL
    AND a.question_id = {question_id}
INNER JOIN asklet_question AS q on
        q.id = a.question_id
LEFT OUTER JOIN asklet_targetquestionweight AS tqw ON
        tqw.question_id = a.question_id
    AND tqw.target_id = t.id
WHERE   t.domain_id = {domain_id}
    AND t.enabled = CAST(1 AS bool)
    AND t.sense IS NOT NULL
    AND t.id NOT IN ({exclude_target_ids})
GROUP BY a.session_id, t.id
HAVING SUM(4 - ABS(a.answer - COALESCE(tqw.nweight, {assumption_weight}))) > {drop_threshold};
                """.format(
                    session_id=self.id,
                    domain_id=self.domain.id,
                    question_id=unranked_answer.question.id,
                    assumption_weight=self.domain.assumption_weight,
                    exclude_target_ids=exclude_target_id_str,
                    drop_threshold=drop_threshold,
                )
            else:
                # For subsequent iterations, update the existing records.
                if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                    sql = """
SELECT  a.session_id,
        t.id AS target_id,
        SUM(4 - ABS(a.answer - COALESCE(tqw.nweight, {assumption_weight}))) AS ranking
FROM    asklet_target AS t
INNER JOIN asklet_answer AS a on
        a.session_id = {session_id}
    AND a.guess_id IS NULL
    AND a.question_id = {question_id}
INNER JOIN asklet_question AS q on
        q.id = a.question_id
LEFT OUTER JOIN asklet_targetquestionweight AS tqw ON
        tqw.question_id = a.question_id
    AND tqw.target_id = t.id
WHERE   t.domain_id = {domain_id}
    AND t.enabled = CAST(1 AS bool)
    AND t.sense IS NOT NULL
GROUP BY a.session_id, t.id
                    """.format(
                        session_id=self.id,
                        domain_id=self.domain.id,
                        question_id=unranked_answer.question.id,
                        assumption_weight=self.domain.assumption_weight,
                    )
                    manually_update = True
                else:
                    sql = """
UPDATE asklet_ranking AS r
SET ranking = r.ranking*{ranking_weight} + s.ranking*{ranking_weight_inv}
FROM (
    SELECT  a.session_id,
            t.target_id,
            SUM(4 - ABS(a.answer - COALESCE(tqw.nweight, {assumption_weight}))) AS ranking
    FROM    asklet_ranking AS t
    INNER JOIN asklet_answer AS a on
            a.session_id = {session_id}
        AND a.guess_id IS NULL
        AND a.question_id = {question_id}
    INNER JOIN asklet_question AS q on
            q.id = a.question_id
    LEFT OUTER JOIN asklet_targetquestionweight AS tqw ON
            tqw.question_id = a.question_id
        AND tqw.target_id = t.target_id
    GROUP BY a.session_id, t.target_id
) AS s
WHERE   r.target_id = s.target_id
    AND r.session_id = s.session_id;
                    """.format(
                        session_id=self.id,
                        domain_id=self.domain.id,
                        question_id=unranked_answer.question.id,
                        assumption_weight=self.domain.assumption_weight,
                        ranking_weight=ranking_weight,
                        ranking_weight_inv=ranking_weight_inv,
                    )
            if verbose:
                print('~'*80)
                print('update_target_rankings sql:\n',sql)
                #raw_input('enter')#TODO:remove
            cursor = connection.cursor()
            cursor.execute(sql)
            
            # Only necessary for Sqlite3 used during unittesting...
            if manually_update:
                for session_id, target_id, ranking in cursor:
                    #print(session_id, target_id, ranking)
                    r, _ = Ranking.objects.get_or_create(
                        session_id=session_id,
                        target_id=target_id,
                        defaults=dict(ranking=0))
                    old_ranking = r.ranking
                    #r.ranking += ranking
                    r.ranking = r.ranking*ranking_weight + ranking*ranking_weight_inv
                    r.save()
                    if verbose:
                        print('sqlite3.ranking.updated %s: %s->%s' % (r.target, old_ranking, r.ranking))
            
            # Mark answer as ranked.
            unranked_answer.ranked = True
            unranked_answer.save()
            
            # Delete the lowest N rankings to speed up the eventual
            # question-ranking.
            #TODO:paramaterize count and ratio threshold?
            # lower, the longer the search takes but more certain
            # higher, the faster the search but more likely to error
            if 1:#rankings_count > 3:#10:
                #rankings_count = self.rankings.all().count()
                #low_rankings = self.rankings.all().order_by('-ranking')[int(rankings_count*0.75):]
                #Ranking.objects.filter(id__in=low_rankings.values_list('id', flat=True))
                low_rankings = self.rankings.filter(ranking__lt=drop_threshold)
#                low_rankings_count = low_rankings.count()
#                if low_rankings_count:
#                    print('deleting %i low rankings' % low_rankings_count)
                low_rankings.delete()
            
            if verbose:
                print('final rankings:',self.rankings.all().count())
            
            #commit()#unnecessary with atomic()
    
    def _query_questionrankings(self, exclude_question_ids=[], verbose=0):
        """
        Uses SQL to finds the next best question given current answers.
        """
        
        usable_targets = self.domain.usable_targets.only('id')
        
        session = self
        session_id = self.id
        ranking_str = ''
        
        #TODO:fix? actually slows down the query?
        if self.rankings.all().exists():
            # Restrict question analysis to those linked to actively ranked targets.
            # Note, we only add this condition if there is at least one ranking.
            # Otherwise, we won't get any questions for the first iteration.
            #ranking_str = 'AND r.id IS NOT NULL'
            ranking_str = '''AND tqw.target_id IN (
    SELECT target_id
    FROM asklet_ranking
    WHERE session_id = {session_id}
)'''.format(session_id=session_id)
            usable_targets = usable_targets.filter(
                rankings__session=self)

#    LEFT OUTER JOIN
#            asklet_ranking AS r ON
#            r.session_id = {session_id}
#        AND r.target_id = tqw.target_id

        total_target_count = usable_targets.count()
        
        exclude_question_ids_str = ''
        if exclude_question_ids:
            exclude_question_ids_str = 'AND q.id NOT IN (' + (','.join(map(str, exclude_question_ids))) + ')'
        
#        print('%i enabled questions' % self.questions.filter(enabled=True).count())
#        print('%i question weights' % TargetQuestionWeight.objects.filter(question__domain=self).count())
        
        # We add the tangible weight sum to the implied sum of missing weights.
        # e.g. If we have 1000 targets but only 100 have weights for
        # a question, then 900 have an implicit weight as defined by
        # the domain's world assumption.
        cursor = connection.cursor()
        sql = """
SELECT  m.*
        --,-((m.up_count/m.target_count)*log(m.up_count/m.target_count) + (m.down_count/m.target_count)*log(m.down_count/m.target_count)) AS entropy
FROM (
SELECT  m.question_id,--m.slug,
        ABS(m.weight_sum + (({total_target_count} - m.target_count)*{missing_weight})) AS weight_sum_abs,
        --m.up_count,
        --m.down_count + case when {missing_weight} < 0 then {total_target_count}-m.up_count else 0 end AS down_count,
        m.weight_sum,
        m.target_count
FROM (
    -- Aggregate question_id -> sum(nweight)
    SELECT  q.id AS question_id,q.slug,
            SUM(COALESCE(a.answer, tqw.nweight)) AS weight_sum,
            SUM(CASE WHEN COALESCE(a.answer, tqw.nweight, -4) > 0  THEN 1 ELSE 0 END) AS up_count,
            SUM(CASE WHEN COALESCE(a.answer, tqw.nweight, -4) <= 0 THEN 1 ELSE 0 END) AS down_count,
            COUNT(DISTINCT tqw.target_id) AS target_count
    FROM    asklet_question AS q
    LEFT OUTER JOIN
            asklet_targetquestionweight AS tqw ON
            tqw.question_id = q.id
        AND tqw.weight IS NOT NULL
    LEFT OUTER JOIN
            asklet_answer AS a ON
            a.session_id = {session_id}
        AND a.question_id = tqw.question_id
    WHERE   q.enabled = CAST(1 AS bool)
        AND q.sense IS NOT NULL
        AND q.domain_id = {domain_id}
        {exclude_question_ids_str}
        {ranking_str}
    GROUP BY q.id
) AS m
) AS m
WHERE m.weight_sum IS NOT NULL
ORDER BY weight_sum_abs ASC
--ORDER BY entropy DESC
LIMIT 1;
        """.format(
            domain_id=self.domain.id,
            session_id=session_id,
            total_target_count=total_target_count,
            missing_weight=self.domain.assumption_weight,
            exclude_question_ids_str=exclude_question_ids_str,
            ranking_str=ranking_str,
#            sub_sql=sub_sql,
        )
        if verbose: print('question sql:',sql)
        cursor.execute(sql)
        results = []
        for question_id, weight_sum_abs, weight_sum, target_count in cursor:
#            print('row:',question_id, weight_sum_abs, weight_sum, target_count, total_count)
            results.append((question_id, weight_sum_abs))
        return results
    
    def rank_questions_sql(self, verbose=True):
        results = self._query_questionrankings(
            exclude_question_ids=self.previously_asked_question_ids,
            verbose=verbose)
        question_rankings = defaultdict(int) # {question:rank}
#        print('results:',results)
        for question_id, rank in results:
            question = Question.objects.get(id=question_id)
            question_rankings[question] = rank

        #TODO:rank questions by finding the one with the most even YES/NO split, explained in 0053
        # Lower rank means better splitting criteria.
        question_rankings = sorted(question_rankings.items(), key=lambda o: abs(o[1]))
        return question_rankings

    def rank_questions(self, *args, **kwargs):
        ranker = settings.ASKLET_RANKER.lower()
        return getattr(self, 'rank_questions_%s' % ranker)(*args, **kwargs)

    def get_next_question(self, verbose=0):
        """
        Returns the next best question to ask.
        """
        if not self.winner is None:
            return
        
        self.update_target_rankings(verbose=verbose)
        
        answers = self.answers.all()
        prior_failed_target_ids = set(self.incorrect_targets.values_list('id', flat=True))
        if verbose:
            print()
            print('%i rankings' % self.rankings.all().count())
            print('%i answers provided' % answers.count())
            print('prior failed guesses:',prior_failed_target_ids)
        
        if verbose:
            #print('prior_top_target_ids:',len(prior_top_target_ids))
            print('Prior answers:')
            for answer in answers:
                if answer.question:
                    print(answer.question.slug, answer.answer)
                else:
                    print(answer.guess.slug, answer.answer)
            print('')
        
        if verbose:
#            print('trunc:',trunc)
#            print('%i top targets A' % len(top_targets))
            print('%i total targets' % self.domain.targets.all().count())
            print('%i total enabled targets' % self.domain.usable_targets.count())
            print('%i total questions' % self.domain.questions.all().count())
            print('%i total enabled questions' % self.domain.usable_questions.count())
            print('%i failed targets' % len(prior_failed_target_ids))
        
        # Create and maintain a cached list of the last N top targets.
        #TODO:convert this to a model field?
        if not hasattr(self, '_cached_last_top_targets'):
            self._cached_last_top_targets = []
        last_top_targets = self._cached_last_top_targets
        
        last_top_targets_n = self.domain.top_n_guess
        
        unguessed_targets = self.unguessed_targets
        if verbose:
            print('unguessed_targets:',unguessed_targets.count())
        unguessed_rankings = self.rankings.exclude(target__id__in=prior_failed_target_ids).order_by('-ranking')
        
        if unguessed_rankings:
            last_top_targets.append(unguessed_rankings[0].target)
        
        # Check for cases where we want to guess the target instead
        # of asking a question.
        if last_top_targets_n and len(last_top_targets) >= last_top_targets_n \
        and len(set(last_top_targets[-last_top_targets_n:])) == 1:
            # If the last N top targets are all the same, then guess that
            # target.
            top_target = last_top_targets[-1]
            # Clear the cached list, so if we're wrong, we won't re-recommend
            # the same target.
            self._cached_last_top_targets = []
#            self.clear_top_targets_cache()
            if verbose: print('top_target case 1:',top_target)
            return top_target
        elif not unguessed_targets:
            # If we've exhausted all targets, which should only happen
            # for trivially small domains, then give up.
            if verbose: print('top_target case 2:')
            return
        elif len(unguessed_rankings) == 1:
            # If there's only one target left, then forego futher questions
            # and just guess that target.
#            self.clear_top_targets_cache()
            top_target = unguessed_rankings[0].target
            if verbose: print('top_target case 3:',top_target)
            return top_target
        elif len(unguessed_targets) == 1:
            # If there's only one target left, then forego futher questions
            # and just guess that target.
#            self.clear_top_targets_cache()
            top_target = unguessed_targets[0]
            if verbose: print('top_target case 3b:',top_target)
            return top_target
        elif unguessed_rankings and answers.count()+1 == self.domain.max_questions:
            # We only have one more question left, so make our best guess.
#            self.clear_top_targets_cache()
            top_target = unguessed_rankings[0].target
            if verbose: print('top_target case 4:',top_target)
            return top_target
        
#        if top_targets:
#            self.save_top_targets_cache(list(target.id for target,rank in top_targets))
        
        # Second mode.
        #print('previous_question_ids:',previous_question_ids)
        previous_question_ids = self.previously_asked_question_ids
        question_rankings = self.rank_questions(
            verbose=verbose)
        if verbose: print('%i question rankings' % len(question_rankings))
        if question_rankings:
            #print('best')
            best_question, best_rank = question_rankings[0]
            return best_question
        else:
            #print('random:',previous_question_ids)
            questions = Question.objects.askable(self.domain.questions.all())
            if previous_question_ids:
                questions = questions.exclude(id__in=previous_question_ids)
            if questions.exists():
                # Otherwise just pick a question at random.
                #print('questions:',questions)
                rand_q = questions.order_by('?')[0]
                #print('randomly selected:',rand_q)
                return rand_q

    def record_result(self, guess, actual, merge=False, attrs=[], verbose=0):
        """
        Records the final result of the session, who won, what the correct
        target was, and any additional descriptors the user gave us.
        """
        
        # Add additional user descriptions of target, which may or may
        # not yet exist in the system.
        for attr, belief in attrs:
            if verbose: print('User: %s %s' % (attr, belief))
            question, _ = Question.objects.get_or_create(
                domain=self.domain,
                slug=attr)
            if merge:
                question.enabled = True
                question.save()
            Answer.objects.get_or_create(
                session=self,
                question=question,
                defaults=dict(answer=belief))
        
        # Lookup the correct answer target.
        if isinstance(actual, Target):
            target = actual
            actual_slug = target.slug
        else:
            target, _ = Target.objects.get_or_create(
                domain=self.domain,
                slug=actual)
            if merge:
                target.enabled = True
                target.save()
            actual_slug = actual
        
        # Lookup our guess.
        guess_slug = None
        if guess:
            if isinstance(guess, Target):
                guess_slug = guess.slug
            else:
                guess, _ = Target.objects.get_or_create(
                    domain=self.domain,
                    slug=guess,
                    defaults=dict(enabled=True))
                guess_slug = guess
        
        # Determine winner.
        self.winner = guess_slug == actual_slug
        self.target = target
        if merge:
            self.merge(verbose=verbose)
        
        self.save()
        
    @atomic
    def merge(self, verbose=0):
        """
        Adds the weight of all answers into the domain's master weight matrix.
        """
        if self.merged or not self.target:
            return
    
        for answer in self.answers.all():
            if verbose: print('merging answer:',answer)
            if answer.question:
                tq, _ = TargetQuestionWeight.objects.get_or_create(
                    target=self.target,
                    question=answer.question,
                )
                tq.weight += answer.answer
                tq.count += 1
                tq.save()
            elif answer.guess:
                #TODO:update weights for targets of failed guesses?
                # Probably shouldn't, because we can't assume the answers
                # strictly apply to our failed guess. They could very well apply,
                # but the user simply wasn't thinking it.
                # e.g. if the user thought "grass" and we guessed "tree" and
                # previously asked them "is it green?", we can't assume they
                # meant that either grass or trees aren't green.
                pass
            else:
                raise Exception('No question but no guess?')
            
        self.merged = True
        
#        commit()

class Ranking(models.Model):
    """
    Caches target rankings for each session.
    """
    
    session = models.ForeignKey('Session', related_name='rankings')
    
    target = models.ForeignKey('Target', related_name='rankings')
    
    ranking = models.FloatField(db_index=True)
    
    class Meta:
        unique_together = (
            ('session', 'target'),
        )
        ordering = (
            '-ranking',
        )

SET_TARGET_INDEX = True

def extract_language_code(s):
    s = (s or '').strip()
    if not s:
        return
    parts = s.strip().split('/')
    if len(parts) < 4:
        return
    elif len(parts[2]) != 2:
        return
    return parts[2]

def extract_pos(s):
    s = (s or '').strip()
    if not s:
        return
    parts = s.strip().split('/')
    if len(parts) < 5:
        return
    elif len(parts[4]) < 1:
        return
    return parts[4]

def extract_sense(s):
    s = (s or '').strip()
    if not s:
        return
    parts = s.strip().split('/')
    if len(parts) < 6:
        return
    elif not len(parts[5]):
        return
    return parts[5]

def extract_word(s):
    s = (s or '').strip()
    if not s:
        return
    parts = s.strip().split('/')
    if len(parts) < 4:
        return
    return parts[3]

class Target(models.Model):
    """
    Things to guess.
    """
    
    domain = models.ForeignKey(Domain, related_name='targets')
    
    slug = models.CharField(
        max_length=500,
        blank=False,
        null=False,
        db_index=True)
        
    slug_parts = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        editable=False)
    
    text = models.TextField(
        blank=True,
        null=True,
        help_text=_('A user-friendly presentation of the question.'))
        
    index = models.PositiveIntegerField(
        default=None,
        editable=False,
        blank=True,
        null=True,
        db_index=True)

    conceptnet_subject = models.CharField(
        max_length=500,
        db_index=True,
        blank=True,
        null=True,
        help_text=_('The URI of the subject in ConceptNet5.'))
    
    language = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        db_index=True,
        editable=False)

    word = models.CharField(
        max_length=500,
        db_index=True,
        blank=True,
        null=True,
        help_text=_('''The word segment of the ConceptNet5 URI.
            e.g. "cat" given "/c/en/cat"'''))
    
    pos = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        db_index=True,
        editable=False)
    
    sense = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_index=True,
        editable=False)
        
    enabled = models.BooleanField(
        default=False,
        db_index=True)
        
    created = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        editable=False)

    total_weights = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        editable=False,
        help_text=_('''Cached count of the total weights linked to this
            target from the subject.'''),
    )
    
    total_weights_aq = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        editable=False,
        verbose_name=_('total weights (ambiguous)'),
        help_text=_('''Cached count of the total weights linked to this
            target from the subject with an ambiguous question.'''),
    )
    
    total_weights_uaq = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        editable=False,
        verbose_name=_('total weights (unambiguous)'),
        help_text=_('''Cached count of the total weights linked to this
            target from the subject with an un-ambiguous question.'''),
    )
    
    total_senses = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        editable=False,
        verbose_name=_('total senses'),
        help_text=_('''If ambiguous, cached count of the total umambiguous
            versions.'''),
    )
    
#    stats_last_updated = models.DateTimeField(
#        blank=True,
#        null=True,
#        editable=False,
#        help_text=_('The last time of weight counts were updated.'))

    class Meta:
        unique_together = (
            ('domain', 'slug'),
#            ('domain', 'index'),
            ('domain', 'conceptnet_subject'),
        )
    
    def __unicode__(self):
        return self.slug
    
    def __str__(self):
        return self.slug
    
    def language_name(self):
        if not self.language:
            return
        return CODE_TO_ENGLISH_NAME[self.language]
    language_name.short_description = 'language'
    
    @property
    def total_prob(self):
        aggs = self.weights.all().aggregate(Avg('prob'))
        return aggs['prob__avg']
    
    def get_all_extended_glosses(self):
        try:
            if not self.sense:
                return
            q = TargetQuestionWeight.objects.filter(
                target=self)
            return ' '.join([self.sense.replace('_', ' ')] + [
                _.question.sense.replace('_', ' ') if _.question.sense else _.question.word.replace('_', ' ')
                for _ in q.iterator()
            ])
        except Exception as e:
            return str(e)
    get_all_extended_glosses.short_description = _('extended glosses')

    def save(self, set_index=True, *args, **kwargs):
        if not self.id and set_index and SET_TARGET_INDEX:
            self.index = self.domain.targets.all().only('id').count()
            
        if not self.conceptnet_subject and '/' in self.slug:
            self.conceptnet_subject = self.slug
            
        if not self.language:
            self.language = extract_language_code(self.conceptnet_subject)
            
        if not self.pos:
            self.pos = extract_pos(self.conceptnet_subject)
            
        if not self.sense:
            self.sense = extract_sense(self.conceptnet_subject)
            
        if not self.word:
            self.word = extract_word(self.conceptnet_subject)
            
        if self.slug_parts is None:
            self.slug_parts = self.slug.count('/')
        
        if self.total_weights is None:
            self.total_weights = self.weights.all().count()
        
        if self.total_weights_uaq is None:
            self.total_weights_uaq  = self.weights.filter(question__sense__isnull=False).count()
        
        if self.total_weights_aq is None:
            self.total_weights_aq  = self.weights.filter(question__sense__isnull=True).count()
        
        if not self.sense and self.total_senses is None:
            q = Target.objects.filter(
                language=self.language,
                word=self.word,
                sense__isnull=False)
            if self.pos:
                q = q.filter(pos=self.pos)
            self.total_senses = q.count()
        
        super(Target, self).save(*args, **kwargs)

class TargetMissing(models.Model):
    """
    Returns all target slugs that have no target record defined.
    """
    
    slug = models.CharField(
        max_length=500,
        blank=False,
        null=False,
        editable=False,
        db_column='target_slug',
        primary_key=True)
    
    domain = models.ForeignKey(
        Domain,
        related_name='missing_targets',
        editable=False,
        db_column='domain_id')
    
    language = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        editable=False)
    
    pos = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        editable=False)
    
    sense = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_index=True,
        editable=False)
        
    _text = models.TextField(
        blank=True,
        null=True,
        editable=False,
        db_column='text',
        help_text=_('A user-friendly presentation of the question.'))
        
    class Meta:
        managed = False
        verbose_name = _('missing target')
        verbose_name_plural = _('missing targets')
    
    @property
    def text(self):
        matches = re.findall(r'\[[^\]]+\][^\]]*\[([^\]]+)\]', self._text or '')
        if matches:
            return matches[0]
    
    def materialize(self):
        target, _ = Target.objects.get_or_create(
            domain=self.domain,
            slug=self.slug,
            defaults=dict(
                conceptnet_subject=self.slug,
                text=self.text,
                enabled=True
            )
        )
        return target
    
#    def save(self, *args, **kwargs):
#        super(TargetMissing, self).save(*args, **kwargs)

class QuestionManager(models.Manager):
    
    def askable(self, q=None):
        if q is None:
            q = self
        return q.filter(enabled=True)

SET_QUESTION_INDEX = True

class Question(models.Model):
    """
    An arbitrary query to be proposed to the user.
    """
    
    objects = QuestionManager()
    
    domain = models.ForeignKey(Domain, related_name='questions')
    
    slug = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_index=True)
    
    slug_parts = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        editable=False)
        
    text = models.TextField(
        blank=True,
        null=True,
        help_text=_('A user-friendly presentation of the question.'))
    
    index = models.PositiveIntegerField(
        default=None,
        editable=False,
        blank=True,
        null=True,
        db_index=True)
    
    conceptnet_predicate = models.CharField(
        max_length=500,
        db_index=True,
        blank=True,
        null=True,
        verbose_name=_('predicate'),
        help_text=_('The URI of the predicate.'))
    
    conceptnet_object = models.CharField(
        max_length=500,
        db_index=True,
        blank=True,
        null=True,
        verbose_name=_('object'),
        help_text=_('The URI of the object.'))
    
    language = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        db_index=True,
        editable=False)

    word = models.CharField(
        max_length=500,
        db_index=True,
        blank=True,
        null=True,
        help_text=_('''The word segment of the ConceptNet5 URI.
            e.g. "cat" given "/c/en/cat"'''))
    
    pos = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        db_index=True,
        editable=False)
    
    sense = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_index=True,
        editable=False)
        
    enabled = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_('''If checked, this question might be asked of the user.
            Otherwise, it will not be asked.'''))
            
    created = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        editable=False)

    total_weights = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        editable=False,
        help_text=_('''Cached count of the total weights linked to this
            question.'''),
    )
    
    total_weights_aq = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        editable=False,
        verbose_name=_('total weights (ambiguous)'),
        help_text=_('''Cached count of the total weights linked to this
            question with an ambiguous target.'''),
    )
    
    total_weights_uaq = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        editable=False,
        verbose_name=_('total weights (unambiguous)'),
        help_text=_('''Cached count of the total weights linked to this
            question with an un-ambiguous question.'''),
    )
    
    class Meta:
        unique_together = (
            ('domain', 'slug'),
            ('domain', 'index'),
            ('domain', 'conceptnet_predicate', 'conceptnet_object'),
        )
    
    def __unicode__(self):
        if not self.slug and self.text:
            return self.conceptnet_predicate + ' ' + self.text[:50].strip() + '...'
        return self.slug or str(self.id)
    
    def __str__(self):
        if not self.slug and self.text:
            return self.conceptnet_predicate + ' ' + self.text[:50].strip() + '...'
        return self.slug or str(self.id)
        
    def language_name(self):
        if not self.language:
            return
        return CODE_TO_ENGLISH_NAME[self.language]
    language_name.short_description = 'language'
    
    def save(self, set_index=True, *args, **kwargs):
        
        if not self.id and set_index and SET_QUESTION_INDEX:
            self.index = self.domain.questions.all().only('id').count()
        
        if self.slug and '/' in self.slug and ',' in self.slug:
            if not self.conceptnet_predicate:
                self.conceptnet_predicate = self.slug.split(',')[0]
            if not self.conceptnet_object:
                self.conceptnet_object = ','.join(self.slug.split(',')[1:])
        
        if not self.language:
            self.language = extract_language_code(self.conceptnet_object)
            
        if not self.pos:
            self.pos = extract_pos(self.conceptnet_object)
            
        if not self.sense:
            self.sense = extract_sense(self.conceptnet_object)
        
        if not self.word:
            self.word = extract_word(self.conceptnet_object)
            
        if self.slug and self.slug_parts is None:
            self.slug_parts = self.slug.count('/')
        
        if self.total_weights is None:
            self.total_weights = self.weights.all().count()
        
        if self.total_weights_uaq is None:
            self.total_weights_uaq  = self.weights.filter(target__sense__isnull=False).count()
        
        if self.total_weights_aq is None:
            self.total_weights_aq  = self.weights.filter(target__sense__isnull=True).count()
        
        super(Question, self).save(*args, **kwargs)

class InferenceRule(models.Model):
    
    domain = models.ForeignKey('Domain', related_name='rules')
    
    name = models.CharField(
        max_length=100,
        blank=False,
        null=False)
        
    lhs = models.TextField(
        blank=False,
        null=False)
        
    rhs = models.TextField(
        blank=False,
        null=False)
    
    enabled = models.BooleanField(
        default=True,
        db_index=True)
    
    created = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        editable=False)
        
    class Meta:
        unique_together = (
            ('domain', 'name'),
        )
        
    def __unicode__(self):
        return self.name
    
    def sql(self, limit=0, target=None, verbose=False):
        """
        Generates the SQL for finding matches.
        """
        selects = []
        joins = ['FROM asklet_domain AS d']
        wheres = ['d.id = %i' % self.domain.id]
        groupbys = []
        havings = []
        lhs_parts = [_.strip() for _ in self.lhs.strip().split('\n') if _.strip()]
        assert lhs_parts, 'No LHS defined.'
        rhs_parts = [_.strip() for _ in self.rhs.strip().split('\n') if _.strip()]
        assert rhs_parts, 'No RHS defined.'
        
#        var_to_field = {}
#        field_to_field = {}
#        field_to_literal = {}
        field_to_literals = defaultdict(set)
        variable_to_values = defaultdict(set)
        
        def is_literal(s):
            return not s.startswith('?')
        
        def is_variable(s):
            return s.startswith('?')
            
        i = 0
        for part in lhs_parts:
            i += 1
            part = re.sub(r'[\s\t\n]+', ' ', part)
            subject, predicate, object = part.split(' ')
            #print subject, predicate, object
            
            selects.append('lw{i}.id AS _lw{i}_id'.format(i=i))
            groupbys.append('lw{i}.id'.format(i=i))
            
            joins.append('''
INNER JOIN asklet_target AS lt{i} ON lt{i}.domain_id = d.id
INNER JOIN asklet_targetquestionweight AS lw{i} ON lw{i}.target_id = lt{i}.id
INNER JOIN asklet_question AS lq{i} ON lq{i}.id = lw{i}.question_id
    AND lq{i}.conceptnet_object != lt{i}.conceptnet_subject
            '''.strip().format(i=i))
            wheres.append('lt{i}.sense IS NOT NULL'.format(i=i))
            
            if target and i == 1:
                wheres.append("lt{i}.slug = '{target}'".format(i=i, target=target))
            
            if self.domain.min_inference_probability:
                wheres.append('lw{i}.prob >= {min_prob}'.format(
                    i=i, min_prob=self.domain.min_inference_probability))
            
            if self.domain.max_inference_depth:
                wheres.append(
                    ('(lw{i}.inference_depth IS NULL OR '
                    'lw{i}.inference_depth <= {max_depth})').format(
                        i=i, max_depth=self.domain.max_inference_depth))
                    
            subject_field = 'lt{i}.conceptnet_subject'.format(i=i)
            predicate_field = 'lq{i}.conceptnet_predicate'.format(i=i)
            object_field = 'lq{i}.conceptnet_object'.format(i=i)
            
            if is_variable(subject):
                variable_to_values[subject].add(subject_field)
            else:
                field_to_literals[subject_field].add(subject)
                joins.append("    AND %s = '%s'" % (subject_field, subject))
                
            if is_variable(predicate):
                variable_to_values[predicate].add(predicate_field)
            else:
                field_to_literals[predicate_field].add(predicate)
                joins.append("    AND %s = '%s'" % (predicate_field, predicate))
            
            if is_variable(object):
                variable_to_values[object].add(object_field)
            else:
                field_to_literals[object_field].add(object)
                joins.append("    AND %s = '%s'" % (object_field, object))
                
        for variable, values in variable_to_values.iteritems():
            if len(values) <= 1:
                continue
            values = list(values)
            last = values[0]
            last_pos = None
            #TODO:make pos-link customizable by rule?
            #e.g. IsA requires match, but others might not?
            if '.conceptnet_' in last:
                last_pos = last.split('.')[0] + '.pos'
            for value in values[1:]:
                joins.append("    AND %s = %s" % (last, value))
                if last_pos and '.conceptnet_' in value:
                    value_pos = value.split('.')[0] + '.pos'
                    joins.append("    AND %s = %s" % (last_pos, value_pos))
                last = value
        
        j = 0
        for part in rhs_parts:
            j += 1
            part = re.sub(r'[\s\t\n]+', ' ', part)
            subject, predicate, object = part.split(' ')
            #print subject, predicate, object
            
            subject_field = 'rt{j}.conceptnet_subject'.format(j=j)
            predicate_field = 'rq{j}.conceptnet_predicate'.format(j=j)
            object_field = 'rq{j}.conceptnet_object'.format(j=j)
            
            joins.append('''
LEFT OUTER JOIN asklet_target AS rt{j} ON rt{j}.domain_id = d.id
            '''.strip().format(j=j))
            
            if is_variable(subject):
                other_field = list(variable_to_values[subject])[0]
                joins.append("    AND %s = %s" % (subject_field, other_field))
                selects.append(list(variable_to_values[subject])[0] + ' AS ' + subject[1:])
                #groupbys.append(list(variable_to_values[subject])[0])
            else:
                joins.append("    AND %s = '%s'" % (subject_field, subject))
            
            joins.append('''
LEFT OUTER JOIN asklet_question AS rq{j} ON rq{j}.domain_id = d.id
            '''.strip().format(j=j))
            
            if is_variable(predicate):
                other_field = list(variable_to_values[predicate])[0]
                joins.append("    AND %s = %s" % (predicate_field, other_field))
                selects.append(list(variable_to_values[predicate])[0] + ' AS ' + predicate[1:])
                #groupbys.append(list(variable_to_values[predicate])[0])
            else:
                joins.append("    AND %s = '%s'" % (predicate_field, predicate))
                
            if is_variable(object):
                other_field = list(variable_to_values[object])[0]
                joins.append("    AND %s = %s" % (object_field, other_field))
                selects.append(list(variable_to_values[object])[0] + ' AS ' + object[1:])
                #groupbys.append(list(variable_to_values[object])[0])
            else:
                joins.append("    AND %s = '%s'" % (object_field, object))
                
            joins.append('''
LEFT OUTER JOIN asklet_targetquestionweight AS rw{j} ON rw{j}.target_id = rt{j}.id AND rw{j}.question_id = rq{j}.id
            '''.strip().format(j=j))
                
            wheres.append('rw{j}.id IS NULL'.format(j=j))
            #havings.append('MAX(rq{j}.id) IS NULL'.format(j=j))

        parts = ['SELECT ' + (', '.join(selects))] + joins \
            + ['WHERE ' + (' AND '.join(wheres))]#\
#            + ['GROUP BY ' + (', '.join(groupbys))] \
#            + ['HAVING ' + (', '.join(havings))]
        sql = '\n'.join(parts)
        if limit:
            sql += '\nLIMIT %i' % limit
        #min_inference_probability
        #max_inference_depth
        if verbose:
            print(sql)
        return sql
    
    def get_matches(self, limit=100, target=None, verbose=False):
        sql = self.sql(limit=limit, target=target, verbose=verbose)
        #print sql
        cursor = DictCursor()
        cursor.execute(sql)
        rhs_parts = [_.strip() for _ in self.rhs.split('\n') if _.strip()]
        matches = []
        for var_values in cursor:
            #print 'var_values:',var_values
            parent_ids = [
                var_values[_k]
                for _k in sorted(var_values.keys())
                if _k.startswith('_lw') and _k.endswith('_id')
            ]
            for rhs_part in rhs_parts:
                rhs_part = re.sub('[\s\t\n]+', ' ', rhs_part)
                rhs_part = [
                    ('{'+_[1:]+'}').format(**var_values)
                    if _.startswith('?')
                    else _
                    for _ in rhs_part.split(' ')]
                matches.append((rhs_part, parent_ids))
        return matches

class TargetQuestionWeightInference(models.Model):
    """
    Documents a rule's inference of a weight.
    Note that multiple rules and argument combinations can potentially result
    in the same weight.
    """
    
    rule = models.ForeignKey(
        'InferenceRule',
        related_name='inferences',
        editable=False)
    
    weight = models.ForeignKey(
        'TargetQuestionWeight',
        related_name='inferences',
        editable=False)
    
    arguments = models.CharField(
        max_length=500,
        blank=False,
        null=False,
        editable=False,
        verbose_name=_('argument IDs'),
        help_text=_('''List of weight IDs matching the
            rule\'s left-hand-side.'''))
    
    argument_weights = models.ManyToManyField(
        'TargetQuestionWeight',
        blank=True,
        null=True,
        verbose_name=_('arguments'),
        help_text=_('''List weights matching the
            rule\'s left-hand-side.'''))
    
    @property
    def argument_objects(self):
        return [
            TargetQuestionWeight.objects.get(id=int(_))
            for _ in self.arguments.split(',')
        ]
    
    class Meta:
        unique_together = (
            ('rule', 'weight', 'arguments'),
        )

class TargetQuestionWeightManager(models.Manager):
    
    def pending_ambiguous(self, force=False):
        """
        Returns all ambiguous edges that haven't seen any attempt
        to disambiguate.
        """
        q = self.filter(
            target__sense__isnull=True,
            question__sense__isnull=True,
            prob__gt=F('target__domain__min_inference_probability'),
        ).filter(
            Q(inference_depth__isnull=True)|\
            Q(inference_depth__lte=F('target__domain__max_inference_depth'))
        )
        if not force:
            q = q.filter(
                disambiguated__isnull=True,
                disambiguation_success__isnull=True,
            )
        return q

class TargetQuestionWeight(models.Model):
    """
    Represents the association between a target and question.
    """
    
    objects = TargetQuestionWeightManager()
    
    target = models.ForeignKey(
        Target,
        related_name='weights')
    
    question = models.ForeignKey(
        Question,
        related_name='weights')
    
    weight = models.FloatField(
        default=0,
        blank=False,
        null=False,
        db_index=True,
        help_text=_('''
            A positive value indicates a YES belief in the association.
            A negative value indicates a NO belief in the association.'''))
    
    count = models.PositiveIntegerField(
        default=0,
        db_index=True,
        blank=False,
        null=False,
        help_text=_('The total number of votes on this weight.'))
    
    nweight = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_('normalized weight'),
        editable=False,
        db_index=True,
        help_text=_('Normalized weight value. Equivalent to weight/count.'))
    
    prob = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_('probability'),
        editable=False,
        db_index=True,
        help_text=_('The normalized weight scaled to [0:1].'))
    
    text = models.TextField(
        blank=True,
        null=True,
        help_text=_('''A user-friendly presentation of the triple.
            Stores the surface-text if this weight comes from ConceptNet.'''))
    
#    conceptnet_uri = models.CharField(
#        max_length=500,
#        blank=True,
#        null=True,
#        db_index=True,
#        editable=False)
    
    inference_depth = models.PositiveIntegerField(
        blank=True,
        null=True,
        editable=False,
        db_index=True,
        help_text=_('''If this node was inferred by a rule, this represents how
            many previous inferences lead to this. A blank or depth of 0
            indicates that the weight was entered by a user and that no rules
            were used.'''))
    
    disambiguated = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        editable=False,
        help_text=_('''The date/time when this weight had a less-ambiguous
            version of it created. This will be blank for edges whose nodes
            have no ambiguity.'''))
            
    disambiguation_success = models.NullBooleanField(
        default=None,
        db_index=True,
        help_text=_('''If true, indicates disambiguation succeeded.
            If false, indicates failure.'''))
    
    created = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        editable=False)
        
    @property
    def normalized_weight(self):
        if not self.count:
            return
        return self.weight/float(self.count)
    
    class Meta:
        unique_together = (
            ('target', 'question'),
        )
        index_together = (
            ('target', 'question', 'weight'),
        )
        ordering = ('-prob',)
    
    def __unicode__(self):
        return u'%s %s = %s' % (self.target.slug, self.question.slug, self.weight)
    
    def __str__(self):
        return '%s %s = %s' % (self.target.slug, self.question.slug, self.weight)
    
    def vote(self, value, save=True):
        assert c.NO <= value <= c.YES
        self.weight += value
        self.count += 1
        if save:
            self.save()
    
    def save(self, *args, **kwargs):
        
        if self.count:
            self.nweight = self.normalized_weight
            assert c.NO <= self.nweight <= c.YES, 'Out-of-range weight: %s' % (self.nweight,)
            self.prob = (self.nweight + c.YES)/float(c.YES - c.NO)
        else:
            self.prob = None
            self.nweight = None
        
        is_new = not self.id
        
        super(TargetQuestionWeight, self).save(*args, **kwargs)
        
        # Incrementally update target weight counts.
        if is_new:
            
            target_q = Target.objects.filter(id=self.target.id)
            target_q.update(total_weights=F('total_weights')+1)
            if self.question.sense:
                target_q.update(total_weights_uaq=F('total_weights_uaq')+1)
            else:
                target_q.update(total_weights_aq=F('total_weights_aq')+1)
            
            question_q = Question.objects.filter(id=self.question.id)
            question_q.update(total_weights=F('total_weights')+1)
            if self.target.sense:
                question_q.update(total_weights_uaq=F('total_weights_uaq')+1)
            else:
                question_q.update(total_weights_aq=F('total_weights_aq')+1)

class Answer(models.Model):
    """
    The user's response to a question or guess in a session.
    
    May be one of three types:
    * attribute answer
    * target guess
    """
    
    session = models.ForeignKey(
        Session,
        related_name='answers')
    
    # May be null if a guess is made.
    question = models.ForeignKey(
        Question,
        related_name='answers',
        on_delete=models.SET_NULL,
        editable=False,
        blank=True,
        null=True)
    
    question_text = models.CharField(
        max_length=1000,
        blank=True,
        editable=False,
        null=True)
    
    # May be null if a question is asked.
    guess = models.ForeignKey(
        Target,
        related_name='guesses',
        blank=True,
        editable=False,
        null=True)
    
    answer = models.IntegerField(
        choices=c.ANSWER_CHOICES,
        blank=True,
        null=True,
        editable=False,
        db_index=True)
        
    ranked = models.BooleanField(
        default=False,
        editable=False,
        help_text=_('''If true, indicate this answer was used to update
            rankings. False otherwise.'''))
    
    class Meta:
        ordering = ('id',)
        unique_together = (
            ('session', 'question', 'guess'),
            ('session', 'question'),
            ('session', 'guess'),
        )
    
    def __str__(self):
        if self.question:
            return 'question: %s %s' % (self.question.slug, self.answer)
        elif self.guess:
            return 'guess: %s %s' % (self.guess.slug, self.answer)
    
    def save(self, *args, **kwargs):
        if not self.question and not self.guess:
            raise Exception('Either a question or guess must be specified.')
        if not self.id:
            if self.question and not self.question_text:
                self.question_text = self.question.slug
        super(Answer, self).save(*args, **kwargs)

class FileImport(models.Model):
    
    domain = models.ForeignKey(Domain, related_name='file_imports')
    
    filename = models.CharField(
        max_length=200,
        blank=False,
        null=False)
        
    part = models.CharField(
        max_length=200,
        blank=False,
        null=False)
    
    current_line = models.PositiveIntegerField(
        blank=True,
        null=True)
    
    total_lines = models.PositiveIntegerField(
        blank=True,
        null=True)
    
    complete = models.BooleanField(
        default=False,
        editable=False,
        db_index=True)
    
    created = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        editable=False)
        
    @property
    def done(self):
        return self.total_lines and self.current_line == self.total_lines
    
    @property
    def percent(self):
        if not self.total_lines:
            return
        if self.current_line is None:
            return
        return self.current_line/float(self.total_lines)*100
        
    def percent_str(self):
        percent = self.percent
        if percent is None:
            return
        return '%.02f%%' % percent
    percent_str.short_description = 'percent'
    
    class Meta:
        unique_together = (
            ('domain', 'filename', 'part'),
        )
        ordering = ('domain', 'filename', 'part')
    
    def save(self, *args, **kwargs):
        
        self.complete = False
        if self.total_lines:
            self.complete = self.total_lines == self.current_line
        
        super(FileImport, self).save(*args, **kwargs)
        