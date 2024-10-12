import os

from autogenstudio.datamodel import Skill
from autogenstudio.utils import utils


class TestUtilGetSkillsPrompt:

    def test_get_skills_prompt(self):

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

        skills = [skill_dict.__dict__, skill_clazz]

        prompt = utils.get_skills_prompt(skills, work_dir="work_dir")

        # test that prompt contains contents of skills class and dict
        assert prompt.find(skill_clazz.content) > 0
        assert prompt.find(skill_dict.content) > 0

        # test that secrets are set in environ
        assert os.getenv("secret_1") == "value_1"
        assert os.getenv("secret_2") == "value_2"

        # cleanup test work_dir
        try:
            os.system("rm -rf work_dir")
        except Exception:
            pass
