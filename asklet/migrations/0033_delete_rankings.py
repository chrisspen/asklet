# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        Ranking = orm['asklet.Ranking']
        qs = Ranking.objects.all()
        qs.delete()


    def backwards(self, orm):
        pass


    models = {
        u'asklet.answer': {
            'Meta': {'ordering': "('id',)", 'unique_together': "(('session', 'question', 'guess'), ('session', 'question'), ('session', 'guess'))", 'object_name': 'Answer'},
            'answer': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'guess': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'guesses'", 'null': 'True', 'to': u"orm['asklet.Target']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['asklet.Question']"}),
            'question_text': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'ranked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'session': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'answers'", 'to': u"orm['asklet.Session']"})
        },
        u'asklet.domain': {
            'Meta': {'object_name': 'Domain'},
            'allow_inference': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'assumption': ('django.db.models.fields.CharField', [], {'default': "'closed'", 'max_length': '25', 'db_index': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'default_inference_count': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'max_inference_depth': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'max_questions': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'min_inference_probability': ('django.db.models.fields.FloatField', [], {'default': '0.5'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '500'}),
            'top_n_guess': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'})
        },
        u'asklet.fileimport': {
            'Meta': {'ordering': "('domain', 'filename', 'part')", 'unique_together': "(('domain', 'filename', 'part'),)", 'object_name': 'FileImport'},
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'current_line': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'file_imports'", 'to': u"orm['asklet.Domain']"}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'part': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'total_lines': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'asklet.inferencerule': {
            'Meta': {'unique_together': "(('domain', 'name'),)", 'object_name': 'InferenceRule'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rules'", 'to': u"orm['asklet.Domain']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lhs': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'rhs': ('django.db.models.fields.TextField', [], {})
        },
        u'asklet.question': {
            'Meta': {'unique_together': "(('domain', 'slug'), ('domain', 'index'), ('domain', 'conceptnet_predicate', 'conceptnet_object'))", 'object_name': 'Question'},
            'conceptnet_object': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'conceptnet_predicate': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions'", 'to': u"orm['asklet.Domain']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'object': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questions'", 'null': 'True', 'to': u"orm['asklet.Target']"}),
            'pos': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'sense': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'slug_parts': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'total_weights': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'total_weights_aq': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'total_weights_uaq': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'word': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'})
        },
        u'asklet.ranking': {
            'Meta': {'ordering': "('-ranking',)", 'unique_together': "(('session', 'target'),)", 'object_name': 'Ranking'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ranking': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'session': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rankings'", 'to': u"orm['asklet.Session']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rankings'", 'to': u"orm['asklet.Target']"})
        },
        u'asklet.session': {
            'Meta': {'object_name': 'Session'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sessions'", 'to': u"orm['asklet.Domain']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merged': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sessions'", 'null': 'True', 'to': u"orm['asklet.Target']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sessions'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['auth.User']"}),
            'user_uuid': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'winner': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'})
        },
        u'asklet.target': {
            'Meta': {'unique_together': "(('domain', 'slug'), ('domain', 'conceptnet_subject'))", 'object_name': 'Target'},
            'conceptnet_subject': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'targets'", 'to': u"orm['asklet.Domain']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'pos': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'sense': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '500', 'db_index': 'True'}),
            'slug_parts': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'total_senses': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'total_weights': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'total_weights_aq': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'total_weights_uaq': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'word': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'})
        },
        u'asklet.targetmissing': {
            'Meta': {'object_name': 'TargetMissing', 'managed': 'False'},
            '_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'text'", 'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'missing_targets'", 'db_column': "'domain_id'", 'to': u"orm['asklet.Domain']"}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'pos': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'sense': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '500', 'primary_key': 'True', 'db_column': "'target_slug'"})
        },
        u'asklet.targetquestionweight': {
            'Meta': {'ordering': "('-prob',)", 'unique_together': "(('target', 'question'),)", 'object_name': 'TargetQuestionWeight', 'index_together': "(('target', 'question', 'weight'),)"},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'disambiguated': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'disambiguation_success': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inference_depth': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'nweight': ('django.db.models.fields.FloatField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'prob': ('django.db.models.fields.FloatField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'weights'", 'to': u"orm['asklet.Question']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'weights'", 'to': u"orm['asklet.Target']"}),
            'text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'weight': ('django.db.models.fields.FloatField', [], {'default': '0', 'db_index': 'True'})
        },
        u'asklet.targetquestionweightinference': {
            'Meta': {'unique_together': "(('rule', 'weight', 'arguments'),)", 'object_name': 'TargetQuestionWeightInference'},
            'argument_weights': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['asklet.TargetQuestionWeight']", 'null': 'True', 'blank': 'True'}),
            'arguments': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'inferences'", 'to': u"orm['asklet.InferenceRule']"}),
            'weight': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'inferences'", 'to': u"orm['asklet.TargetQuestionWeight']"})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['asklet']