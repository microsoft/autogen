import os
import json
from autogen import oai
from autogen.math_utils import eval_math_responses, get_answer
import time
from utils import load_samples, write_json, mylogger
from agentchat import AgentChat
from langchain_react import ReAct
from answer_checker import AnswerChecker
from functools import partial
from copy import deepcopy
import signal
import os
from multi_agent_debate.interactive import Debate
import json


def solve_problems(problem_set, saving_folder, solver_function, checker=None):
    """Solve a set of problems
    Args:
        problem_set (list): a list of problems
        saving_folder (str): the result folder to save the solved problems, the category folder will be created inside
        solver_function (function): the solver function to solve one problem, take a problem dict as input and return a result dict

    Returns:
        None
    """
    if len(problem_set) == 0:
        return
    os.makedirs(saving_folder, exist_ok=True)
    logger = mylogger(os.path.join(saving_folder, "log.txt"))

    stars = "*" * 80
    done_problems = set(
        [int(f.split(".")[0]) for f in os.listdir(saving_folder) if "json" in f]
    )  # from the saving folder load solved problems
    correct_counts = 0

    for i, problem in enumerate(problem_set):
        # update problem
        problem = {k: problem[k] for k in ["problem", "level", "type", "solution", "correct_ans"]}
        problem["problem_id"] = str(i)  # assign problem id

        # check if problem is already solved
        problem_path = os.path.join(saving_folder, str(i) + ".json")
        if int(problem["problem_id"]) in done_problems:
            continue

        # solve problem
        result = solver_function(problem)
        problem.update(result)

        # check answer
        if checker is not None:
            checker_result = checker.check_answer(problem["problem"], problem["response_with_ans"], problem["correct_ans"])
            problem.update(checker_result)
            correct_counts += problem["is_correct"]
            logger.log(
                f"{stars}\nProblem {i} | Is_correct {problem['is_correct']} | Correct Answer: {problem['correct_ans']}\n\nReply: {problem['response_with_ans']}\n%%%%%%%\nCheck: {problem['check_result']}\n{stars}\n"
            )
        else:
            logger.log(
                f"{stars}\nProblem {i} | Correct Answer: {problem['correct_ans']}\n\nReply: {problem['response_with_ans']}\n{stars}\n"
            )

        # save and print
        problem["trial"] = -1
        write_json(problem, problem_path)

        # exit()
        

    logger.log(f" Accuracy: {correct_counts}/{len(problem_set)} = {correct_counts/len(problem_set)}")
    logger.log("------------------------------------------------------------\n", verbose=True)


import datasets
def load_math_test(num_samples=1):
    data = datasets.load_dataset("competition_math")
    test_data = data["test"]
    test_data = [test_data[x] for x in range(len(test_data))]
    num_samples = len(test_data) if num_samples < 0 else num_samples
    # print(f"++++Length of test data: {len(test_data)}, num problem loaded: {num_samples}++++")
    assert "How many vertical asymptotes does" in test_data[0]["problem"]
    assert "What is the positive difference between $120\\%$" in test_data[1]["problem"]
    if num_samples > 0:
        return test_data[:num_samples]
    return test_data

def solve_problem_with_multiple_solvers(problem, solvers_with_paths, checker=None):
    """Solve a single problem using multiple solvers and save the results
    Args:
        problem (dict): a problem in dictionary format
        solvers (list): a list of solver functions
        paths (list): a list of saving folders corresponding to solvers
        checker (function, optional): a function to check the correctness of the solution

    Returns:
        None
    """
    stars = "*" * 80
    # Iterate through all solvers and corresponding paths
    start = time.time()
    for solver, path, name in solvers_with_paths:
        
        # Make directory if not exists
        os.makedirs(path, exist_ok=True)
        
        # Initialize logger (assuming mylogger function is defined in your code)
        logger = mylogger(os.path.join(path, "log.txt"))
        
        # Check if problem is already solved
        problem_path = os.path.join(path, f"{problem['problem_id']}.json")
        if os.path.exists(problem_path):
            continue


        print(f"Start solving problem {problem['problem_id']} with {name}", flush=True)
        # Solve the problem using the solver
        result = solver(problem)
        
        # Update problem with the result
        tmp_problem = deepcopy(problem)
        tmp_problem.update(result)
        
        # Check the answer if checker is available
        if checker is not None:
            print(f"Start checking problem {tmp_problem['problem_id']} solved with {name}", flush=True)
            checker_result = checker.check_answer(
                tmp_problem["problem"], tmp_problem["response_with_ans"], tmp_problem["correct_ans"]
            )
            tmp_problem.update(checker_result)
            
            logger.log(
                f"{stars}\nSolver: {name} | Problem {tmp_problem['problem_id']} | Is_correct {tmp_problem['is_correct']} | Correct Answer: {tmp_problem['correct_ans']}\n\nReply: {tmp_problem['response_with_ans']}\n%%%%%%%\nCheck: {tmp_problem['check_result']}\n{stars}\n"
            )
        else:
            logger.log(
                f"{stars}\nSolver: {name} | Problem {tmp_problem['problem_id']} | Correct Answer: {tmp_problem['correct_ans']}\n\nReply: {tmp_problem['response_with_ans']}\n{stars}\n"
            )
        
        # Save the problem
        tmp_problem["trial"] = -1
        write_json(tmp_problem, problem_path)
        # exit()

def solve_with_verifier(problem, solver_function, verifier_function):
    result = solver_function(problem)

    verify_result = verifier_function(problem["problem"], result["response_with_ans"])

    re_solve_count = 3
    re_check_count = 1
    while (
        (verify_result["state"] == "no_answer" or verify_result["state"] == "wrong")
        and re_solve_count > 0
        and re_check_count > 0
    ):
        if verify_result["state"] == "no_answer":
            verify_result = verifier_function(problem["problem"], result["response_with_ans"])
            re_check_count -= 1
            continue

        result = solver_function(problem)
        verify_result = verifier_function(problem["problem"], result["response_with_ans"])
        re_solve_count -= 1


def vanilla_solver(config_list, problem):
    
    llm_config = {
        "model" : "gpt-4",
        "config_list": config_list,
        "seed": 42,
        "request_timeout": 600,
    }
    messages =  [{"content": 'You are a helpful AI Assistant.', "role": "system"},
                 {"content": problem["problem"], "role": "user"}]
    
    def timeout_handler(signum, frame):
        raise Exception("Vanilla GPT-4 Timeout")

    start = time.time()
    signal.signal(signal.SIGALRM, timeout_handler)
    try:
        signal.alarm(800)
        responses = oai.ChatCompletion.create(
                context=messages[-1].pop("context", None), messages=messages, **llm_config
            )
        signal.alarm(0)
    except Exception as e:
        print(f"Got exception {e} when solving problem {problem['problem_id']}", flush=True)
        return {
            "response_with_ans": "Got exception when solving problem",
            "correct_ans": get_answer(problem["solution"]),
            "time": time.time() - start,
        }

    return {
        "response_with_ans": responses["choices"][0]["message"]['content'],
        "correct_ans": get_answer(problem["solution"]),
        "time": time.time() - start,
    }

def contains_asy_code(input_string):
    # patterns = ["\[asy\]", "\[ASY\]"]
    # for p in patterns:
    #     if p in input_string:
    #         return True
    if "[asy" in input_string or "[ASY" in input_string:
        return True
    return False


def multidebate(config_list, problem):
    def timeout_handler(signum, frame):
        raise Exception("multidebate Timeout")

    config = json.load(open(f"multi_agent_debate/code/utils/config4all.json", "r"))
    config['debate_topic'] = problem['problem']
    
    signal.signal(signal.SIGALRM, timeout_handler)
    try:
        signal.alarm(800)
        start = time.time()
        debate = Debate(num_players=3, config_list=config_list, config=config, temperature=1, sleep_time=0, model_name='gpt-4', max_round=15)
        debate.run()
        result = {
            "response_with_ans": debate.config['debate_answer'],
            "correct_ans": get_answer(problem["solution"]),
            "time": time.time() - start,
            "prompt_tokens": debate.prompt_token,
            "completion_tokens": debate.completion_token,
        }
        result.update(debate.config)
        del result['debate_topic']
        signal.alarm(0)
    except Exception as e:
        print(f"Got exception {e} when solving problem {problem['problem_id']}", flush=True)
        result = {
            "response_with_ans": "Got exception when solving problem",
            "correct_ans": get_answer(problem["solution"]),
            "time": time.time() - start,
        }
    
    return result

def pseudo_main(config_list, use_azure):
    samples = load_samples("./300problems/", num_samples=20)
    cate = samples.keys()
    checker = AnswerChecker(config_list=config_list)

    # # ---------------------------------------------------------------
    # run vanilla solver
    # vanilla_solver_function = partial(vanilla_solver, config_list)
    # for i, category in enumerate(cate):
    #     solve_problems(
    #         samples[category],
    #         f"./asy/vanilla_solver/" + category,
    #         solver_function=vanilla_solver_function,
    #         checker=checker,
    #     )

    # ---------------------------------------------------------------
    agentchat = AgentChat(config_list=config_list)
    for i, category in enumerate(cate):
        solve_problems(
            samples[category],
            f".results/agentchat/" + category,
            solver_function=agentchat.solve_one_problem,
            checker=checker,
        )

    # # # ---------------------------------------------------------------
    # run react
    # react = ReAct(config_list, use_azure)
    # print("Running ReAct on 120 problems with asy removed", flush=True)
    # for i, category in enumerate(cate):
    #     solve_problems(
    #         samples[category], 
    #         "./asy/asy_react_120/" + category, 
    #         solver_function=react.solve_one_problem, 
    #         checker=checker
    #     )
    # print("tar 120 problems", flush=True)
    # os.system("tar -czf all_problems.tar.gz all_problems full_run.out")

    # ---------------------------------------------------------------
    # run multi-agent debate
    # samples = load_samples("./300problems/", num_samples=20)
    # cate = samples.keys()
    # checker = AnswerChecker(config_list=config_list)

    # print("Running Multi-Agent Debate on 120 problems", flush=True)
    # for i, category in enumerate(cate):
    #     solve_problems(
    #         samples[category], 
    #         "./results/debate/" + category, 
    #         solver_function=partial(multidebate, config_list), 
    #         checker=checker
    #     )
    # print("tar 120 problems", flush=True)
    # os.system("tar -czf results.tar.gz results full_run.out")

