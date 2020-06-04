from akashic.arules.transpiler import Transpiler

from akashic.ads.data_provider import DataProvider
from akashic.ads.env_provider import EnvProvider

from akashic.bridges.data_bridge import DataBridge
from akashic.bridges.time_bridge import TimeBridge

from os.path import join, dirname, abspath
import json

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
    

    # Setup akashic transpiler
    transpiler = Transpiler(env_provider)


    # Load Akashic rule
    
    # time_return
    # rhs_create
    # simple_return
    # run_once
    # rhs_update
    # rhs_update_pure
    this_folder = dirname(__file__)
    sample_path = abspath(join(this_folder, '..', 'test', 'samples', 'arules', 'rhs_update.json'))
    with open(sample_path, 'r') as sample:
        akashic_rule = sample.read()
        transpiler.load(akashic_rule)

    # Print transpiled LHS commands
    print("\n----------------")
    print("Transpiled Rule:")
    print()
    print(transpiler.tranpiled_rule)
    print("\n----------------")
    print("\n")

    # Insert transpiled rule in env_provider
    env_provider.insert_rule(transpiler.rule.rule_name, transpiler.tranpiled_rule)


    #####  ADD FACTS FROM THE WEB

    # Read users from DS
    multiple_courses = course_data_provider.read_multiple()
    # Generate CLIPS facts from JSON objects
    course_clips_facts = course_data_provider.generate_multiple_clips_facts(multiple_courses, 5)
    # Insert CLIPS facts in env_provider
    for u in course_clips_facts:
        env_provider.insert_fact(u)


    ###### RUN CLIPS ENGINE

    # Run CLIPS engine
    env_provider.run()

    print("\n")
    print("RULES: ")
    print("-------------------------START")
    for r in env_provider.env.rules():
        print(r)
        print("-------------------------END")

    print("\n")
    print("FACTS: ")
    print("-------------------------START")
    for f in env_provider.env.facts():
        print(f)
        print("-------------------------END")


    # Run CLIPS engine
    env_provider.run()

    print("\n")
    print("RULES: ")
    print("-------------------------START")
    for r in env_provider.env.rules():
        print(r)
        print("-------------------------END")

    print("\n")
    print("FACTS: ")
    print("-------------------------START")
    for f in env_provider.env.facts():
        print(f)
        print("-------------------------END")
       


if __name__ == "__main__":
    #test_data_provider()

    test_rule_transpiler()