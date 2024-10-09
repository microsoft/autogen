import subprocess
from flask import Flask, render_template_string, request
import pandas as pd
from io import StringIO
import re

app = Flask(__name__)


def run_agbench_command(path):
    command = f"agbench tabulate {path}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    command_csv = f"agbench tabulate {path} -c"
    result_csv = subprocess.run(command_csv, shell=True, capture_output=True, text=True)
    return result.stdout, result_csv.stdout


def parse_data_csv(input_string):
    # Split the input string into lines
    lines = input_string.strip().split("\n")
    parsed_data = []
    for line in lines:
        # Use regex to split the line
        parts = re.split(r",\s*\(", line)
        if len(parts) != 2:
            print("len(parts) != 2")
            print(f"Skipping line: {line}")
            continue

        task_id = parts[0]
        # Remove the trailing parenthesis and split the rest
        # interpret as python tuple
        values = eval(parts[1].strip(")"))

        if len(values) != 3:
            print("len(values) != 3")
            print(f"Skipping line: {line}")
            continue

        score, groundtruth, prediction = values

        parsed_data.append(
            {"task_id": task_id, "score": float(score), "groundtruth": groundtruth, "prediction": prediction}
        )

    return pd.DataFrame(parsed_data)


def parse_agbench_output(output, output_csv):
    # Split the output into lines
    lines = output.split("\n")

    # Find the start and end of the table
    start_index = next(i for i, line in enumerate(lines) if line.startswith("Task Id"))
    end_index = next(i for i, line in enumerate(lines) if line.startswith("----") and i > start_index + 1)
    # Extract the summary statistics
    summary_start = end_index + 1
    summary_data = "\n".join(lines[summary_start - 1 :])
    summary = pd.read_csv(StringIO(summary_data), sep=r"\s{2,}", engine="python")
    summary.columns = ["Metric", "Value"]

    df = parse_data_csv(output_csv)

    return df.to_html(classes="table table-striped table-hover", index=False), summary.to_html(
        classes="table table-sm table-bordered", index=False
    )


@app.route("/", methods=["GET", "POST"])
def index():
    table_html = ""
    summary_html = ""
    path = ""
    if request.method == "POST":
        path = request.form["path"]
        output, output_csv = run_agbench_command(path)
        table_html, summary_html = parse_agbench_output(output, output_csv)

    return render_template_string(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AutoGenBench Dashboard</title>
            <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
            <style>
                .summary-table {
                    width: 50%;
                    margin: 0 auto;
                    text-align: left;
                    font-size: 1.2em;
                    
                }
                .summary-table th {
                    background-color: #f8f9fa;
                    font-weight: bold;
                    text-align: left;

                }
                .summary-table td {
                    text-align: left;
                }
                .results-table {
                    font-size: 1.0em;
                    align-items: left;
                    text-align: left;

                }
                .results-table th {
                    background-color: #f8f9fa;
                    font-weight: bold;
                    text-align: left;
                }
                
            </style>
        </head>
        <body>
            <div class="container mt-3">
                <h1 class="text-center mb-4">AutoGenBench Dashboard</h1>
                <form method="post" class="mb-4">
                    <div class="form-group">
                        <label for="path">Results Logs Path:</label>
                        <input type="text" class="form-control" id="path" name="path" value="{{ path }}" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">Tabulate Logs</button>
                </form>
                {% if summary_html %}
                    <h2 class="text-center mb-3">Summary</h2>
                    <div class="table-responsive summary-table mb-5">
                        {{ summary_html|safe }}
                    </div>
                {% endif %}
                {% if table_html %}
                    <h2 class="text-center mb-3">Results Table</h2>
                    <div class="table-responsive results-table">
                        {{ table_html|safe }}
                    </div>
                {% endif %}
            </div>
        </body>
        </html>
    """,
        table_html=table_html,
        summary_html=summary_html,
        path=path,
    )


if __name__ == "__main__":
    app.run(debug=True)
