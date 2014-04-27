/*

sign = 
    
    return (them*us-1+abs(them*us))/abs(them*us-1+abs(them*us))*abs(them+us)/2.
*/

select 1/cast(2 as float)

select * from asklet_targetrankings where session_id=1607 order by rank desc

select s.id as session_id,
t.id as target_id, t.slug
--,tqw.question_id
--,tqw.weight
--,tqw.count
--,(tqw.weight::float/tqw.count) as them
--,a.answer as us
,SUM(((tqw.weight::float/tqw.count)*a.answer-1+abs((tqw.weight::float/tqw.count)*a.answer))/abs((tqw.weight::float/tqw.count)*a.answer-1+abs((tqw.weight::float/tqw.count)*a.answer))*abs((tqw.weight::float/tqw.count)+a.answer)/2.) as rank
from asklet_session as s
left outer join asklet_answer as a on
	a.session_id = s.id
	and a.guess_id is null
left outer join asklet_targetquestionweight as tqw on
	a.question_id is not null and a.question_id = tqw.question_id

left outer join asklet_target as t on
	t.id = tqw.target_id

where 1=1
and s.id = 1607
--limit 100
group by s.id, t.id, t.slug
order by rank desc