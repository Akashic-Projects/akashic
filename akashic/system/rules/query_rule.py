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
                    "field": "{2}",
                    "value": "?data.{2}",
                    "line_start": {3},
                    "col_start": {4},
                    "line_end": {5},
                    "col_end": {6}
                }}
            }}
        
        }}
    ]
}}

"""