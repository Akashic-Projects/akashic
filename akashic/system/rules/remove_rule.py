REMOVE_RULE = 
"""
{
    "rule-name": "__remove_rule",
    "salience-override": 100001,
    "when": [
        { "clips": "$rtr <- (__RuleToRemove)"}
    ],
    "then": [
        { "clips": "(undefrule $rtr->rule_name)" },
        { "clips": "(retract $rtr)"}
    ]
}

"""