# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Domain'
        db.create_table('asklet_domain', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('max_questions', self.gf('django.db.models.fields.PositiveIntegerField')(default=20)),
            ('top_n_guess', self.gf('django.db.models.fields.PositiveIntegerField')(default=5)),
        ))
        db.send_create_signal('asklet', ['Domain'])

        # Adding model 'Session'
        db.create_table('asklet_session', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('domain', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sessions', to=orm['asklet.Domain'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sessions', null=True, on_delete=models.SET_NULL, to=orm['auth.User'])),
            ('user_uuid', self.gf('django.db.models.fields.CharField')(max_length=500, null=True, blank=True)),
            ('winner', self.gf('django.db.models.fields.NullBooleanField')(default=None, null=True, db_index=True, blank=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sessions', null=True, to=orm['asklet.Target'])),
            ('merged', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('asklet', ['Session'])

        # Adding model 'Target'
        db.create_table('asklet_target', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('domain', self.gf('django.db.models.fields.related.ForeignKey')(related_name='targets', to=orm['asklet.Domain'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('index', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, db_index=True)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
        ))
        db.send_create_signal('asklet', ['Target'])

        # Adding unique constraint on 'Target', fields ['domain', 'slug']
        db.create_unique('asklet_target', ['domain_id', 'slug'])

        # Adding unique constraint on 'Target', fields ['domain', 'index']
        db.create_unique('asklet_target', ['domain_id', 'index'])

        # Adding model 'Question'
        db.create_table('asklet_question', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('domain', self.gf('django.db.models.fields.related.ForeignKey')(related_name='questions', to=orm['asklet.Domain'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('text', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('index', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, db_index=True)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True, db_index=True)),
        ))
        db.send_create_signal('asklet', ['Question'])

        # Adding unique constraint on 'Question', fields ['domain', 'slug']
        db.create_unique('asklet_question', ['domain_id', 'slug'])

        # Adding unique constraint on 'Question', fields ['domain', 'index']
        db.create_unique('asklet_question', ['domain_id', 'index'])

        # Adding model 'TargetQuestionWeight'
        db.create_table('asklet_targetquestionweight', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(related_name='weights', to=orm['asklet.Target'])),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(related_name='weights', to=orm['asklet.Question'])),
            ('weight', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('count', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('asklet', ['TargetQuestionWeight'])

        # Adding unique constraint on 'TargetQuestionWeight', fields ['target', 'question']
        db.create_unique('asklet_targetquestionweight', ['target_id', 'question_id'])

        # Adding index on 'TargetQuestionWeight', fields ['target', 'question', 'weight']
        db.create_index('asklet_targetquestionweight', ['target_id', 'question_id', 'weight'])

        # Adding model 'Answer'
        db.create_table('asklet_answer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('session', self.gf('django.db.models.fields.related.ForeignKey')(related_name='answers', to=orm['asklet.Session'])),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='answers', null=True, on_delete=models.SET_NULL, to=orm['asklet.Question'])),
            ('question_text', self.gf('django.db.models.fields.CharField')(max_length=1000, null=True, blank=True)),
            ('guess', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='guesses', null=True, to=orm['asklet.Target'])),
            ('answer', self.gf('django.db.models.fields.IntegerField')(db_index=True, null=True, blank=True)),
        ))
        db.send_create_signal('asklet', ['Answer'])

        # Adding unique constraint on 'Answer', fields ['session', 'question', 'guess']
        db.create_unique('asklet_answer', ['session_id', 'question_id', 'guess_id'])

        # Adding unique constraint on 'Answer', fields ['session', 'question']
        db.create_unique('asklet_answer', ['session_id', 'question_id'])

        # Adding unique constraint on 'Answer', fields ['session', 'guess']
        db.create_unique('asklet_answer', ['session_id', 'guess_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Answer', fields ['session', 'guess']
        db.delete_unique('asklet_answer', ['session_id', 'guess_id'])

        # Removing unique constraint on 'Answer', fields ['session', 'question']
        db.delete_unique('asklet_answer', ['session_id', 'question_id'])

        # Removing unique constraint on 'Answer', fields ['session', 'question', 'guess']
        db.delete_unique('asklet_answer', ['session_id', 'question_id', 'guess_id'])

        # Removing index on 'TargetQuestionWeight', fields ['target', 'question', 'weight']
        db.delete_index('asklet_targetquestionweight', ['target_id', 'question_id', 'weight'])

        # Removing unique constraint on 'TargetQuestionWeight', fields ['target', 'question']
        db.delete_unique('asklet_targetquestionweight', ['target_id', 'question_id'])

        # Removing unique constraint on 'Question', fields ['domain', 'index']
        db.delete_unique('asklet_question', ['domain_id', 'index'])

        # Removing unique constraint on 'Question', fields ['domain', 'slug']
        db.delete_unique('asklet_question', ['domain_id', 'slug'])

        # Removing unique constraint on 'Target', fields ['domain', 'index']
        db.delete_unique('asklet_target', ['domain_id', 'index'])

        # Removing unique constraint on 'Target', fields ['domain', 'slug']
        db.delete_unique('asklet_target', ['domain_id', 'slug'])

        # Deleting model 'Domain'
        db.delete_table('asklet_domain')

        # Deleting model 'Session'
        db.delete_table('asklet_session')

        # Deleting model 'Target'
        db.delete_table('asklet_target')

        # Deleting model 'Question'
        db.delete_table('asklet_question')

        # Deleting model 'TargetQuestionWeight'
        db.delete_table('asklet_targetquestionweight')

        # Deleting model 'Answer'
        db.delete_table('asklet_answer')


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
            'Meta': {'unique_together': "(('domain', 'slug'), ('domain', 'index'))", 'object_name': 'Question'},
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
            'Meta': {'unique_together': "(('domain', 'slug'), ('domain', 'index'))", 'object_name': 'Target'},
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