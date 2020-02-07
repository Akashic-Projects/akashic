from textx import metamodel_from_file
from textx.export import metamodel_export, model_export

from os.path import join, dirname

from akashic.exceptions import SemanticMismatchError

class DataSourceDefinitionInterpreter(object):

    class ForeignIdSlotDef(object):
        def __init__(self):
            self.foreign_id_slot_name = None
            self.native_id_slot_name = None
            self.json_object_path = None
            self.slot_type = None

    class RegularSlotDef(object):
        def __init__(self):
            self.native_slot_name = None
            self.json_object_path = None
            self.slot_type = None

    class DataSourceDef(object):
        def __init__(self):
            self.data_source_name = None
            # self.data_source_definition_hashcode = None -> generated value
            self.template_name = None
            self.create_provider_api = None
            self.read_one_provider_api = None
            self.read_multiple_provider_api = None
            self.update_provider_api = None
            self.delete_provider_api = None

            self.native_id_slot_name = None
            self.foreign_id_slot_defs = {}

            self.regular_slot_defs = {}


    class DSGroupDef(object):
        def __init__(self):
            self.group_name = None
            self.data_sources = {}

    def __init__(self):
        processors = {
            'LogicExpression': self.logic_expression,
            'CompExpression': self.comp_expression,
            'PlusMinusExpr': self.plus_minus_expr,
            'MulDivExpr': self.mul_div_expr,
            'SqrExpr': self.sqr_expr,
            'Factor': self.factor,
            'DataLocator': self.data_locator,
        }

        this_folder = dirname(__file__)
        self.meta_model = metamodel_from_file(join(this_folder, 'meta_model.tx'), debug=False)
        self.meta_model.register_obj_processors(processors)

        self.ds_groups = {}


    def assamble_data_source(g):
        ds = DataSourceDef()
        ds.data_source_name = g.data_source_name
        ds.template_name = g.template_name

        ds.create_provider_api = g.create_provider_api
        ds.read_one_provider_api = g.read_one_provider_api
        ds.read_multiple_provider_api = g.read_multiple_provider_api
        ds.update_provider_api = g.update_provider_apis
        ds.delete_provider_api = g.delete_provider_api

        ds.native_id_slot_name = g.native_id_slot_name
        ds.foreign_id_slot_defs = {}
        ds.regular_slot_defs = {}

        for s in g.foreign_id_slot_defs:
            fisd = ForeignIdSlotDef()
            fisd.foreign_id_slot_name = s.foreign_id_slot_name
            fisd.native_id_slot_name = s.native_id_slot_name
            fisd.json_object_path = s.json_object_path
            fisd.slot_type = s.slot_type
            ds.foreign_id_slot_defs[fisd.native_id_slot_name] = fisd

        for s in g.regular_slot_defs:
            rsd = RegularSlotDef()
            rsd.native_slot_name = s.native_slot_name
            rsd.json_object_path = s.json_object_path
            rsd.slot_type = s.slot_type
            ds.regular_slot_defs[rsd.native_slot_name] = rsd
    
        return ds


    def interpret_and_add_data_source_group(self, data_source_group_def):
        data = self.meta_model.model_from_str(data_source_group_def)
        
        if data.model.__class__.__name__ != "DataSourcesGroup":
            raise SemanticMismatchError

        dsg = DSGroupDef()
        dsg.group_name = data.model.group_name
        dsg.data_sources = {}
        
        for g in data.model.data_sources:
            ds = assamble_data_source(g)
            dsg.data_sources[ds.data_source_name] = ds
        self.ds_groups[dsg.group_name] = dsg


    def interpret_and_add_data_source(self, data_sources_def):
        data = self.meta_model.model_from_str(data_sources_def)

        if data.model.__class__.__name__ != "DataSourceAlone":
            raise SemanticMismatchError

        ds = assamble_data_source(data.model)
        target_group_name = data.model.data_source_group_name
        
        if target_group_name not in self.ds_groups:
            dsg = DSGroupDef()
            dsg.group_name = target_group_name
            dsg.data_sources = {}
            self.ds_groups[target_group_name] = dsg

        self.ds_groups[target_group_name].data_sources[ds.data_source_name] = ds
    
