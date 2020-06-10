DSD_META_MODEL = \
"""

DataSourceDefinition:
    '{'
        ((DSD_NAME_KW               ':'      def_name            = STRING                     )
        (MODEL_ID_KW                ':' '"'  model_id            = ID            '"'          )
        (MODEL_DESCRIPTION_KW       ':'      model_description   = STRING                     )
        (CAN_REFLECT_ON_WEB         ':'      can_reflect         = BOOL                       )
        (AUTHENTICATION_HEADER_KW   ':'      auth_header         = AuthenticationHeader       )?
        (ADDITIONAL_HEADERS_KW      ':' '['  additional_headers *= AdditionalHeader[',']  ']' )?
        (FIELDS_KW                  ':' '['  fields             += Field[',']             ']' )
        (APIS_KW                    ':' '['  apis                = Apis                   ']' )?)#[',']
    '}'
;
DSD_NAME_KW:                    /\"data-source-definition-name\"/ ;
MODEL_ID_KW:                    /\"model-id\"/ ;
MODEL_DESCRIPTION_KW:           /\"model-description\"/ ;
CAN_REFLECT_ON_WEB:             /\"can-reflect-on-web\"/ ;
FIELDS_KW:                      /\"fields\"/ ;
APIS_KW:                        /\"apis\"/ ;
////////////////////////////////////////////////////////////////////////////////////////////////////


AuthenticationHeader:
    '{' 
        ((AUTH_HEADER_NAME_KW   ':'  auth_header_name  = STRING  )
        (TOKEN_PREFIX_KW        ':'  token_prefix      = STRING  )
        (TOKEN_KW               ':'  token             = STRING  ))#[',']
    '}' 
;
AUTHENTICATION_HEADER_KW:   /\"authentication-header\"/ ;
AUTH_HEADER_NAME_KW:        /\"auth-header-name\"/ ;
TOKEN_PREFIX_KW:            /\"token-prefix\"/ ;
TOKEN_KW:                   /\"token\"/ ;
////////////////////////////////////////////////////////////////////////////////////////////////////


AdditionalHeader:
    '{'
        ((HEADER_NAME_KW    ':'  header_name  = STRING   )
        (HEADER_VALUE_KW    ':'  header_value = STRING   ))#[',']
    '}'
;
ADDITIONAL_HEADERS_KW:  /\"additional-headers\"/ ;
HEADER_NAME_KW:         /\"header-name\"/ ;
HEADER_VALUE_KW:        /\"header-value\"/ ;
////////////////////////////////////////////////////////////////////////////////////////////////////


Field: PrimaryKeyField | ForeignKeyField | DataField ;
PrimaryKeyField:
    '{'
        ((FIELD_NAME_KW             ':' '"' field_name              = ID       '"'  )
        (TYPE_KW                    ':' '"' type                    = Type     '"'  )
        (USE_AS_KW                  ':'     use_as = /\"primary-key\"/              )
        (RESPONSE_ONE_JSON_PATH_KW  ':'     response_one_json_path  = STRING        )?
        (RESPONSE_MUL_JSON_PATH_KW  ':'     response_mul_json_path  = STRING        )?)#[',']
    '}'
;
ForeignKeyField:
    '{'
        ((FIELD_NAME_KW              ':' '"' field_name              = ID        '"' )
        (TYPE_KW                     ':' '"' type                    = Type      '"' )
        (USE_AS_KW                   ':'     use_as = /\"foreign-key\"/              )
        (REF_FOREIGN_MODEL_ID_KW     ':' '"' ref_foreign_model_id    = ID        '"' )
        (REF_FOREIGN_FIELD_NAME_KW   ':' '"' ref_foreign_field_name  = ID        '"' )
        (RESPONSE_ONE_JSON_PATH_KW   ':'     response_one_json_path  = STRING        )?
        (RESPONSE_MUL_JSON_PATH_KW   ':'     response_mul_json_path  = STRING        )?)#[',']
    '}'
;
DataField:
    '{'
        ((FIELD_NAME_KW             ':' '"' field_name              = ID       '"'  )
        (TYPE_KW                    ':' '"' type                    = Type     '"'  )
        (USE_AS_KW                  ':'     use_as = /\"data\"/                     )
        (RESPONSE_ONE_JSON_PATH_KW  ':'     response_one_json_path  = STRING        )?
        (RESPONSE_MUL_JSON_PATH_KW  ':'     response_mul_json_path  = STRING        )?)#[',']
    '}'
;
FIELD_NAME_KW:                  /\"field-name\"/ ;
TYPE_KW:                        /\"type\"/ ;
USE_AS_KW:                      /\"use-as\"/ ;
RESPONSE_ONE_JSON_PATH_KW:      /\"response-one-json-path\"/ ;
RESPONSE_MUL_JSON_PATH_KW:      /\"response-multiple-json-path\"/ ;

REF_FOREIGN_MODEL_ID_KW:    /\"referenced-foreign-model-id\"/ ;
REF_FOREIGN_FIELD_NAME_KW:  /\"referenced-foreign-field-name\"/ ;
Type:                         INETGER_KW | FLAOT_KW | STRING_KW | BOOLEAN_KW ;
INETGER_KW: "INTEGER" ;
FLAOT_KW: "FLOAT" ;
STRING_KW: "STRING" ;
BOOLEAN_KW: "BOOLEAN" ;
////////////////////////////////////////////////////////////////////////////////////////////////////


Apis: (
    create           = CreateApi? 
    read_one         = ReadOneApi? 
    read_multiple    = ReadMultipleApi? 
    update           = UpdateApi? 
    delete           = DeleteApi?
)#[','] ;

CreateApi:
    '{'
        ((OPERATION_KW      ':'       /\"create\"/                               )
        (METHOD_KW          ':'  '"'  method        = Method  '"'                )
        (URL_MAP_KW         ':'       url_map       = STRING                     )
        (REF_MODELS_KW      ':'  '['  ref_models    *= ReferencedModel[','] ']'  )?)#[',']
    '}'
;
ReadOneApi:
    '{'
        ((OPERATION_KW      ':'       /\"read-one\"/                              )
        (METHOD_KW          ':'  '"'  method         = Method  '"'                )
        (URL_MAP_KW         ':'       url_map        = STRING                     )
        (REF_MODELS_KW      ':'  '['  ref_models    *= ReferencedModel[','] ']'   )?)#[',']
    '}'
;
ReadMultipleApi:
    '{'
        ((OPERATION_KW             ':'       /\"read-multiple\"/                             )
        (METHOD_KW                 ':'  '"'  method              = Method  '"'               )
        (URL_MAP_KW                ':'       url_map             = STRING                    )
        (REF_MODELS_KW             ':'  '['  ref_models         *= ReferencedModel[','] ']'  )?
        
        (PAGE_INDEX_UP_KW          ':'  '"'  page_index_url_placement       = ID        '"'  )
        (DEFAULT_PAGE_INDEX_KW     ':'       default_page_index             = NUMBER         )

        (PAGE_ROW_COUNT_UP_KW      ':'  '"'  page_row_count_url_placement   = ID        '"'  )
        (DEFAULT_PAGE_ROW_COUNT_KW ':'       default_page_row_count         = NUMBER         )

        (SEARCH_FIELDS_UP_KW       ':'  '"'  search_fields_url_placement    = ID        '"'  )
        (SEARCH_FIELDS_UD_KW       ':'       search_fields_url_delimiter    = STRING         )  
        
        (SEARCH_STRINGS_UP_KW      ':'  '"'  search_strings_url_placement   = ID        '"'  )
        (SEARCH_STRINGS_UD_KW      ':'       search_strings_url_delimiter   = STRING         )
        
        (SORT_FIELD_UP_KW          ':'  '"'  sort_field_url_placement       = ID        '"'  )
        (SORT_ORDER_UP_KW          ':'  '"'  sort_order_url_placement       = ID        '"'  ))#[',']
    '}'
;
UpdateApi:
    '{'
        ((OPERATION_KW   ':'       /\"update\"/                             )
        (METHOD_KW       ':'  '"'  method        = Method  '"'              )
        (URL_MAP_KW      ':'       url_map       = STRING                   )
        (REF_MODELS_KW   ':'  '['  ref_models   *= ReferencedModel[','] ']' )?)#[',']
    '}'
;
DeleteApi:
    '{'
        ((OPERATION_KW  ':'       /\"delete\"/                               )
        (METHOD_KW      ':'  '"'  method         = Method  '"'               )
        (URL_MAP_KW     ':'       url_map        = STRING                    )
        (REF_MODELS_KW  ':'  '['  ref_models   *= ReferencedModel[','] ']'  )?)#[',']
    '}'
;

OPERATION_KW:               /\"operation\"/ ;
METHOD_KW:                  /\"method\"/ ;
URL_MAP_KW:                 /\"url-map\"/ ;
REF_MODELS_KW:              /\"referenced-models\"/ ;

PAGE_INDEX_UP_KW:           /\"page-index-url-placement\"/ ;
DEFAULT_PAGE_INDEX_KW:      /\"default-page-index\"/ ;

PAGE_ROW_COUNT_UP_KW:       /\"page-row-count-url-placement\"/ ;
DEFAULT_PAGE_ROW_COUNT_KW:  /\"default-page-row-count\"/ ;

SEARCH_FIELDS_UP_KW:        /\"search-fields-url-placement\"/ ;
SEARCH_FIELDS_UD_KW:        /\"search-fields-url-delimiter\"/ ;

SEARCH_STRINGS_UP_KW:       /\"search-strings-url-placement\"/ ;
SEARCH_STRINGS_UD_KW:       /\"search-strings-url-delimiter\"/ ;

SORT_FIELD_UP_KW:           /\"sort-field-url-placement\"/ ;
SORT_ORDER_UP_KW:           /\"sort-order-url-placement\"/ ;

Method: 'GET' | 'POST' | 'PUT' | 'DELETE' ;
////////////////////////////////////////////////////////////////////////////////////////////////////


ReferencedModel:
    '{'
        ((MODEL_ID_KW        ':'  '"'  model_id       = ID     '"' )
        (FIELD_NAME_KW       ':'  '"'  field_name     = ID     '"' )
        (URL_PLACEMENT_KW    ':'  '"'  url_placement  = ID     '"' ))#[',']
    '}'
;
URL_PLACEMENT_KW:   /\"url-placement\"/ ;
////////////////////////////////////////////////////////////////////////////////////////////////////


Comment:
  /\/\/.*$/
;
"""