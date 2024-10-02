# Dockerfiles and Devcontainer Configurations for AutoGen

Welcome to the `.devcontainer` directory! Here you'll find Dockerfiles and devcontainer configurations that are essential for setting up your AutoGen development environment. Each Dockerfile is tailored for different use cases and requirements. Below is a brief overview of each and how you can utilize them effectively.

These configurations can be used with Codespaces and locally.

## Dockerfile Descriptions

### base

- **Purpose**: This Dockerfile, i.e., `./Dockerfile`, is designed for basic setups. It includes common Python libraries and essential dependencies required for general usage of AutoGen.
- **Usage**: Ideal for those just starting with AutoGen or for general-purpose applications.
- **Building the Image**: Run `docker build -f ./Dockerfile -t autogen_base_img .` in this directory.
- **Using with Codespaces**: `Code > Codespaces > Click on +` By default + creates a Codespace on the current branch.

### full

- **Purpose**: This Dockerfile, i.e., `./full/Dockerfile` is for advanced features. It includes additional dependencies and is configured for more complex or feature-rich AutoGen applications.
- **Usage**: Suited for advanced users who need the full range of AutoGen's capabilities.
- **Building the Image**: Execute `docker build -f full/Dockerfile -t autogen_full_img .`.
- **Using with Codespaces**: `Code > Codespaces > Click on ...> New with options > Choose "full" as devcontainer configuration`. This image may require a Codespace with at least 64GB of disk space.

### dev

- **Purpose**: Tailored for AutoGen project developers, this Dockerfile, i.e., `./dev/Dockerfile` includes tools and configurations aiding in development and contribution.
- **Usage**: Recommended for developers who are contributing to the AutoGen project.
- **Building the Image**: Run `docker build -f dev/Dockerfile -t autogen_dev_img .`.
- **Using with Codespaces**: `Code > Codespaces > Click on ...> New with options > Choose "dev" as devcontainer configuration`. This image may require a Codespace with at least 64GB of disk space.
- **Before using**: We highly encourage all potential contributors to read the [AutoGen Contributing](https://microsoft.github.io/autogen/docs/Contribute) page prior to submitting any pull requests.


### studio

- **Purpose**: Tailored for AutoGen project developers, this Dockerfile, i.e., `./studio/Dockerfile`, includes tools and configurations aiding in development and contribution.
- **Usage**: Recommended for developers who are contributing to the AutoGen project.
- **Building the Image**: Run `docker build -f studio/Dockerfile -t autogen_studio_img .`.
- **Using with Codespaces**: `Code > Codespaces > Click on ...> New with options > Choose "studio" as devcontainer configuration`.
- **Before using**: We highly encourage all potential contributors to read the [AutoGen Contributing](https://microsoft.github.io/autogen/docs/Contribute) page prior to submitting any pull requests.


## Customizing Dockerfiles

Feel free to modify these Dockerfiles for your specific project needs. Here are some common customizations:

- **Adding New Dependencies**: If your project requires additional Python packages, you can add them using the `RUN pip install` command.
- **Changing the Base Image**: You may change the base image (e.g., from a Python image to an Ubuntu image) to suit your project's requirements.
- **Changing the Python version**: do you need a different version of python other than 3.11. Just update the first line of each of the Dockerfiles like so:
    `FROM python:3.11-slim-bookworm` to `FROM python:3.10-slim-bookworm`
- **Setting Environment Variables**: Add environment variables using the `ENV` command for any application-specific configurations. We have prestaged the line needed to inject your OpenAI_key into the docker environment as a environmental variable. Others can be staged in the same way. Just uncomment the line.
    `# ENV OPENAI_API_KEY="{OpenAI-API-Key}"` to `ENV OPENAI_API_KEY="{OpenAI-API-Key}"`
- **Need a less "Advanced" Autogen build**: If the `./full/Dockerfile` is to much but you need more than advanced then update this line in the Dockerfile file.
`RUN pip install autogen-agentchat[teachable,lmm,retrievechat,mathchat,blendsearch]~=0.2 autogenra` to install just what you need. `RUN pip install autogen-agentchat[retrievechat,blendsearch]~=0.2 autogenra`
- **Can't Dev without your favorite CLI tool**: if you need particular OS tools to be installed in your Docker container you can add those packages here right after the sudo for the `./base/Dockerfile` and `./full/Dockerfile` files. In the example below we are installing net-tools and vim to the environment.

    ```code
    RUN apt-get update \
        && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            software-properties-common sudo net-tools vim\
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*
    ```

### Managing Your Docker Environment

After customizing your Dockerfile, build the Docker image using the `docker build` command as shown above. To run a container based on your new image, use:

```bash
docker run -it -v $(pwd)/your_app:/app your_image_name
```

Replace `your_app` with your application directory and `your_image_name` with the name of the image you built.

#### Closing for the Day

- **Exit the container**: Type `exit`.
- **Stop the container**: Use `docker stop {application_project_name}`.

#### Resuming Work

- **Restart the container**: Use `docker start {application_project_name}`.
- **Access the container**: Execute `sudo docker exec -it {application_project_name} bash`.
- **Reactivate the environment**: Run `source /usr/src/app/autogen_env/bin/activate`.

### Useful Docker Commands

- **View running containers**: `docker ps -a`.
- **View Docker images**: `docker images`.
- **Restart container setup**: Stop (`docker stop my_container`), remove the container (`docker rm my_container`), and remove the image (`docker rmi my_image:latest`).

#### Troubleshooting Common Issues

- Check Docker daemon, port conflicts, and permissions issues.

#### Additional Resources

For more information on Docker usage and best practices, refer to the [official Docker documentation](https://docs.docker.com).
