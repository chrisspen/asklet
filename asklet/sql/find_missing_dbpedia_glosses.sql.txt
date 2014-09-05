select t.id
from asklet_target as t
where t.id not in 
(
    select tqw.target_id
    from asklet_question as q
    inner join asklet_targetquestionweight as tqw on tqw.question_id=q.id
    and q.conceptnet_predicate='/dbpedia.org/ontology/abstract'
)
limit 10