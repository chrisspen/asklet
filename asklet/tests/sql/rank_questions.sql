
--select count(*) from asklet_target where domain_id=2
/*
0.13
select -((10/1000.)*log(2,10/1000.)+(10/1000.)*log(2,10/1000.)+(10/1000.)*log(2,980/1000.))

0.0
select -((1000/1000.)*log(2,1000/1000.))

1.0
select -((500/1000.)*log(2,500/1000.)+(500/1000.)*log(2,500/1000.))
*/

/*
select
m.question_id,
-((500/m.total_count)*log(2,500/m.total_count)+(500/m.total_count)*log(2,500/m.total_count))
from (
select q.id as question_id,
sum(tqw.weight) as weight_sum,
count(tqw.target_id) as target_count,
(select count(*) from asklet_target where domain_id=2)::float as total_count

from asklet_question as q
--left outer join asklet_target as t on t.domain_id = q.domain_id
left outer join asklet_targetquestionweight as tqw on
	tqw.question_id = q.id
	--and tqw.target_id = t.id
	--and tqw.weight is not null
where q.domain_id=2
group by q.id
--order by weight_sum
) as m
*/

select
m.question_id,
q.slug,
abs(m.weight_sum + ((m.total_count - m.target_count)*-4)) as weight_sum_abs,
m.target_count,
m.total_count
from (
	select q.id as question_id,
	sum(tqw.weight) as weight_sum,
	count(tqw.target_id) as target_count,
	(select count(*) from asklet_target where domain_id=2) as total_count

	from asklet_question as q
	left outer join asklet_targetquestionweight as tqw on
		tqw.question_id = q.id
		--and tqw.weight is not null
	where q.domain_id=2
	group by q.id
	
) as m
inner join asklet_question as q on q.id = m.question_id
order by weight_sum_abs
