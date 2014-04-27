/*
2014.4.27 CKS
Lists all table sizes.
*/
DROP VIEW IF EXISTS asklet_targetrankings CASCADE;
CREATE OR REPLACE VIEW asklet_targetrankings
AS
SELECT  s.id AS session_id,
        t.id AS target_id,
        --,tqw.question_id
        --,tqw.weight
        --,tqw.count
        --,(tqw.weight::float/tqw.count) as them
        --,a.answer as us
        SUM(((tqw.weight::float/tqw.count)*a.answer-1+ABS((tqw.weight::float/tqw.count)*a.answer))/ABS((tqw.weight::float/tqw.count)*a.answer-1+ABS((tqw.weight::float/tqw.count)*a.answer))*ABS((tqw.weight::float/tqw.count)+a.answer)/2.) AS rank
FROM    asklet_session as s
LEFT OUTER JOIN asklet_answer AS a ON
        a.session_id = s.id
    AND a.guess_id IS NULL
LEFT OUTER JOIN asklet_question AS q ON q.id = a.question_id
LEFT OUTER JOIN asklet_targetquestionweight AS tqw ON
        a.question_id IS NOT NULL
    AND a.question_id = tqw.question_id
LEFT OUTER JOIN asklet_target AS t on
        t.id = tqw.target_id
GROUP BY
        s.id,
        t.id;