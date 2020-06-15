UNBLOCK_RULE = \
"""
{{
    "rule-name": "__unblock_rule_{0}",
    "salience": "system",
    "run-once": true,
    "when": [
        {{ "clips": "?rtb <- (__RuleToBlock (rule_name ?rn&: (= (str-compare ?rn {1}) 0) ))" }}
    ],
    "then": [
        {{ "clips": "(retract ?rtb)" }}
    ]
}}

"""