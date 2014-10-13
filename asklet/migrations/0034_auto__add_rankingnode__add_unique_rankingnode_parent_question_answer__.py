# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Ranking', fields ['session', 'target']
        db.delete_unique(u'asklet_ranking', ['session_id', 'target_id'])

        # Adding model 'RankingNode'
        db.create_table(u'asklet_rankingnode', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='children', null=True, to=orm['asklet.RankingNode'])),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(related_name='ranking_nodes', to=orm['asklet.Question'])),
            ('answer', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'asklet', ['RankingNode'])

        # Adding unique constraint on 'RankingNode', fields ['parent', 'question', 'answer']
        db.create_unique(u'asklet_rankingnode', ['parent_id', 'question_id', 'answer'])

        # Adding model 'TreeNode'
        db.create_table(u'asklet_treenode', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('domain', self.gf('django.db.models.fields.related.ForeignKey')(related_name='tree_nodes', to=orm['asklet.Domain'])),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['asklet.TreeNode'], null=True, blank=True)),
            ('parent_answer', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(related_name='tree_nodes', to=orm['asklet.Question'])),
            ('depth', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('splitting_metric', self.gf('django.db.models.fields.FloatField')()),
            ('best_splitter', self.gf('django.db.models.fields.NullBooleanField')(default=None, null=True, db_index=True, blank=True)),
            ('fresh', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal(u'asklet', ['TreeNode'])

        # Adding M2M table for field targets on 'TreeNode'
        m2m_table_name = db.shorten_name(u'asklet_treenode_targets')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('treenode', models.ForeignKey(orm[u'asklet.treenode'], null=False)),
            ('target', models.ForeignKey(orm[u'asklet.target'], null=False))
        ))
        db.create_unique(m2m_table_name, ['treenode_id', 'target_id'])

        # Adding unique constraint on 'TreeNode', fields ['parent', 'parent_answer', 'question']
        db.create_unique(u'asklet_treenode', ['parent_id', 'parent_answer', 'question_id'])

        # Adding unique constraint on 'TreeNode', fields ['domain', 'depth', 'best_splitter']
        db.create_unique(u'asklet_treenode', ['domain_id', 'depth', 'best_splitter'])

        # Adding index on 'TreeNode', fields ['domain', 'parent', 'best_splitter']
        db.create_index(u'asklet_treenode', ['domain_id', 'parent_id', 'best_splitter'])

        # Adding index on 'TreeNode', fields ['domain', 'fresh']
        db.create_index(u'asklet_treenode', ['domain_id', 'fresh'])

        # Adding index on 'TreeNode', fields ['domain', 'depth']
        db.create_index(u'asklet_treenode', ['domain_id', 'depth'])

        # Adding field 'Domain.use_tree_indexing'
        db.add_column(u'asklet_domain', 'use_tree_indexing',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Domain.max_tree_targets'
        db.add_column(u'asklet_domain', 'max_tree_targets',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1000),
                      keep_default=False)

        # Deleting field 'Ranking.session'
        db.delete_column(u'asklet_ranking', 'session_id')

        # Adding field 'Ranking.node'
        db.add_column(u'asklet_ranking', 'node',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='rankings', to=orm['asklet.RankingNode']),
                      keep_default=False)

        # Adding field 'Ranking.created'
        db.add_column(u'asklet_ranking', 'created',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, default=datetime.datetime(2014, 10, 6, 0, 0), blank=True),
                      keep_default=False)

        # Adding field 'Ranking.updated'
        db.add_column(u'asklet_ranking', 'updated',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, default=datetime.datetime(2014, 10, 6, 0, 0), db_index=True, blank=True),
                      keep_default=False)

        # Adding unique constraint on 'Ranking', fields ['node', 'target']
        db.create_unique(u'asklet_ranking', ['node_id', 'target_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Ranking', fields ['node', 'target']
        db.delete_unique(u'asklet_ranking', ['node_id', 'target_id'])

        # Removing index on 'TreeNode', fields ['domain', 'depth']
        db.delete_index(u'asklet_treenode', ['domain_id', 'depth'])

        # Removing index on 'TreeNode', fields ['domain', 'fresh']
        db.delete_index(u'asklet_treenode', ['domain_id', 'fresh'])

        # Removing index on 'TreeNode', fields ['domain', 'parent', 'best_splitter']
        db.delete_index(u'asklet_treenode', ['domain_id', 'parent_id', 'best_splitter'])

        # Removing unique constraint on 'TreeNode', fields ['domain', 'depth', 'best_splitter']
        db.delete_unique(u'asklet_treenode', ['domain_id', 'depth', 'best_splitter'])

        # Removing unique constraint on 'TreeNode', fields ['parent', 'parent_answer', 'question']
        db.delete_unique(u'asklet_treenode', ['parent_id', 'parent_answer', 'question_id'])

        # Removing unique constraint on 'RankingNode', fields ['parent', 'question', 'answer']
        db.delete_unique(u'asklet_rankingnode', ['parent_id', 'question_id', 'answer'])

        # Deleting model 'RankingNode'
        db.delete_table(u'asklet_rankingnode')

        # Deleting model 'TreeNode'
        db.delete_table(u'asklet_treenode')

        # Removing M2M table for field targets on 'TreeNode'
        db.delete_table(db.shorten_name(u'asklet_treenode_targets'))

        # Deleting field 'Domain.use_tree_indexing'
        db.delete_column(u'asklet_domain', 'use_tree_indexing')

        # Deleting field 'Domain.max_tree_targets'
        db.delete_column(u'asklet_domain', 'max_tree_targets')

        # Adding field 'Ranking.session'
        db.add_column(u'asklet_ranking', 'session',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='rankings', to=orm['asklet.Session']),
                      keep_default=False)

        # Deleting field 'Ranking.node'
        db.delete_column(u'asklet_ranking', 'node_id')

        # Deleting field 'Ranking.created'
        db.delete_column(u'asklet_ranking', 'created')

        # Deleting field 'Ranking.updated'
        db.delete_column(u'asklet_ranking', 'updated')

        # Adding unique constraint on 'Ranking', fields ['session', 'target']
        db.create_unique(u'asklet_ranking', ['session_id', 'target_id'])


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
            'max_tree_targets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1000'}),
            'min_inference_probability': ('django.db.models.fields.FloatField', [], {'default': '0.5'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '500'}),
            'top_n_guess': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'use_tree_indexing': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
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
            'Meta': {'ordering': "('-ranking',)", 'unique_together': "(('node', 'target'),)", 'object_name': 'Ranking'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rankings'", 'to': u"orm['asklet.RankingNode']"}),
            'ranking': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rankings'", 'to': u"orm['asklet.Target']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'})
        },
        u'asklet.rankingnode': {
            'Meta': {'unique_together': "(('parent', 'question', 'answer'),)", 'object_name': 'RankingNode'},
            'answer': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['asklet.RankingNode']"}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ranking_nodes'", 'to': u"orm['asklet.Question']"})
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
        u'asklet.treenode': {
            'Meta': {'unique_together': "(('parent', 'parent_answer', 'question'), ('domain', 'depth', 'best_splitter'))", 'object_name': 'TreeNode', 'index_together': "(('domain', 'parent', 'best_splitter'), ('domain', 'fresh'), ('domain', 'depth'))"},
            'best_splitter': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'depth': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tree_nodes'", 'to': u"orm['asklet.Domain']"}),
            'fresh': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['asklet.TreeNode']", 'null': 'True', 'blank': 'True'}),
            'parent_answer': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tree_nodes'", 'to': u"orm['asklet.Question']"}),
            'splitting_metric': ('django.db.models.fields.FloatField', [], {}),
            'targets': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['asklet.Target']", 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
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