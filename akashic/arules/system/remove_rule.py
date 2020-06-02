REMOVE_RULE = 
"""
{
    "rule-name": "Remove_rule",
    "salience-override": 100000,
    "when": [
        { "clips": "$tr <- (Rule_to_remove)"}
    ],
    "then": [
        { "clips": "***RETRACT COMMANDS, first rule, than fact" }
    ]
}

"""