import random
from collections import defaultdict

from django.db import models
from django.db.transaction import commit_on_success
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

import six
u = six.u
unicode = six.text_type
basestring = six.string_types

from . import constants as c
from . import settings as _settings
from .backends.sql import SQLBackend

def get_backend_cls():
    name = settings.ASKLET_BACKEND
    if name == 'SQL':
        return SQLBackend
    else:
        raise NotImplementedError('Unknown backend: %s' % (name,))

class Domain(models.Model):
    """
    A specific context used to organize separate groups
    of questions and targets.
    
    Also manages the learned model.
    """
    
    slug = models.SlugField(
        unique=True,
        blank=False,
        null=False)
    
    max_questions = models.PositiveIntegerField(
        default=20,
        help_text=_('''The maximum number of questions the system will
            be allowed to ask in a session.'''))
    
    top_n_guess = models.PositiveIntegerField(
        default=5,
        help_text=_('''If a target is the top-ranked choice for this many
            iterations, it will be used as a guess.'''))
    
    def __unicode__(self):
        return self.slug
    
    def __str__(self):
        return '<Domain: %s>' % (self.slug,)
    
    def accuracy_history(self, chunk=10):
        try:
            sessions = self.sessions.filter(winner__isnull=False).order_by('id')
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
        max_weight_count = self.targets.all().count() * self.questions.all().count()
        actual_weight_count = self.weights.all().count()
        if not max_weight_count:
            return
        ratio = actual_weight_count/float(max_weight_count)
        return ratio
    
    @property
    def weights(self):
        return TargetQuestionWeight.objects.filter(target__domain=self)
    
    def get_weight(self, target, question, normalized=False):
        if isinstance(question, Question):
            weights = TargetQuestionWeight.objects.filter(target=target, question=question)
        elif isinstance(question, basestring):
            weights = TargetQuestionWeight.objects.filter(target=target, question__slug=question)
        if weights.exists():
            if normalized:
                return weights[0].normalized_weight
            else:
                return weights[0].weight
        return 0
    
    def rank_targets(self, answers, prior_failed_target_ids=[], prior_top_target_ids=[], target_rankings=None, verbose=False):
        """
        Returns a list of targets ordered from most likely to least likely
        to be the user's choice.
        
        answers := {question_slug: answer_int}
        prior_failed_target_ids := [target_ids that should be ignored]
        prior_top_target_ids := [target_ids to start with]
        
        Note, this implementation is a hypothetical interpreation of Burgener's
        algorithm, as sections 0048 and 0049, which claim to describe the
        target ranking, omit any explanation of how the final aggregation is
        to occur. Empirical tests taking a sum of the user's answer weight plus
        the pre-adjusted weight result in no learning.
        What follows is an educated guess of how to accomplish the result,
        even though the method below is not actually described in the patent
        filing.
        """
        #print('target_rankings:',target_rankings)
        assert isinstance(target_rankings, dict)
        target_rankings = target_rankings or defaultdict(int) # {target:rank}
        targets = self.targets.all()
        
        # Exclude the targets the user has explicitly said NO to.
        if prior_failed_target_ids:
            targets = targets.exclude(id__in=prior_failed_target_ids)
            
        # Start with the top targets if we know them.
        if prior_top_target_ids:
            targets = targets.filter(id__in=prior_top_target_ids)
        
        #TODO:cache target rankings and only update when a new answer is provided
        for target in targets.iterator():
            if target not in target_rankings:
                target_rankings[target] = 0
            if verbose: print('target:',target.slug)
            for question_slug, answer_weight in answers.items():
                if not question_slug:
                    continue
                local_weight = self.get_weight(target, question_slug, normalized=True)
                if verbose: print('\tanswer weight:', question_slug, answer_weight, local_weight)
                agreement = (local_weight < 0 and answer_weight < 0) or (local_weight > 0 and answer_weight > 0)
                #TODO:is this correct? section 0048 is ambiguous
                diff = abs((answer_weight + local_weight)/2.)
                if agreement:
                    target_rankings[target] += diff
                else:
                    target_rankings[target] -= diff
            if verbose: print('\tfinal weight:',target_rankings[target])
            
        if verbose: print('%i targets' % len(target_rankings))
        
        # Higher rank means more likely to be the target the user is thinking.
        top_targets = sorted(target_rankings.items(), key=lambda o:o[1], reverse=True)
        
        return top_targets
    
    def rank_questions(self, targets, previous_question_ids=[], verbose=True):
        #print('targets:',targets)
        
        questions = Question.objects.askable(self.questions.all())
        if verbose: print('askable0:',questions.count())
        if previous_question_ids:
            if verbose: print('previous_question_ids:',previous_question_ids)
            questions = questions.exclude(id__in=previous_question_ids)
        if verbose: print('askable1:',questions.count())
    
        if verbose:
            print('%i askable questions out of %i total questions and %i questions asked' \
                % (
                   questions.count(),
                   self.questions.all().count(),
                   len(previous_question_ids),
                ))
#        splittable_questions = questions
        splittable_questions = questions.filter(
            weights__id__isnull=False,
            weights__target__in=targets).distinct()
        question_rankings = defaultdict(int) # {question:rank}
        for question in splittable_questions.iterator():
#            for target in targets:
            for weight in question.weights.all().iterator():
#                if TargetQuestionWeight.objects.filter(target=target, question=question).exists()
                #TODO:use raw weight?
                
                #accuracy=1/20
                question_rankings[question] += 1 if weight.weight > 0 else -1
                
                #accuracy=2/20
#                question_rankings[question] += weight.weight or 0
                
                #accuracy=0/20
#                if not weight.count:
#                    continue
#                question_rankings[question] += weight.weight/float(weight.count)
        if verbose: print('%i splittable questions' % splittable_questions.count())
        #TODO:rank questions by finding the one with the most even YES/NO split, explained in 0053
        # Lower rank means better splitting criteria.
        question_rankings = sorted(question_rankings.items(), key=lambda o: abs(o[1]))
        return question_rankings
    
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
    
    def questions_count(self):
        return self.answers.all().count()
    questions_count.short_description = 'questions'
    
    def __unicode__(self):
        return u('user %s in domain %s' % (self.user or self.user_uuid, self.domain))
    
    def get_top_targets_cache(self):
        prior_top_target_ids = []
        if hasattr(self, '_cached_prior_top_target_ids'):
            prior_top_target_ids = self._cached_prior_top_target_ids
        return prior_top_target_ids
        
    def clear_top_targets_cache(self):
        self._cached_prior_top_target_ids = []
    
    def save_top_targets_cache(self, lst):
        self._cached_prior_top_target_ids = lst
    
    def get_target_rankings_cache(self):
        if hasattr(self, '_cached_target_rankings'):
            d = self._cached_target_rankings
            if not isinstance(d, dict):
                d = dict(d)
            return d
        return defaultdict(int)
    
    def save_target_rankings_cache(self, tr):
        if not isinstance(tr, dict):
            d = defaultdict(int)
            d.update(tr)
        self._cached_target_rankings = tr
    
    def get_prior_question_ids_cache(self):
        if hasattr(self, '_cached_prior_question_ids'):
            return self._cached_prior_question_ids
        return []
        
    def save_prior_question_ids_cache(self, lst):
        self._cached_prior_question_ids = lst
    
    def get_next_question(self, verbose=0):
        """
        Returns the next best question to ask.
        """
        if not self.winner is None:
            return
        
        answers = self.answers.all()
        prior_failed_target_ids = set(self.answers.filter(guess__isnull=False).values_list('guess_id', flat=True))
        if verbose: print('%i answers provided' % answers.count())
        
        prior_top_target_ids = self.get_top_targets_cache()
        
        # First mode.
        # Rank targets according to the answers we've received so far.
        # Described in section 0048.
        #TODO:cache, so we don't have to iterate over millions of targets each time
        #TODO:use a priority-dictionary?
        if verbose:
            print('Prior answers:')
            for answer in answers:
                if answer.question:
                    print(answer.question.slug, answer.answer)
                else:
                    print(answer.guess.slug, answer.answer)
            print('')
        
#        print('answers:',answers)
        target_rankings = self.get_target_rankings_cache()
        prior_question_ids = self.get_prior_question_ids_cache()
        top_targets = self.domain.rank_targets(
            answers=dict((answer.question.slug, answer.answer) for answer in answers if answer.question and answer.question.id not in prior_question_ids),
            prior_failed_target_ids=prior_failed_target_ids,
            prior_top_target_ids=prior_top_target_ids,
            target_rankings=target_rankings,
        )
        self.save_target_rankings_cache(top_targets)
        self.save_prior_question_ids_cache(answer.question.id for answer in answers if answer.question)
        
        #TODO:remove targets that have low weights, 0050
        trunc = int(len(top_targets)*0.1)
        if verbose: print('trunc:',trunc)
        if verbose: print('%i top targets' % len(top_targets))
        if trunc > 10:
            top_targets = top_targets[:trunc]
        if verbose:
            print('%i top targets' % len(top_targets))
            for target,rank in top_targets:
                print('top target:', rank, target)
        
        # Create and maintain a cached list of the last N top targets.
        if not hasattr(self, '_cached_last_top_targets'):
            self._cached_last_top_targets = []
        last_top_targets = self._cached_last_top_targets
        if top_targets:
            last_top_targets.append(top_targets[0][0])
        
        last_top_targets_n = self.domain.top_n_guess
        
        if last_top_targets_n and len(last_top_targets) >= last_top_targets_n \
        and len(set(last_top_targets[-last_top_targets_n:])) == 1:
            # If the last N top targets are all the same, then guess that target.
            top_target = last_top_targets[-1]
            # Clear the cached list, so if we're wrong, we won't re-recommend the same target.
            self._cached_last_top_targets = []
            self.clear_top_targets_cache()
            return top_target
        elif not top_targets:
            return
        elif len(top_targets) == 1:
            self.clear_top_targets_cache()
            return top_targets[0][0]
        elif answers.count()+1 == self.domain.max_questions:
            # We only have one more question left, so make our best guess.
            self.clear_top_targets_cache()
            return top_targets[0][0]
        
        self.save_top_targets_cache(list(target.id for target,rank in top_targets))
        
        # Second mode.
        previous_question_ids = self.answers.filter(question__isnull=False).values_list('question_id', flat=True)
        #print('previous_question_ids:',previous_question_ids)
        question_rankings = self.domain.rank_questions(
            targets=[_1 for _1,_2 in top_targets],
            previous_question_ids=previous_question_ids,
            verbose=verbose)
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
        
        for attr, belief in attrs:
            if verbose: print('User: %s %s' % (attr, belief))
            question, _ = Question.objects.get_or_create(domain=self.domain, slug=attr)
            Answer.objects.get_or_create(session=self, question=question, defaults=dict(answer=belief))
        
        if isinstance(actual, Target):
            target = actual
            actual_slug = target.slug
        else:
            target, _ = Target.objects.get_or_create(
                domain=self.domain,
                slug=actual,
                defaults=dict(enabled=True))
            actual_slug = actual
        
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
        
        self.winner = guess_slug == actual_slug
        self.target = target
        if merge:
            self.merge(verbose=verbose)
        
        self.save()
        
    @commit_on_success
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

class Target(models.Model):
    """
    Things to guess.
    """
    
    domain = models.ForeignKey(Domain, related_name='targets')
    
    slug = models.SlugField(
        blank=False,
        null=False,
        db_index=True)
    
    index = models.PositiveIntegerField(
        default=0,
        editable=False,
        db_index=True)

    enabled = models.BooleanField(
        default=False,
        db_index=True)

    class Meta:
        unique_together = (
            ('domain', 'slug'),
            ('domain', 'index'),
        )
    
    def __unicode__(self):
        return self.slug
    
    def __str__(self):
        return u(self.slug)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.index = self.domain.targets.all().only('id').count()
        super(Target, self).save(*args, **kwargs)

class QuestionManager(models.Manager):
    
    def askable(self, q=None):
        if q is None:
            q = self
        return q.filter(enabled=True)

class Question(models.Model):
    """
    An arbitrary query to be proposed to the user.
    """
    
    objects = QuestionManager()
    
    domain = models.ForeignKey(Domain, related_name='questions')
    
    slug = models.SlugField(
        blank=False,
        null=False,
        db_index=True)
    
    text = models.TextField(
        blank=True,
        null=True,
        help_text=_('A user-friendly presentation of the question.'))
    
    index = models.PositiveIntegerField(
        default=0,
        editable=False,
        db_index=True)
    
    enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_('''If checked, this question might be asked of the user.
            Otherwise, it will not be asked.'''))
    
    class Meta:
        unique_together = (
            ('domain', 'slug'),
            ('domain', 'index'),
        )
    
    def __unicode__(self):
        return self.text or self.slug
    
    def __str__(self):
        return u(self.text or self.slug)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.index = self.domain.questions.all().only('id').count()
        super(Question, self).save(*args, **kwargs)

class TargetQuestionWeight(models.Model):
    
    target = models.ForeignKey(
        Target,
        related_name='weights')
    
    question = models.ForeignKey(
        Question,
        related_name='weights')
    
    weight = models.IntegerField(
        default=0,
        blank=False,
        null=False,
        help_text=_('''
            A positive value indicates a YES belief in the association.
            A negative value indicates a NO belief in the association.'''))
    
    count = models.PositiveIntegerField(
        default=0,
        blank=False,
        null=False)
    
    @property
    def normalized_weight(self):
        return self.weight/float(self.count)
    
    class Meta:
        unique_together = (
            ('target', 'question'),
        )
        index_together = (
            ('target', 'question', 'weight'),
        )
        ordering = ('-weight',)
    
    def __str__(self):
        return u('%s %s = %s' % (self.target.slug, self.question.slug, self.weight))
    
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
        