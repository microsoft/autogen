import sqlite3
import datetime
import json

try:
    import openai
    from openai.types.chat import ChatCompletion
    ERROR = None
except ImportError:
    ERROR = ImportError("Please install openai>=1 and diskcache to use autogen.OpenAIWrapper.")


class Telemetry:
    def __init__(self):
        self.con = sqlite3.connect("telemetry.db")
        self.cur = self.con.cursor()
        query = """
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY,
                telemetry_id TEXT,
                request TEXT,
                response TEXT,
                is_cached INEGER,
                client_config TEXT,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME DEFAULT CURRENT_TIMESTAMP)
        """
        self.cur.execute(query)


    def _to_dict(self, obj):
        if isinstance(obj, (int, float, str, bool)):
            return obj
        elif isinstance(obj, dict):
            return {k: self._to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._to_dict(v) for v in obj]
        elif hasattr(obj, "__dict__"):
            return {k: self._to_dict(v) for k, v in vars(obj).items()}
        else:
            return obj


    def cleanup_config(self, d, keyword):
        if not isinstance(d, dict):
            return

        keys_to_remove = [key for key in d if keyword in key]
        for key in keys_to_remove:
            del d[key]

        for key, value in d.items():
            if isinstance(value, dict):
                self.cleanup_config(value, keyword)


    def insert(self, telemetry_id, request, response, is_cached, client_config, start_time):
        end_time = self.get_current_ts()

        if ERROR:
            raise ERROR

        if isinstance(response, ChatCompletion):
            response_messages = json.dumps(self._to_dict(response))
        elif isinstance(response, str):
            response_messages = json.dumps({'error': response})
        else:
            raise "invalid type of response"

        if self.con:
            # TODO: handle insert failure
            query = """INSERT INTO messages (
                telemetry_id, request, response, is_cached, client_config, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?)"""
            self.cur.execute(query, (
                telemetry_id,
                json.dumps(request),
                response_messages,
                is_cached,
                json.dumps(client_config),
                start_time,
                end_time))
            self.con.commit()


    def get_current_ts(self):
        return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


    def close(self):
        if self.con:
            self.con.close()
