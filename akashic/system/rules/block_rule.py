BLOCK_RULE = 
"""
{
    "rule-name": "__block_rule",
    "salience-override": 100000,
    "run-once": true,
    "when": [
    ],
    "then": [
        { "clips": "(assert (__RuleToBlock (rule_name "{0}")))" }
    ]
}

"""