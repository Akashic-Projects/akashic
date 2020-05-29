from akashic.arules.transpiler import Transpiler

from akashic.ads.data_provider import DataProvider
from akashic.ads.env_provider import EnvProvider

from akashic.bridges.data_bridge import DataBridge
from akashic.bridges.time_bridge import TimeBridge

from os.path import join, dirname, abspath
import json



def test_data_provider():
    data_provider = DataProvider()

    # Read rule from sample file
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'ads', 'user_dsd.json'))
    with open(sample_path, 'r') as sample:
        dsd_string = sample.read()
        data_provider.load(dsd_string)
        data_provider.setup()

        url_map = "http://localhost:80/api/users/{user_id}/courses/{id}"
        url = data_provider.fill_data_map(url_map, user_id=10, id=40)
        print(f"Filled url:\n{str(url)}\n")

        # TODO: Fix this
        # Do we need this to be done every time? No!
        clips_template = data_provider.generate_clips_template()
        print(f"Generated tempalte:\n{str(clips_template)}\n")

        response = data_provider.read_one(id=1)
        print(f"Response:\n{str(json.dumps(response))}\n")

        #clips_fact = data_provider.generate_clips_fact(use_json_as="response", operation="read-one", json_object=response)
        clips_fact = data_provider.generate_one_clips_fact(response)
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


        # TODO: Where should data_checker stand?
        clips_facts = data_provider.generate_multiple_clips_facts(rm, 5)
        for f in clips_facts:
            print(f"Generated clips fact:\n{str(f)}\n")

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


def test_rule_transpiler():
    
    # Setup User data provider
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'ads', 'user_dsd.json'))

    dsd_string = None
    with open(sample_path, 'r') as sample:
        dsd_string = sample.read()

    user_data_provider = DataProvider()
    user_data_provider.load(dsd_string)
    user_data_provider.setup()

    # Setup Course data provider
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'ads', 'course_dsd.json'))

    dsd_string = None
    with open(sample_path, 'r') as sample:
        dsd_string = sample.read()

    course_data_provider = DataProvider()
    course_data_provider.load(dsd_string)
    course_data_provider.setup()

    # Create CLIPS env_provider
    env_provider = EnvProvider([user_data_provider, course_data_provider])
    
    # Insert COURSE tempalte
    course_template = course_data_provider.generate_clips_template() 
    env_provider.define_template(course_template)

    # Insert USER tempalte
    user_template = user_data_provider.generate_clips_template() 
    env_provider.define_template(user_template)

    # Setup akashic transpiler
    transpiler = Transpiler(env_provider)

    # Load Akashic rule
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'arules', 'test_test.json'))
    with open(sample_path, 'r') as sample:
        akashic_rule = sample.read()
        transpiler.load(akashic_rule)

    # Print transpiled LHS commands
    print("\n----------------")
    print("Transpiled Rule:")
    print()
    print(transpiler.tranpiled_rule)        
    print()

    # Insert transpiled rule in env_provider
    env_provider.insert_rule(transpiler.tranpiled_rule)


    #####  1. TEST OF THE SYSTEM

    # Read users from DS
    multiple_courses = course_data_provider.read_multiple()
    # Generate CLIPS facts from JSON objects
    course_clips_facts = course_data_provider.generate_multiple_clips_facts(multiple_courses, 5)
    # Insert CLIPS facts in env_provider
    for u in course_clips_facts:
        env_provider.insert_fact(u)


    # env_provider.env.eval("(undefrule Test_count_rule)")


    # Run CLIPS engine
    env_provider.run()

    # print("\n")
    # print("RULES: ")
    # print("-------------------------")
    # for r in env_provider.env.rules():
    #     print(r)
    #     print("+++++++++++++++++++++++++")
       


if __name__ == "__main__":
    #test_data_provider()

    test_rule_transpiler()