from akashic.arules.interpreter import RulesInterpreter
from akashic.adsds.interpreter import DataSourceDefinitionInterpreter

from os.path import join, dirname, abspath

def test_rule_interpreter():
    i = RulesInterpreter()

    # Read rule from sample file
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'arules', 'sample1.json'))
    with open(sample_path, 'r') as sample:
        akashic_rule = sample.read()
        i.interpret(akashic_rule)


def test_data_soruce_def_interpreter():
    dsdi = DataSourceDefinitionInterpreter()

    # Read rule from sample file
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'adsds', 'data_source1_full.json'))
    with open(sample_path, 'r') as sample:
        dsd_string = sample.read()
        dsdi.load(dsd_string)
        dsdi.check_url_mappings()

        url_map = "http://localhost:80/api/users/{user_id}/courses/{id}"
        r = dsdi.fill_url_map(url_map, user_id=10, id=40)
        print("Filled url: " + str(r))

        r = dsdi.generate_clips_template()
        print("Generated tempalte: \n" + str(r))

if __name__ == "__main__":
    test_data_soruce_def_interpreter()
   

