/*
?s1 (?p1=isa ?o1) ?w1
?s2=?o1 (?p2 ?o2) ?w2
?w1*?w2 > 0.5
=>
?s1 ?p2 ?o2 ?w1*?w2
*/

select
t1.id as s1_id
,t1.slug as s1_slug
,q1.conceptnet_predicate as p1_slug
,q1.conceptnet_object as o1_slug
,tqw1.prob as w1

,t2.id as s2_id
,t2.slug as s2_slug
,q2.conceptnet_predicate as p2_slug
,q2.conceptnet_object as o2_slug
,tqw2.prob as w2

,tqw1.prob*tqw2.prob as w3
/*
    
    tqw2.conceptnet_predicate as p_slug,
    tqw2.conceptnet_object as z_slug,
    tqw1.prob*tqw2.prob as prob
    */
from asklet_targetquestionweight as tqw1
inner join asklet_target as t1 on t1.id = tqw1.target_id
inner join asklet_question as q1 on q1.id = tqw1.question_id

inner join asklet_target as t2 on t2.slug = q1.conceptnet_object
inner join asklet_targetquestionweight as tqw2 on tqw2.target_id = t2.id
inner join asklet_question as q2 on q2.id = tqw2.question_id

where 1=1
and t1.domain_id=2
and q1.conceptnet_predicate = '/r/IsA'
and tqw1.prob*tqw2.prob > 0.5
and t1.slug = '/c/en/cat'
--and t1.slug = '/c/en/feline'
--and t1.slug = '/c/en/animal'
limit 10

/*
select distinct conceptnet_predicate
from asklet_question
where domain_id=2
order by conceptnet_predicate
*/
