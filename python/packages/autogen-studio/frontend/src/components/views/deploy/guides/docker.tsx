import React from "react";
import { Alert } from "antd";
import { CodeSection, copyToClipboard } from "./guides";

const DockerGuide: React.FC = () => {
  return (
    <div className="max-w-4xl">
      <h1 className="tdext-2xl font-bold mb-6">Docker Container Setup</h1>

      <Alert
        className="mb-6"
        message="Prerequisites"
        description={
          <ul className="list-disc pl-4 mt-2 space-y-1">
            <li>Docker installed on your system</li>
          </ul>
        }
        type="info"
      />
      <CodeSection
        title="1. Dockerfile"
        description=<div>
          AutoGen Studio provides a
          <a
            href="https://github.com/microsoft/autogen/blob/main/python/packages/autogen-studio/Dockerfile"
            target="_blank"
            rel="noreferrer"
            className="text-accent underline px-1"
          >
            Dockerfile
          </a>
          that you can use to build your Docker container.{" "}
        </div>
        code={`FROM mcr.microsoft.com/devcontainers/python:3.10

WORKDIR /code

RUN pip install -U gunicorn autogenstudio

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user 
    PATH=/home/user/.local/bin:$PATH 
    AUTOGENSTUDIO_APPDIR=/home/user/app

WORKDIR $HOME/app

COPY --chown=user . $HOME/app

CMD gunicorn -w $((2 * $(getconf _NPROCESSORS_ONLN) + 1)) --timeout 12600 -k uvicorn.workers.UvicornWorker autogenstudio.web.app:app --bind "0.0.0.0:8081"`}
        onCopy={copyToClipboard}
      />

      {/* Build and Run */}
      <CodeSection
        title="2. Build and Run"
        description="Build and run your Docker container:"
        code={`docker build -t autogenstudio .
docker run -p 8000:8000 autogenstudio`}
        onCopy={copyToClipboard}
      />
    </div>
  );
};

export default DockerGuide;
