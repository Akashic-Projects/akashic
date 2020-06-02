
RULE_TO_BLOCK = \
"""
{
    "data-source-definition-name": "__RuleToBlock",
    "model-name": "__RuleToBlock",
    "model-description": "System DSD for marking rules to be blocked from running.",
    "can-reflect-on-web": false,
    "fields": [
        {
            "field-name": "rule_name",
            "type": "STRING",
            "use-as": "primary-key"
        }
    ]
}
"""