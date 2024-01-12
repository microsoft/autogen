def download_spider(cache_dir: str) -> None:
    import os
    import zipfile

    # Not guaranteed to work indefinitely.
    cmd = f'mkdir -p {cache_dir}; cd {cache_dir}; curl --insecure -LOJ "https://drive.google.com/uc?export=download&id=1iRDVHLr4mX2wQKSgA9J8Pire73Jahh0m&confirm="'
    os.system(cmd)

    with zipfile.ZipFile(os.path.join(cache_dir, "spider.zip")) as zf:
        zf.extractall(cache_dir)
    assert os.path.isfile(os.path.join(cache_dir, "spider/train_spider.json"))


class SpiderEnv:
    def __init__(self, cache_dir: str = "~/.cache/spider", random_seed=666):
        import json
        import os
        import numpy as np

        # TODO: logger.
        self._rng = np.random.default_rng(random_seed)

        cache_dir = os.path.expanduser(cache_dir)
        self._db_dir = os.path.join(cache_dir, "spider/database")

        # Download and unzip the dataset if non-existent.
        data_file = os.path.join(cache_dir, "spider/train_spider.json")
        if not os.path.isfile(data_file):
            print(f"Downloading Spider dataset to {cache_dir}")
            download_spider(cache_dir)
        else:
            print(f"Loading cached Spider dataset from {cache_dir}")

        # TODO: Use other train & dev files.
        with open(data_file) as f:
            self._dataset = json.load(f)

        # Try to load every unique schema
        unique_db_ids = set(data["db_id"] for data in self._dataset)
        error_db_ids = []
        for db_id in unique_db_ids:
            schema = self._get_schema(db_id)
            if schema is None:
                error_db_ids.append(db_id)

        # Remove data with schema errors
        self._dataset = [
            data for data in self._dataset if data["db_id"] not in error_db_ids
        ]

    def _get_schema(self, db_id: str) -> str:
        import glob

        schema_files = glob.glob(f"{self._db_dir}/{db_id}/*.sql")
        if len(schema_files) == 0:
            print(f"Schema file not found for {self._db_dir}/{db_id}")
            return None
        if len(schema_files) > 1:
            print(f"Multiple schema files found for {self._db_dir}/{db_id}")
            return None

        try:
            with open(schema_files[0]) as f:
                # Extract all the "CREATE TABLE (...);" statements
                schema = ""
                in_create_table = False
                for line in f:
                    line = line.strip()
                    if "CREATE TABLE " in line.upper():
                        in_create_table = True
                    if in_create_table:
                        schema += line + "\n"
                    if ");" in line:
                        in_create_table = False
                schema = schema.replace("`", '"')
        except Exception as e:
            print(e)
            return None

        return schema

    def _run_query(self, db_id: str, query: str):
        import os
        import sqlite3

        con = sqlite3.connect(os.path.join(self._db_dir, f"{db_id}/{db_id}.sqlite"))
        cur = con.cursor()
        result, error = None, None

        try:
            result = cur.execute(query).fetchall()
        except Exception as e:
            error = str(e)

        return result, error

    def reset(self, k: int = None):
        if k is None:
            # Get a random question.
            self._k = self._rng.integers(len(self._dataset))  # TODO: Replacement?
        else:
            self._k = k

        data = self._dataset[self._k]
        db_id = data["db_id"]

        observation = {
            "observation": db_id,
            "instruction": data["question"],
            "feedback": None,
        }
        self._info = {
            "schema": self._get_schema(db_id),
            "gold_query": data["query"],
            "gold_result": self._run_query(db_id, data["query"])[0],
        }

        return observation, self._info

    def step(self, query: str):
        data = self._dataset[self._k]
        db_id = data["db_id"]

        result, error = self._run_query(db_id, query)

        if error is not None:
            reward = 0.0
        else:
            # TODO: Add another reward for query exact_set_match comparing with query_toks_no_value.
            reward = 1.0 if result == self._info["gold_result"] else 0.0

        observation = {
            "observation": db_id,
            "instruction": data["question"],
            "feedback": {"result": result, "error": error},
        }

        # TODO: Handle these.
        terminated, truncated = False, False

        return observation, reward, terminated, truncated, self._info
