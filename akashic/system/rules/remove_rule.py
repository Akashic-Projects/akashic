REMOVE_RULE = \
"""
{
    "rule-name": "__remove_rule",
    "salience": "system",
    "when": [
        { "clips": "?rtr <- (__RuleToRemove)"}
    ],
    "then": [
        { "clips": "(undefrule ?rtr->rule_name)" },
        { "clips": "(retract ?rtr)"}
    ]
}

"""