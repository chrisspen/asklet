/*
Indicates how often the part-of-speech of the subject matches
the object for each predicate.
*/
DROP VIEW IF EXISTS asklet_pospolarity;
CREATE VIEW asklet_pospolarity
AS
select m.*, m.cnt_same::float/m.cnt as same_ratio
from (
select  t.domain_id,
        q.conceptnet_predicate as predicate,
        count(*) as cnt,
        count(case when t.pos = q.pos then 1 else null end) as cnt_same
from asklet_targetquestionweight as w
inner join asklet_target as t on t.id=w.target_id
    and t.pos is not null
inner join asklet_question as q on q.id=w.question_id
    and q.pos is not null
group by t.domain_id, q.conceptnet_predicate
) as m;