RULE_META_MODEL = \
"""

Rule:
    '{{'
        ((RULE_NAME_KW        ':' '"'  rule_name=ID  '"'            )
        (RULE_SALIENCE_KW     ':'      (salience=SYSTEM_SALIENCE_KW | 
                                        salience=INT)               )
        (RUN_ONCE_KW          ':'      run_once=BOOL                )?
        (lhs=LHS                                                    )
        (rhs=RHS                                                    ))#[',']
    '}}'
;

RULE_NAME_KW:        /\"rule-name\"/ ;
RULE_SALIENCE_KW:    /\"salience\"/ ;
SYSTEM_SALIENCE_KW:  /\"system"/ ;
RUN_ONCE_KW:         /\"run-once\"/ ;

LHS:
    WHEN_KW ':' '['
        statements *= LHSStatement[',']
    ']'
;

WHEN_KW:    /\"when\"/ ;


LHSStatement: 
    stat=SYMBOLIC_VAR | 
    stat=BINDING_VAR |
    stat=FACT_ADDRESS_VAR |
    stat=ASSERTION |
    stat=LHS_CLIPS_CODE
;

SYMBOLIC_VAR:
    '{{' 
        '"' var_name=/\?[^\d\W]\w*\\b/ '"' ':' 
        '"' expr=Root '"' 
    '}}'
;

BINDING_VAR:
    '{{' 
        '"' var_name=/\?[^\d\W]\w*\\b/ '=' '"' ':' 
        '"' expr=Root '"' 
    '}}'
;

FACT_ADDRESS_VAR:
    '{{' 
        '"' var_name=/\?[^\d\W]\w*\\b/ '<-' '"' ':' 
        '"' expr=SpecialSingularLogicExpression '"' 
    '}}'
;

ASSERTION:
    '{{' ASSERT_KW ':'
        '"' (expr=SpecialBinaryLogicExpression | 
             expr=TestSingularLogicExpression) '"' 
    '}}'
;


LHS_CLIPS_CODE:
    '{{' 
        CLIPS_KW ':' 
        clips_code=/(\")(.*)(\")/ 
    '}}'
;


ASSERT_KW:  /\"assert\"/ ;
CLIPS_KW:   /\"clips\"/ ;

PLUS_MINUS:     '+'     | '-'  ;
MUL_DIV:        '*'     | '/'  ;
SQR:            '^' ;
CMP:            '=='    | '!=' | '<' | '>' | '<=' | '>=' ;
LOGIC:          'and'   | 'or' ;
NOT:            'not' ;

EXISTS:         'exists' ;
FORALL:         'forall' ;
TEST:           'test' ;

COUNT:          'count' ;
STR:            'str' ;
NOW:            'now' ;
TIME_TO_STR:    'time_to_str' ;
STR_TO_TIME:    'str_to_time' ;
SUB_TIMES:      'sub_times' ;


SPECIAL_SINGULAR: NOT | EXISTS | FORALL ;


SpecialBinaryLogicExpression:
    operands=SpecialSingularLogicExpression 
    (operator=LOGIC operands=SpecialSingularLogicExpression)*
;

SpecialSingularLogicExpression:
    (operator=SPECIAL_SINGULAR? '[' template=ID ']') |
    (operator=SPECIAL_SINGULAR? '[' operand=Root ']')
;

TestSingularLogicExpression:
    operator=TEST '[' operand=Root ']'
;


Root:
    LogicExpression |
    Function
;

// Always from less specific to more specific
Function:
    OnePlusArgFunction |
    OneArgFunction |
    ZeroArgFunction
;

ZeroArgFuncNames: 
    NOW {0}
;
OneArgFuncNames: 
    NOT | 
    COUNT | 
    STR {1}
;
OnePlusArgFuncNames: 
    TIME_TO_STR | 
    STR_TO_TIME |
    SUB_TIMES {2}
;

ZeroArgFunction:
    func_name=ZeroArgFuncNames LPAR RPAR
;
OneArgFunction:
    (func_name=COUNT '(' template=ID ')') |
    (func_name=OneArgFuncNames args=Factor)
;
OnePlusArgFunction:
    func_name=OnePlusArgFuncNames LPAR args=Factor COMMA args=Factor RPAR
;


LogicExpression:
    operands=CompExpression (operator=LOGIC operands=CompExpression)*
;

CompExpression:
    operands=PlusMinusExpr (operator=CMP operands=PlusMinusExpr)*
;

PlusMinusExpr:
    operands=MulDivExpr (operator=PLUS_MINUS operands=MulDivExpr)*
;

MulDivExpr:
    operands=SqrExpr (operator=MUL_DIV operands=SqrExpr)*
;

SqrExpr:
    operands=Factor (operator=SQR operands=Factor)*
;

Factor:
    (value=Function) |
    (value=STRICTFLOAT) |
    (value=INT) |
    (value=BOOL) |
    (value=STRING_C) |
    (value=LHSValueLocator) |
    (value=VARIABLE) |
    (value=DataLocator) |
    (LPAR value=LogicExpression RPAR) |
    (value=LogicExpression)
;

COMMA:  ',';
LPAR:   '(' ;
RPAR:   ')' ;
STRING_C: val=/(\')([^\']*)(\')/ ; //'
VARIABLE: var_name=/\?[^\d\W]\w*\\b/;

DataLocator: template_conn_expr=TEMPLATE_CONNECTION_EXPRESSION ('.' field=ID)  (is_query=/\?\?*\?/)? ;
TEMPLATE_CONNECTION_EXPRESSION: templates=ID ('~' templates=ID)* ;

LHSValueLocator:
    var_name=/\?[^\d\W]\w*\\b/ '.' field_name=ID ;


RHS:
    THEN_KW ':' '['
        statements*=RHSStatement[',']
    ']'
;

THEN_KW:    /\"then\"/ ;


RHSStatement:
    stat=CreateStatement | 
    stat=ReturnStatement | 
    stat=UpdateStatement | 
    stat=DeleteStatement |
    stat=RHS_CLIPS_CODE
;


CreateStatement:
    '{{' 
        CREATE_KW ':' '{{'
            ((MODEL_ID_KW       ':' '"' model_id    = ID   '"'    )
            (REFLECT_ON_WEB     ':'     reflect     = BOOL        )
            ( DATA_KW           ':'     json_object = JSONObject  ))#[',']
        '}}' 
    '}}'
;
CREATE_KW:       /\"create\"/ ;
MODEL_ID_KW:     /\"model-id\"/ ;
REFLECT_ON_WEB:  /\"reflect-on-web\"/ ;
DATA_KW:         /\"data\"/ ;


ReturnStatement:
    '{{' 
        RETURN_KW ':' '{{' 
            ((TAG_KW      ':'     tag          = STRING      )
            (DATA_KW      ':'     json_object  = JSONObject  ))#[',']
        '}}' 
    '}}'
;
RETURN_KW:    /\"return\"/ ;
TAG_KW:       /\"tag\"/ ;


UpdateStatement:
    '{{' 
        UPDATE_KW ':' '{{'
            ((MODEL_ID_KW       ':' '"' model_id     = ID   '"'    )
            (REFLECT_ON_WEB     ':'     reflect      = BOOL        )
            (DATA_KW            ':'     json_object  = JSONObject  ))#[',']
        '}}' 
    '}}'
;
UPDATE_KW:          /\"update\"/ ;
FACT_ADDRESS_KW:    /\"fact-address\"/ ;


DeleteStatement:
    '{{' 
        DELETE_KW ':' '{{'
            ((MODEL_ID_KW       ':' '"' model_id    = ID   '"'    )
            (REFLECT_ON_WEB     ':'     reflect     = BOOL        )
            ( DATA_KW           ':'     json_object = JSONObject  ))#[',']
        '}}'
    '}}'
;
DELETE_KW:  /\"delete\"/ ;


JSONObject:
    "{{" field_list*=FieldEntry[','] "}}"
;
FieldEntry:
    name=STRING ':' value=FieldValue
;
FieldValue:
    RHSValueLocator | RHS_VARIABLE | STRICTFLOAT | INT | BOOL | STRING 
;

RHSValueLocator:
    '"' var_name=/\?[^\d\W]\w*\\b/ '.' field_name=ID  '"';

RHS_VARIABLE: '"' var_name=/\?[^\d\W]\w*\\b/ '"';

RHS_CLIPS_CODE:
    '{{' 
        CLIPS_KW ':' 
        clips_code=/(\")(.*)(\")/ 
    '}}'
;


Comment:
  /\/\/.*$/
;

"""