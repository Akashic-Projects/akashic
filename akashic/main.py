from akashic.rule_engine.interpreter import RulesInterpreter

from os.path import join, dirname

if __name__ == "__main__":

    i = RulesInterpreter()

    # Read rule from sample file
    this_folder = dirname(__file__)
    sample_path = join(this_folder, 'test_samples', 'sample2_alone.json')
    with open(sample_path, 'r') as sample:
        akashic_rule = sample.read()
        i.interpret(akashic_rule)