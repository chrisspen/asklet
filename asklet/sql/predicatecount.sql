DROP VIEW IF EXISTS asklet_predicatecount CASCADE;
CREATE OR REPLACE VIEW asklet_predicatecount
AS
SELECT  domain_id,
        conceptnet_predicate,
        COUNT(*) AS cnt
FROM    asklet_question
GROUP BY domain_id, conceptnet_predicate
ORDER BY cnt DESC;