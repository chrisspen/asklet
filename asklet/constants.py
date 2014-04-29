
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

SQL = 'sql'
BACKENDS = (
    SQL,
)

PYTHON = 'python'
RANKERS = (
    SQL,
    PYTHON,
)

CLOSED = 'closed'
OPEN = 'open'

ASSUMPTION_CHOICES = (
    (CLOSED, 'closed'),
    (OPEN, 'open'),
)

# Learns faster initially, but takes longer converge.
# Works best when weight connections are established but there are
# a lot of sparse values indicating NO.
# e.g. Your domain represents all known YES beliefs and has
# few or no explicit NO beliefs.
CWA_WEIGHT = NO

# Learns slower initially, but tends to be more thorough.
OWA_WEIGHT = DEPENDS
