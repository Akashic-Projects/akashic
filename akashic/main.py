from akashic.rule_engine.interpreter import RulesInterpreter

from akashic.data_sources.interpreter import DataSourceDefinitionInterpreter

from os.path import join, dirname

def test_rule_interpreter():
    i = RulesInterpreter()

    # Read rule from sample file
    this_folder = dirname(__file__)
    sample_path = join(this_folder, 'test_samples', 'rule_engine', 'sample1.json')
    with open(sample_path, 'r') as sample:
        akashic_rule = sample.read()
        i.interpret(akashic_rule)


def test_data_soruce_def_interpreter():
    dsdi = DataSourceDefinitionInterpreter()

    # Read rule from sample file
    this_folder = dirname(__file__)
    sample_path = join(this_folder, 'test_samples', 'data_sources', 'data_source1_full.json')
    with open(sample_path, 'r') as sample:
        dsd_string = sample.read()
        dsdi.load(dsd_string)
        dsdi.check_structure()

if __name__ == "__main__":
    test_data_soruce_def_interpreter()
   

