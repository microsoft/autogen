import os

from autogenstudio.datamodel import Agent, Skill
from autogenstudio.utils import utils


class TestUtilSaveSkillsToFile:

    def test_save_skills_to_file(self):

        # cleanup test work_dir
        try:
            os.system("rm -rf work_dir")
        except Exception:
            pass

        # Create two Agents, each with a skill
        skill_clazz = Skill(
            name="skill_clazz",
            description="skill_clazz",
            user_id="guestuser@gmail.com",
            libraries=["lib1.0", "lib1.1"],
            content="I am the skill clazz content",
            secrets=[{"secret": "secret_1", "value": "value_1"}],
            agents=[],
        )

        skill_dict = Skill(
            name="skill_dict",
            description="skill_dict",
            user_id="guestuser@gmail.com",
            libraries=["lib2.0", "lib2.1"],
            content="I am the skill dict content",
            secrets=[{"secret": "secret_2", "value": "value_2"}],
            agents=[],
        )

        Agent(skills=[skill_clazz])
        Agent(skills=[skill_dict])

        # test from flow
        skills = [skill_dict.__dict__, skill_clazz]

        utils.save_skills_to_file(skills, work_dir="work_dir")

        f = open("work_dir/skills.py", "r")
        skills_content = f.read()

        assert skills_content.find(skill_clazz.content)
        assert skills_content.find(skill_dict.content)

        # cleanup test work_dir
        try:
            os.system("rm -rf work_dir")
        except Exception:
            pass
