UNBLOCK_RULE = 
"""
{
    "rule-name": "__unblock_rule",
    "salience-override": 100000,
    "run-once": true,
    "when": [
        { "clips": "$rtb <- (__RuleToBlock (rule_name ?rn&: (= (str-compare ?rn {0}) 0) ))"}
    ],
    "then": [
        { "clips": "(retract $rtb)"}
    ]
}

"""