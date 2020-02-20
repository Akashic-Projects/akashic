from akashic.arules.interpreter import RulesInterpreter
from akashic.adss.data_provider import DataProvider
from akashic.adss.env_provider import EnvProvider

from os.path import join, dirname, abspath
import json


def test_rule_interpreter():
    i = RulesInterpreter()

    # Read rule from sample file
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'arules', 'sample1.json'))
    with open(sample_path, 'r') as sample:
        akashic_rule = sample.read()
        i.interpret(akashic_rule)


def test_data_soruce_def_interpreter():
    data_provider = DataProvider()

    # Read rule from sample file
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'adss', 'user_dsd.json'))
    with open(sample_path, 'r') as sample:
        dsd_string = sample.read()
        data_provider.load(dsd_string)
        data_provider.setup()

        url_map = "http://localhost:80/api/users/{user_id}/courses/{id}"
        url = data_provider.fill_url_map(url_map, user_id=10, id=40)
        print(f"Filled url:\n{str(url)}\n")

        clips_template = data_provider.generate_clips_template()
        print(f"Generated tempalte:\n{str(clips_template)}\n")

        response = data_provider.read_one(id=1)
        print(f"Response:\n{str(json.dumps(response))}\n")

        clips_fact = data_provider.generate_clips_fact(use_json_as="response", operation="read-one", json_object=response)
        print(f"Generated clips fact:\n{str(clips_fact)}\n")


        ep = EnvProvider()
        r1 = ep.define_template(clips_template)
        print(f"Template define response:\n{str(r1)}\n")
        r2 = ep.insert_fact(clips_fact)
        print(f"Fact insert response:\n{str(r2)}\n")

        # TODO: Create service for user creation
        # data_provider.create(json.loads("{\"name\": \"Lazar\", \"email\": \"lazar@gmail.com\"}"))

        rm = data_provider.read_multiple()
        print(f"Response:\n{str(json.dumps(rm))}\n")

        # TODO: API Key to make initial setup-request to akashic server
        # Akashic server is anonymous entity, encrypted and safe. -> Koristi zero knowledge sistem
        # Connection flow for one session:
            # First time: Setup request (send API key, get secret key, get session token - needs to be refreshed)
            
            # Send secret key, to start new session (get session token)
            
            # Send session token with all of those:
                # Define datasources (optional, may be already defined)
                # Provide 'superuser' api token to akashic server and refresh-token-api url
                # Create rules
                # Get assistance for making rules
                # Execute rules

        # How is data encrypted in database?
        # Enable user to ligin to account?
        # No anonymous!

if __name__ == "__main__":
    test_data_soruce_def_interpreter()
   

