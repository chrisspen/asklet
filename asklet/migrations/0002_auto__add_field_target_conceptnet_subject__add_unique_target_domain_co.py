# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Target.conceptnet_subject'
        db.add_column('asklet_target', 'conceptnet_subject',
                      self.gf('django.db.models.fields.CharField')(db_index=True, max_length=500, null=True, blank=True),
                      keep_default=False)

        # Adding unique constraint on 'Target', fields ['domain', 'conceptnet_subject']
        db.create_unique('asklet_target', ['domain_id', 'conceptnet_subject'])

        # Adding field 'Question.conceptnet_predicate'
        db.add_column('asklet_question', 'conceptnet_predicate',
                      self.gf('django.db.models.fields.CharField')(db_index=True, max_length=500, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Question.conceptnet_object'
        db.add_column('asklet_question', 'conceptnet_object',
                      self.gf('django.db.models.fields.CharField')(db_index=True, max_length=500, null=True, blank=True),
                      keep_default=False)

        # Adding unique constraint on 'Question', fields ['domain', 'conceptnet_predicate', 'conceptnet_object']
        db.create_unique('asklet_question', ['domain_id', 'conceptnet_predicate', 'conceptnet_object'])


    def backwards(self, orm):
        # Removing unique constraint on 'Question', fields ['domain', 'conceptnet_predicate', 'conceptnet_object']
        db.delete_unique('asklet_question', ['domain_id', 'conceptnet_predicate', 'conceptnet_object'])

        # Removing unique constraint on 'Target', fields ['domain', 'conceptnet_subject']
        db.delete_unique('asklet_target', ['domain_id', 'conceptnet_subject'])

        # Deleting field 'Target.conceptnet_subject'
        db.delete_column('asklet_target', 'conceptnet_subject')

        # Deleting field 'Question.conceptnet_predicate'
        db.delete_column('asklet_question', 'conceptnet_predicate')

        # Deleting field 'Question.conceptnet_object'
        db.delete_column('asklet_question', 'conceptnet_object')


    models = {
        'asklet.answer': {
            'Meta': {'ordering': "('id',)", 'unique_together': "(('session', 'question', 'guess'), ('session', 'question'), ('session', 'guess'))", 'object_name': 'Answer'},
            'answer': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'guess': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'guesses'", 'null': 'True', 'to': "orm['asklet.Target']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['asklet.Question']"}),
            'question_text': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'session': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'answers'", 'to': "orm['asklet.Session']"})
        },
        'asklet.domain': {
            'Meta': {'object_name': 'Domain'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_questions': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'top_n_guess': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'})
        },
        'asklet.question': {
            'Meta': {'unique_together': "(('domain', 'slug'), ('domain', 'index'), ('domain', 'conceptnet_predicate', 'conceptnet_object'))", 'object_name': 'Question'},
            'conceptnet_object': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'conceptnet_predicate': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions'", 'to': "orm['asklet.Domain']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'asklet.session': {
            'Meta': {'object_name': 'Session'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sessions'", 'to': "orm['asklet.Domain']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merged': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sessions'", 'null': 'True', 'to': "orm['asklet.Target']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sessions'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'user_uuid': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'winner': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'})
        },
        'asklet.target': {
            'Meta': {'unique_together': "(('domain', 'slug'), ('domain', 'index'), ('domain', 'conceptnet_subject'))", 'object_name': 'Target'},
            'conceptnet_subject': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'targets'", 'to': "orm['asklet.Domain']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        'asklet.targetquestionweight': {
            'Meta': {'ordering': "('-weight',)", 'unique_together': "(('target', 'question'),)", 'object_name': 'TargetQuestionWeight', 'index_together': "(('target', 'question', 'weight'),)"},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'weights'", 'to': "orm['asklet.Question']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'weights'", 'to': "orm['asklet.Target']"}),
            'weight': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'user_set'", 'blank': 'True', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'user_set'", 'blank': 'True', 'to': "orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['asklet']