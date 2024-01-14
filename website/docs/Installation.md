# AutoGen Installation Guide

AutoGen is a versatile tool that can be installed and run in Docker or locally using a virtual environment. Below are detailed instructions for both methods.

## Option 1: Install and Run AutoGen in Docker

Docker, an indispensable tool in modern software development, offers a compelling solution for AutoGen's setup. Docker allows you to create consistent environments that are portable and isolated from the host OS. With Docker, everything AutoGen needs to run, from the operating system to specific libraries, is encapsulated in a container, ensuring uniform functionality across different systems. The Dockerfiles necessary for AutoGen are conveniently located in the project's GitHub repository at [https://github.com/microsoft/autogen/tree/main/samples/dockers](https://github.com/microsoft/autogen/tree/main/samples/dockers). For more details on customizing the Dockerfiles, see the [Docker Samples README](../samples/dockers/Dockerfiles.md).

**Pre-configured DockerFiles**: The AutoGen Project offers pre-configured Dockerfiles for your use. These Dockerfiles will run as is, however they can be modified to suit your development needs. Please see the README.md file in autogen/samples/dockers

- **autogen_base_img**: For a basic setup, you can use the `autogen_base_img` to run simple scripts or applications. This is ideal for general users or those new to AutoGen.
- **autogen_full_img**: Advanced users or those requiring more features can use `autogen_full_img`. Be aware that this version loads ALL THE THINGS and thus is very large. Take this into consideration if you build your application off of it.

### Step 1: Install Docker

- **General Installation**: Follow the [official Docker installation instructions](https://docs.docker.com/get-docker/). This is your first step towards a containerized environment, ensuring a consistent and isolated workspace for AutoGen.

- **For Mac Users**: If you encounter issues with the Docker daemon, consider using [colima](https://smallsharpsoftwaretools.com/tutorials/use-colima-to-run-docker-containers-on-macos/). Colima offers a lightweight alternative to manage Docker containers efficiently on macOS.

### Step 2: Build a Docker Image

AutoGen now provides updated Dockerfiles tailored for different needs. Building a Docker image is akin to setting the foundation for your project's environment:

- **Autogen Basic (dockerfile.base)**: Ideal for general use, this setup includes common Python libraries and essential dependencies. Perfect for those just starting with AutoGen.

  ```bash
  docker build -f samples/dockers/Dockerfile.base -t autogen_base_img https://github.com/microsoft/autogen.git
  ```

- **Autogen Advanced (dockerfile.full)**: Advanced users or those requiring all the things that AutoGen has to offer `autogen_full_img`

   ```bash
   docker build -f samples/dockers/Dockerfile.full -t autogen_full_img https://github.com/microsoft/autogen.git  
   ```

### Step 3: Run AutoGen Applications from Docker Image

Here's how you can run an application built with AutoGen, using the Docker image:

1. **Mount Your Code**: Use the Docker `-v` flag to mount your local application directory to the Docker container. This allows you to develop on your local machine while running the code in a consistent Docker environment. For example:

   ```bash
   docker run -it -v $(pwd)/myapp:/home/autogen/autogen/myapp autogen_base_img:latest python /home/autogen/autogen/myapp/main.py
   ```

   Here, `$(pwd)/myapp` is your local directory, and `/home/autogen/autogen/myapp` is the path in the Docker container where your code will be located. 

2. **Port Mapping**: If your application requires a specific port, use the `-p` flag to map the container's port to your host. For instance, if your app runs on port 3000 inside Docker and you want it accessible on port 8080 on your host machine:

   ```bash
   docker run -it -p 8080:3000 -v $(pwd)/myapp:/myapp autogen_base_img:latest python /myapp
   ```

   In this command, `-p 8080:3000` maps port 3000 from the container to port 8080 on your local machine.

3. **Examples of Running Different Applications**:
`docker run -it -p {WorkstationPortNum}:{DockerPortNum} -v {WorkStation_Dir}:{Docker_DIR} {name_of_the_image}:latest`

- *Simple Script*: Run a Python script located in your local `myapp` directory.

   ```bash
   docker run -it -v `pwd`/myapp:/myapp autogen_base_img:latest python /myapp/my_script.py
   ```

- *Web Application*: If your application includes a web server running on port 5000.

   ```bash
   docker run -it -p 8080:5000 -v $(pwd)/myapp:/myapp autogen_base_img:latest
   ```

- *Data Processing*: For tasks that involve processing data stored in a local directory.

   ```bash
   docker run -it -v $(pwd)/data:/data autogen_base_img:latest python /myapp/process_data.py
   ```

#### Additional Resources

- For more information on Docker usage and best practices, refer to the [official Docker documentation](https://docs.docker.com).

- Details for managing and interacting with your AutoGen Docker containers can be found in the [Docker Samples README](../samples/dockers/Dockerfiles.md).

- Details on how to use the Dockerfile.dev version can be found on the [Contributing](Contribute.md#docker)

## Option 2: Install AutoGen Locally Using Virtual Environment

### Option a: venv

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv pyautogen
   source pyautogen/bin/activate
   ```

2. To exit the virtual environment:

   ```bash
   deactivate
   ```

### Option b: conda

1. Create and activate a Conda environment:

   ```bash
   conda create -n pyautogen python=3.10
   conda activate pyautogen
   ```

2. To exit Conda environment:

   ```bash
   conda deactivate
   ```

### Option c: poetry

1. Initialize and activate a Poetry environment:

   ```bash
   poetry init
   poetry shell
   poetry add pyautogen
   ```

2. To exit the Poetry environment:

   ```bash
   exit
   ```

## Python Version Compatibility

AutoGen requires **Python version >= 3.8, < 3.12**. Install it using pip:

```bash
pip install pyautogen
```

Refer to the [Migration guide to v0.2](/autogen/docs/Installation#migration-guide-to-v0.2) for updates and changes.

### Optional Dependencies

- **Docker**: Highly recommended for code execution. Install with `pip install docker`.
- **Blendsearch**: For hyperparameter optimization. Install with `pip install "pyautogen[blendsearch]<0.2"`.
- **Retrievechat**: For retrieval-augmented tasks. Install with `pip install "pyautogen[retrievechat]"`.
- **Teachability**: For teachable agents. Install with `pip install "pyautogen[teachable]"`.
- **LMM Agents**: For multimodal conversable agents. Install with `pip install "pyautogen[lmm]"`.
- **Mathchat**: For math problem-solving agents. Install with `pip install "pyautogen[mathchat]<0.2"`.
