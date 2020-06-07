QUERY_RULE = \
"""
{{
    "rule-name": "__query_rule_{0}",
    "salience": "system",
    "run-once": false,
    "when": [
        {{ "?data<-": "[{1}]" }}
    ],
    "then": [
        {{ 
            "return": {{
                "tag": "query_return",
                "data": {{
                    "model_id": "{1}",
                    "{2}": "?data.{2}"
                }}
            }}
        
        }}
    ]
}}

"""