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
                    "{2}": "?data{3}"
                }}
            }}
        
        }}
    ]
}}

"""