
from django.conf import settings
from django.contrib import admin
from django.utils.translation import (
    ungettext,
    ugettext_lazy as _
)

from admin_steroids.options import BetterRawIdFieldsModelAdmin
from admin_steroids.filters import NullListFilter

from . import models

class ModelAdmin(BetterRawIdFieldsModelAdmin):
    pass


class DomainAdmin(ModelAdmin):
    
    list_display = (
        'id',
        'slug',
        #'targets_count',
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
        'rule_count',
    )
    
    def connectivity_str(self, obj):
        if not obj or obj.connectivity is None:
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
    
    def rule_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/inferencerule/?domain=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.rules.all().count(),)
    rule_count.short_description = 'rules'
    rule_count.allow_tags = True

admin.site.register(models.Domain, DomainAdmin)

class InferenceRuleAdmin(ModelAdmin):
    
    list_display = (
        'name',
        'domain',
        'enabled',
    )
    
    list_filter = (
        'enabled',
    )
    
    raw_id_fields = (
        'domain',
    )
    
    readonly_fields = (
        'inference_count',
    )
    
    def inference_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/targetquestionweightinference/?rule=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.inferences.all().count(),)
    inference_count.short_description = 'inferences'
    inference_count.allow_tags = True

admin.site.register(models.InferenceRule, InferenceRuleAdmin)

class TargetQuestionWeightInferenceAdmin(ModelAdmin):
    
    list_display = (
        'id',
        'rule',
        'weight',
        'arguments',
    )
    
    list_filter = (
    )
    
    raw_id_fields = (
        'rule',
        'weight',
    )
    
    readonly_fields = (
        'rule',
        'weight',
        'arguments',
        'arguments_str',
    )
    
    def arguments_str(self, obj=None):
        if not obj:
            return ''
        parents = [
            models.TargetQuestionWeight.objects.get(id=int(_))
            for _ in obj.arguments.split(',')
        ]
        return '<br/>'.join(map(unicode, parents))
    arguments_str.short_description = 'arguments'
    arguments_str.allow_tags = True

admin.site.register(models.TargetQuestionWeightInference, TargetQuestionWeightInferenceAdmin)

class TargetAdmin(ModelAdmin):
    
    list_display = (
        'id',
        'slug',
        'language_name',
        'word',
        'pos',
        'sense',
        #'index',
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
        ('sense', NullListFilter),
    )
    
    readonly_fields = (
        'weights_count',
        'slug_parts',
        'language_name',
        'pos',
        'sense',
        'get_all_extended_glosses',
    )
    
    def lookup_allowed(self, key, value=None):
        return True
        
    def weights_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/targetquestionweight/?target=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.weights.all().count(),)
    weights_count.short_description = 'weights'
    weights_count.allow_tags = True
    
admin.site.register(models.Target, TargetAdmin)

class TargetMissingAdmin(ModelAdmin):
    
    list_display = (
        'slug',
        'language',
        'pos',
        'domain',
        'sense',
    )
    
    list_filter = (
        'language',
        'pos',
    )
    
    search_fields = (
        'slug',
    )
    
    readonly_fields = (
        'slug',
        'language',
        'pos',
        'domain',
        'sense',
        'text',
    )

admin.site.register(models.TargetMissing, TargetMissingAdmin)

class QuestionAdmin(ModelAdmin):
    
    list_display = (
        'id',
        'slug',
        'language_name',
        'word',
        'pos',
        'sense',
        #'index',
        'domain',
        'weights_count',
        'enabled',
    )
    
    search_fields = (
        'slug',
    )
    
    list_filter = (
        'enabled',
        ('sense', NullListFilter),
    )
    
    raw_id_fields = (
        'domain',
    )
    
    readonly_fields = (
        'weights_count',
        'slug_parts',
        'language_name',
        'pos',
        'sense',
    )
    
    def weights_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/targetquestionweight/?question=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.weights.all().count(),)
    weights_count.short_description = 'weights'
    weights_count.allow_tags = True
    
admin.site.register(models.Question, QuestionAdmin)

class TargetQuestionWeightAdmin(ModelAdmin):
    
    list_display = (
        'id',
        'target',
        'question',
        'weight',
        'count',
        #'normalized_weight',
        'prob',
        'inference_depth',
    )
    
    search_fields = (
        'target__slug',
        'question__slug',
    )
    
    list_filter = (
        ('inference_depth', NullListFilter),
    )
    
    raw_id_fields = (
        'target',
        'question',
    )
    
    readonly_fields = (
        #'weights_count',
        'normalized_weight',
        'prob',
        'inference_count',
    )
    
    def lookup_allowed(self, key, value=None):
        return True
    
    def weights_count(self, obj):
        if not obj:
            return 0
        return obj.weights.all().count()
    weights_count.short_description = 'weights'
    
    def inference_count(self, obj):
        if not obj:
            return 0
        return '<a href="/admin/asklet/targetquestionweightinference/?weight=%i" class="button" target="_blank">View %i</a>' % (obj.id, obj.inferences.all().count(),)
    inference_count.short_description = 'inferences'
    inference_count.allow_tags = True
    
admin.site.register(models.TargetQuestionWeight, TargetQuestionWeightAdmin)

class AnswerInline(admin.TabularInline):
    
    model = models.Answer
    
    readonly_fields = (
        'question',
        'guess',
        'answer',
    )
    
    max_num = 0

class SessionAdmin(ModelAdmin):
    
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

class FileImportAdmin(ModelAdmin):
    
    list_display = (
        'domain',
        'filename',
        'part',
        'current_line',
        'total_lines',
        'percent_str',
        'complete',
    )
    
    list_filter = (
        'complete',
    )
    
    readonly_fields = (
        'percent_str',
        'complete',
    )
    
admin.site.register(models.FileImport, FileImportAdmin)

