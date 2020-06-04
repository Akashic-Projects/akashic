
RULE_TO_REMOVE = \
"""
{
    "data-source-definition-name": "__RuleToRemove",
    "model-id": "__RuleToRemove",
    "model-description": "System DSD for marking rules to be removed.",
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