
from django.conf import settings
from django.contrib import admin
from django.utils.translation import (
    ungettext,
    ugettext_lazy as _
)

from . import models

#try:
#    from admin_steroids.queryset import ApproxCountQuerySet
#except ImportError:
#    ApproxCountQuerySet = None

class DomainAdmin(admin.ModelAdmin):
    
    list_display = (
        'id',
        'slug',
        'targets_count',
        'connectivity_str',
    )
    
    search_fields = (
        'slug',
    )
    
    readonly_fields = (
        'connectivity_str',
        'accuracy_history',
        'targets_count',
        'question_count',
        'session_count',
    )
    
    def connectivity_str(self, obj):
        if not obj:
            return
        return '%.06f' % obj.connectivity
    connectivity_str.short_description = 'connectivity'
    
    def targets_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/target/?domain=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.targets.all().count(),)
    targets_count.short_description = 'targets'
    targets_count.allow_tags = True
    
    def question_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/question/?domain=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.questions.all().count(),)
    question_count.short_description = 'questions'
    question_count.allow_tags = True
    
    def session_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/session/?domain=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.sessions.all().count(),)
    session_count.short_description = 'sessions'
    session_count.allow_tags = True

admin.site.register(models.Domain, DomainAdmin)

class TargetAdmin(admin.ModelAdmin):
    
    list_display = (
        'id',
        'slug',
        'index',
        'domain',
        'weights_count',
        'enabled',
    )
    
    search_fields = (
        'slug',
    )
    
    raw_id_fields = (
        'domain',
    )
    
    list_filter = (
        'enabled',
    )
    
    readonly_fields = (
        'weights_count',
    )
    
    def weights_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/targetquestionweight/?target=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.weights.all().count(),)
    weights_count.short_description = 'weights'
    weights_count.allow_tags = True
    
admin.site.register(models.Target, TargetAdmin)

class QuestionAdmin(admin.ModelAdmin):
    
    list_display = (
        'id',
        'slug',
        'index',
        'domain',
        'weights_count',
        'enabled',
    )
    
    search_fields = (
        'slug',
    )
    
    list_filter = (
        'enabled',
    )
    
    raw_id_fields = (
        'domain',
    )
    
    readonly_fields = (
        'weights_count',
    )
    
    def weights_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/targetquestionweight/?question=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.weights.all().count(),)
    weights_count.short_description = 'weights'
    weights_count.allow_tags = True
    
admin.site.register(models.Question, QuestionAdmin)

class TargetQuestionWeightAdmin(admin.ModelAdmin):
    
    list_display = (
        'id',
        'target',
        'question',
        'weight',
        'count',
        #'normalized_weight',
        'prob',
    )
    
    search_fields = (
        'target__slug',
        'question__slug',
    )
    
    list_filter = (
    )
    
    raw_id_fields = (
        'target',
        'question',
    )
    
    readonly_fields = (
        #'weights_count',
        'normalized_weight',
    )
    
    def lookup_allowed(self, key, value=None):
        return True
    
    def weights_count(self, obj):
        if not obj:
            return 0
        return obj.weights.all().count()
    weights_count.short_description = 'weights'
    
admin.site.register(models.TargetQuestionWeight, TargetQuestionWeightAdmin)

class AnswerInline(admin.TabularInline):
    
    model = models.Answer
    
    readonly_fields = (
        'question',
        'guess',
        'answer',
    )
    
    max_num = 0

class SessionAdmin(admin.ModelAdmin):
    
    list_display = (
        'id',
        'domain',
        'user',
        'user_uuid',
        'winner',
        'target',
        'question_count',
        'merged',
        'created',
    )
    
    list_filter = (
        'winner',
        'merged',
    )
    
    raw_id_fields = (
        'domain',
        'user',
        'target',
    )
    
    readonly_fields = (
        'question_count',
    )
    
    inlines = (
        AnswerInline,
    )
    
    def lookup_allowed(self, key, value=None):
        return True
    
admin.site.register(models.Session, SessionAdmin)