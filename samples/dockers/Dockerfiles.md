# README for AutoGen Docker Samples

Welcome to the `autogen/samples/dockers` directory! Here you'll find Dockerfiles that are essential for setting up your AutoGen development environment. Each Dockerfile is tailored for different use cases and requirements. Below is a brief overview of each and how you can utilize them effectively.

## Dockerfile Descriptions

### Dockerfile.base

- **Purpose**: This Dockerfile is designed for basic setups. It includes common Python libraries and essential dependencies required for general usage of AutoGen.
- **Usage**: Ideal for those just starting with AutoGen or for general-purpose applications.
- **Building the Image**: Run `docker build -f Dockerfile.base -t autogen_base_img .` in this directory.

### Dockerfile.full

- **Purpose**: This Dockerfile is for advanced features. It includes additional dependencies and is configured for more complex or feature-rich AutoGen applications.
- **Usage**: Suited for advanced users who need the full range of AutoGen's capabilities.
- **Building the Image**: Execute `docker build -f Dockerfile.full -t autogen_full_img .`.

### Dockerfile.dev

- **Purpose**: Tailored for AutoGen project developers, this Dockerfile includes tools and configurations aiding in development and contribution.
- **Usage**: Recommended for developers who are contributing to the AutoGen project.
- **Building the Image**: Run `docker build -f Dockerfile.dev -t autogen_dev_img .`.
- **Before using**: We highly encourage all potential contributors to read the [AutoGen Contributing](https://microsoft.github.io/autogen/docs/Contribute) page prior to submitting any pull requests.

## Customizing Dockerfiles

Feel free to modify these Dockerfiles for your specific project needs. Here are some common customizations:

- **Adding New Dependencies**: If your project requires additional Python packages, you can add them using the `RUN pip install` command.
- **Changing the Base Image**: You may change the base image (e.g., from a Python image to an Ubuntu image) to suit your project's requirements.
- **Changing the Python version**: do you need a different version of python other than 3.11. Just update the first line of each of the Dockerfiles like so:
    `FROM python:3.11-slim-bookworm` to `FROM python:3.10-slim-bookworm`
- **Setting Environment Variables**: Add environment variables using the `ENV` command for any application-specific configurations. We have prestaged the line needed to inject your OpenAI_key into the docker environment as a environmental variable. Others can be staged in the same way. Just uncomment the line.
    `# ENV OPENAI_API_KEY="{OpenAI-API-Key}"` to `ENV OPENAI_API_KEY="{OpenAI-API-Key}"`
- **Need a less "Advanced" Autogen build**: If the Dockerfile.full is to much but you need more than advanced then update this line in the Dockerfile.full file.
`RUN pip install pyautogen[teachable,lmm,retrievechat,mathchat,blendsearch] autogenra` to install just what you need. `RUN pip install pyautogen[retrievechat,blendsearch] autogenra`
- **Can't Dev without your favorite CLI tool**: if you need particular OS tools to be installed in your Docker container you can add those packages here right after the sudo for the Dockerfile.base and Dockerfile.full files. In the example below we are installing net-tools and vim to the environment.

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
