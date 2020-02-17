from akashic.arules.interpreter import RulesInterpreter
from akashic.adss.data_provider import DataProvider
from akashic.adss.env_provider import EnvProvider

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
    dsdi = DataProvider()

    # Read rule from sample file
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'adss', 'user_dsd.json'))
    with open(sample_path, 'r') as sample:
        dsd_string = sample.read()
        dsdi.load(dsd_string)
        dsdi.setup()

        url_map = "http://localhost:80/api/users/{user_id}/courses/{id}"
        url = dsdi.fill_url_map(url_map, user_id=10, id=40)
        print(f"Filled url:\n{str(url)}\n")

        clips_template = dsdi.generate_clips_template()
        print(f"Generated tempalte:\n{str(clips_template)}\n")

        response = dsdi.read_one(id=1)
        print(f"Response:\n{str(response)}\n")

        clips_fact = dsdi.generate_clips_fact(use_json_as="response", operation="read-one", json_string=response)
        print(f"Generated clips fact:\n{str(clips_fact)}\n")

        ep = EnvProvider()
        r1 = ep.define_template(clips_template)
        print(f"Template define response:\n{str(r1)}\n")

        r2 = ep.insert_fact(clips_fact)
        print(f"Fact insert response:\n{str(r2)}\n")

if __name__ == "__main__":
    test_data_soruce_def_interpreter()
   

