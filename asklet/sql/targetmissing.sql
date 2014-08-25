/*
Finds targets that should exist but are missing.
*/
DROP VIEW IF EXISTS asklet_targetmissing CASCADE;
CREATE VIEW asklet_targetmissing
AS
SELECT  q.conceptnet_object AS target_slug,
        q.domain_id,
        q.language,
        q.pos,
        q.sense,
        q.text
FROM   asklet_question AS q
INNER JOIN asklet_domain AS d ON d.id = q.domain_id
LEFT OUTER JOIN asklet_target AS t ON
        t.conceptnet_subject = q.conceptnet_object
    AND t.domain_id = q.domain_id
WHERE   t.id IS NULL
    AND q.conceptnet_object IS NOT NULL
    AND (d.language IS NULL
        OR (q.language IS NOT NULL AND d.language = q.language))
    AND q.pos IS NOT NULL
    AND q.sense IS NOT NULL
    AND q.conceptnet_object IS NOT NULL
    AND q.conceptnet_object != '';