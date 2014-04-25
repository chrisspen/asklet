
YES = USUALLY = 4
PROBABLY = 3
SOMETIMES = PARTLY = 2
MAYBE = 1

NO = -4
RARELY = -2
DOUBTFUL = -1
DEPENDS = IRRELEVANT = 0

UNKNOWN = None

ANSWER_CHOICES = (
    (YES, 'yes/usually'),
    (PROBABLY, 'probably'),
    (SOMETIMES, 'sometimes/partly'),
    (MAYBE, 'maybe'),
    
    (NO, 'no'),
    (RARELY, 'rarely'),
    (DOUBTFUL, 'doubtful'),
    (DEPENDS, 'depends/irrelevant'),
    
    (UNKNOWN, 'unknown'),
)