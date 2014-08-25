/*
Finds all edges with senseless subjects or objects.

Note, you can aggregate this view, grouping by subject0 and predicate0.
If the associated count is 1, there's effectively no ambiguity and these
edges can be automatically created.

Groupings with counts higher than 1 will need to undergo
word-sense-disambiguation to determine which senses are appropriate.
In some cases, multiple sense may be relevant to the same word, but for
simplicity, we may choose to assume only one is relevant.
*/
DROP VIEW IF EXISTS asklet_conceptnetuntagged CASCADE;
CREATE VIEW asklet_conceptnetuntagged
AS
SELECT  t1.domain_id,
        tqw1.id AS weight_id,
        t1.conceptnet_subject AS subject0,
        t2.conceptnet_subject AS subject1,
        q1.conceptnet_predicate AS predicate0,
        q1.conceptnet_object AS object0,
        t3.conceptnet_subject AS object1
FROM    asklet_targetquestionweight AS tqw1
INNER JOIN asklet_target AS t1 ON t1.id = tqw1.target_id
    AND tqw1.disambiguated IS NULL
    AND t1.sense IS NULL
    AND t1.pos IS NULL
INNER JOIN asklet_question AS q1 ON q1.id = tqw1.question_id
    AND q1.sense IS NULL
    AND q1.pos IS NULL
    
-- Attach unambigous targets.
LEFT OUTER JOIN asklet_target AS t2 ON
        t2.sense IS NOT NULL
    AND t2.domain_id = t1.domain_id
    AND t2.language = t1.language
    AND t2.word = t1.word
LEFT OUTER JOIN asklet_target AS t3 ON
        t3.sense IS NOT NULL
    AND t3.domain_id = t1.domain_id
    AND t3.language = q1.language
    AND t3.word = q1.word
    
/*
An attempt to exclude all that already have a weight created.
This is inefficient, and triples the execution time.
*/
LEFT OUTER JOIN asklet_question AS q22 ON 
        q22.domain_id = t1.domain_id
    AND q22.conceptnet_predicate = q1.conceptnet_predicate
    AND q22.conceptnet_object = t3.conceptnet_subject
LEFT OUTER JOIN asklet_targetquestionweight AS tqw2 ON
        tqw2.question_id = q22.id
    AND tqw2.target_id = t2.id

WHERE   t2.id IS NOT NULL
    AND tqw2.id IS NULL
    AND t3.id IS NOT NULL;

--and q1.conceptnet_predicate = '/r/IsA'
--limit 10
